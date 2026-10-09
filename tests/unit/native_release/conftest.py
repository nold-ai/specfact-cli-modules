from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from scripts import build_macos_native_capsule as builder
from scripts.native_release import release
from tests.unit.test_build_macos_native_capsule import ANALYZER_VERSIONS, _macho


def fixture_runtime(tmp_path: Path):
    root = tmp_path / "runtime"
    images = {
        "bin/specfact-native-broker",
        "bin/specfact-native-bootstrap",
        "bin/specfact-native-self-test",
        "bin/specfact-native-verifier",
        "python/bin/python3",
        "tools/ruff",
        "tools/semgrep-core",
        "tools/node",
        "tools/uv",
        "tools/git",
    }
    for name in images:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_macho())
        path.chmod(0o755)
    (root / "licenses").mkdir()
    (root / "licenses/runtime.txt").write_text("fixture license\n")
    (root / "provenance").mkdir()
    (root / "provenance/runtime.json").write_text('{"fixture":true}\n')
    return root, images


@pytest.fixture
def release_artifact(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(builder, "verify_managed_git_runtime", lambda *_args, **_kwargs: None)
    root, images = fixture_runtime(tmp_path)
    signature = {
        "format": "mach-o",
        "mode": "adhoc",
        "identifier": "ai.nold.fixture",
        "cdhash": "a" * 40,
        "hardened_runtime": True,
    }

    def prepare(abi="cp312", *, altered_entitlement=None):
        def entitlements(path):
            name = path.relative_to(root).as_posix()
            if altered_entitlement is not None and name == altered_entitlement:
                return {"com.apple.security.cs.allow-jit": True}
            if name in {"python/bin/python3", "tools/semgrep-core"}:
                return {"com.apple.security.cs.disable-library-validation": True}
            return {}

        return builder.build_native_capsule(
            runtime_root=root,
            output_dir=tmp_path / abi,
            closure={
                "images-v1": sorted(images),
                "licenses-v1": ["licenses/runtime.txt"],
                "provenance-v1": ["provenance/runtime.json"],
            },
            environment_id=f"darwin-arm64-{abi}",
            backend="managed-v3",
            policy="project-domains-v3",
            analyzer_versions=ANALYZER_VERSIONS,
            private_key=None,
            signature_inspector=lambda _path: dict(signature),
            entitlements_inspector=entitlements,
        )

    return prepare


@pytest.fixture
def release_inputs(release_artifact, tmp_path):
    directories = [release_artifact(abi).archive.parent for abi in release.ABIS]
    receipts = []
    for directory in directories:
        artifact = release.inspect_archive(directory)
        for runner, (version, build) in release.PLATFORMS.items():
            receipts.append(
                {
                    "schema": "specfact-native-acceptance-v1",
                    "source_sha": "a" * 40,
                    "environment_id": artifact.document["environment_id"],
                    "runner": runner,
                    "os_version": version,
                    "os_build": build,
                    "architecture": "arm64",
                    "manifest_sha256": artifact.manifest_sha256,
                    "archive_sha256": artifact.document["archive"]["sha256"],
                    "checks": dict.fromkeys(release.REQUIRED_CHECKS, True),
                }
            )
    receipt_path = tmp_path / "receipts.json"
    receipt_path.write_text(json.dumps(receipts))
    key = ed25519.Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    context = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "nold-ai/specfact-cli-modules",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REF_PROTECTED": "true",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_WORKFLOW_SHA": "a" * 40,
        "GITHUB_WORKFLOW_REF": "nold-ai/specfact-cli-modules/.github/workflows/native-capsule-release.yml@refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
    }
    return directories, receipt_path, key, public, context
