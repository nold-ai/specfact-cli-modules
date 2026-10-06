"""Data-only protected signing and atomic module-catalog staging."""

from __future__ import annotations

import ctypes
import errno
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization

from scripts.build_macos_native_capsule import _sign
from scripts.native_release.artifacts import REPOSITORY, ReleaseArtifact, inspect_archive, open_regular, read_bounded

# The release format deliberately shares the existing consumer validators.
# pylint: disable=protected-access
from scripts.native_release.platforms import ABIS, PLATFORMS, REQUIRED_CHECKS
from specfact_code_review.run import native_backend, native_capsule


WORKFLOW = "nold-ai/specfact-cli-modules/.github/workflows/native-capsule-release.yml@refs/heads/main"


def protected_source(context: Mapping[str, str]) -> str:
    """Reject every non-reviewed context before reading signing material."""
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "nold-ai/specfact-cli-modules",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REF_PROTECTED": "true",
        "GITHUB_WORKFLOW_REF": WORKFLOW,
        "GITHUB_EVENT_NAME": "workflow_dispatch",
    }
    source = context.get("GITHUB_SHA", "")
    if any(context.get(name) != value for name, value in expected.items()):
        raise ValueError("native signing requires the protected reviewed workflow")
    if re.fullmatch(r"[0-9a-f]{40}", source) is None or context.get("GITHUB_WORKFLOW_SHA") != source:
        raise ValueError("protected workflow and source identity differ")
    return source


def _artifact_set(directories: Sequence[Path]) -> dict[str, ReleaseArtifact]:
    artifacts: dict[str, ReleaseArtifact] = {}
    for directory in directories:
        artifact = inspect_archive(directory)
        identity = artifact.document["environment_id"]
        if identity in artifacts:
            raise ValueError("duplicate capsule ABI")
        artifacts[identity] = artifact
    if set(artifacts) != {f"darwin-arm64-{abi}" for abi in ABIS}:
        raise ValueError("complete three-ABI capsule set is required")
    return artifacts


def validate_matrix(path: Path, artifacts: Mapping[str, ReleaseArtifact], source: str) -> None:
    import json

    receipts = json.loads(read_bounded(path, 1024 * 1024), object_pairs_hook=_unique_pairs)
    if not isinstance(receipts, list) or len(receipts) != len(ABIS) * len(PLATFORMS):
        raise ValueError("incomplete native acceptance matrix")
    observed: set[tuple[str, str]] = set()
    for receipt in receipts:
        identity = _validate_receipt(receipt, artifacts, source)
        if identity in observed:
            raise ValueError("duplicate native acceptance matrix cell")
        observed.add(identity)
    if observed != {(environment, runner) for environment in artifacts for runner in PLATFORMS}:
        raise ValueError("native acceptance matrix coverage differs")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate receipt JSON field")
        result[name] = value
    return result


def _validate_receipt(receipt: Any, artifacts: Mapping[str, ReleaseArtifact], source: str) -> tuple[str, str]:
    fields = {
        "schema",
        "source_sha",
        "environment_id",
        "runner",
        "os_version",
        "os_build",
        "architecture",
        "manifest_sha256",
        "archive_sha256",
        "checks",
    }
    if not isinstance(receipt, dict) or set(receipt) != fields:
        raise ValueError("invalid native acceptance receipt")
    environment, runner = receipt["environment_id"], receipt["runner"]
    if environment not in artifacts or runner not in PLATFORMS:
        raise ValueError("unsupported native acceptance matrix cell")
    artifact = artifacts[environment]
    expected = {
        "schema": "specfact-native-acceptance-v1",
        "source_sha": source,
        "architecture": "arm64",
        "os_version": PLATFORMS[runner][0],
        "os_build": PLATFORMS[runner][1],
        "manifest_sha256": artifact.manifest_sha256,
        "archive_sha256": artifact.document["archive"]["sha256"],
        "checks": dict.fromkeys(REQUIRED_CHECKS, True),
    }
    if any(
        native_capsule._canonical(receipt[name]) != native_capsule._canonical(value) for name, value in expected.items()
    ):
        raise ValueError("native acceptance receipt failed or substituted")
    return environment, runner


def catalog_entry(artifact: ReleaseArtifact) -> dict[str, Any]:
    document = artifact.document
    environment = document["environment_id"]
    prefix = f"resources/native-capsules/{environment}"
    return {
        "environment_id": environment,
        "backend": document["backend"],
        "policy": document["policy"],
        "resources": {
            "manifest": f"{prefix}/manifest.json",
            "signature": f"{prefix}/manifest.sig",
            "public_key": f"{prefix}/manifest-public.pem",
        },
        "ghcr": {
            "repository": REPOSITORY,
            "blob": {"digest": f"sha256:{document['archive']['sha256']}", "size": document["archive"]["size"]},
            "redirect_allowlist": [
                {"host": "ghcr.io", "path_prefix": f"/v2/{REPOSITORY}/blobs/"},
                {"host": "pkg-containers.githubusercontent.com", "path_prefix": "/"},
            ],
            "max_redirects": 4,
        },
    }


def _public_bytes(key: Any) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def _stage_artifact(work: Path, artifact: ReleaseArtifact, key: Any, public: bytes) -> dict[str, Any]:
    environment = artifact.document["environment_id"]
    archive_root = work / "archives" / environment
    resource_root = work / "module/resources/native-capsules" / environment
    archive_root.mkdir(parents=True)
    resource_root.mkdir(parents=True)
    with (
        open_regular(artifact.directory / "capsule.tar") as source,
        (archive_root / "capsule.tar").open("xb") as destination,
    ):
        shutil.copyfileobj(source, destination, 64 * 1024)
    signature = _sign(artifact.manifest, key)
    native_capsule._authenticate(artifact.manifest, signature, public)
    for root in (archive_root, resource_root):
        (root / "manifest.json").write_bytes(artifact.manifest)
        (root / "manifest.sig").write_text(signature, encoding="ascii")
        (root / "manifest-public.pem").write_bytes(public)
    inspect_archive(archive_root)
    return catalog_entry(artifact)


def install_exclusive(source: Path, destination: Path) -> None:
    """Atomically publish a directory without replacing a concurrent writer."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        operation = library.renamex_np
        arguments = (os.fsencode(source), os.fsencode(destination), 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        operation = library.renameat2
        arguments = (-100, os.fsencode(source), -100, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    else:
        raise ValueError("exclusive release installation requires Darwin or Linux")
    if operation(*arguments) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise ValueError("release output already exists")
        raise OSError(error, os.strerror(error))


@dataclass(frozen=True)
class StageRequest:
    """Reviewed immutable input identities and one exclusive output location."""

    directories: Sequence[Path]
    receipts: Path
    output: Path
    public: bytes
    context: Mapping[str, str]


def stage_release(request: StageRequest, load_key: Callable[[], Any]) -> None:
    """Stage only; this function never uploads, executes payloads or promotes."""
    directories, receipts, output, public, context = (
        request.directories,
        request.receipts,
        request.output,
        request.public,
        request.context,
    )
    source = protected_source(context)
    if output.exists() or output.is_symlink():
        raise ValueError("release output already exists")
    artifacts = _artifact_set(directories)
    validate_matrix(receipts, artifacts, source)
    key = load_key()
    if _public_bytes(key) != public:
        raise ValueError("release signing key differs from the reviewed public key")
    work = Path(tempfile.mkdtemp(prefix=".release-", dir=output.parent))
    try:
        entries = {name: _stage_artifact(work, artifact, key, public) for name, artifact in artifacts.items()}
        module = work / "module"
        for name, entry in entries.items():
            native_backend._catalog_entry(module, name, entry, offline=True)
        catalog = module / "resources/contracts/native-capsule-catalog-v1.json"
        catalog.parent.mkdir(parents=True)
        catalog.write_bytes(
            native_capsule._canonical({"schema": "specfact-native-capsule-catalog-v1", "entries": entries}) + b"\n"
        )
        (work / "release.json").write_bytes(
            native_capsule._canonical(
                {"source_sha": source, "publication": "staged-only", "production_eligible": False}
            )
            + b"\n"
        )
        install_exclusive(work, output)
    finally:
        if work.exists():
            shutil.rmtree(work)
