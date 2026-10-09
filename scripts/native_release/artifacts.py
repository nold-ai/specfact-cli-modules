"""Validate final native archive bytes without extracting or executing payloads."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from specfact_code_review.run import native_backend, native_capsule


# Reuse the consumer's exact bounded parser; there is no alternate archive format.
# pylint: disable=protected-access
REPOSITORY = "nold-ai/specfact-code-review-capsule-darwin-arm64"
LOADER_IMAGES = frozenset({"python/bin/python3", "tools/semgrep-core"})
LOADER_ENTITLEMENTS = {"com.apple.security.cs.disable-library-validation": True}
REQUIRED_IMAGES = frozenset(
    {
        "bin/specfact-native-broker",
        "bin/specfact-native-bootstrap",
        "bin/specfact-native-self-test",
        "bin/specfact-native-verifier",
        "tools/git",
        "tools/uv",
        "tools/node",
        "tools/ruff",
        *LOADER_IMAGES,
    }
)
SIGNING_METADATA = "metadata/native-signing.json"


@dataclass(frozen=True)
class ReleaseArtifact:
    """Bind one validated input directory to the exact manifest bytes."""

    directory: Path
    manifest: bytes
    document: dict[str, Any]

    @property
    def manifest_sha256(self) -> str:
        return hashlib.sha256(self.manifest).hexdigest()


@contextmanager
def open_regular(path: Path) -> Iterator[BinaryIO]:
    """Reject linked/special inputs and retain the original opened descriptor."""
    if path.absolute() != path.resolve(strict=True) or not path.is_file():
        raise ValueError("release input must be a canonical regular file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("release input must be a regular file")
        yield stream


def read_bounded(path: Path, maximum: int) -> bytes:
    with open_regular(path) as stream:
        result = stream.read(maximum + 1)
    if not result or len(result) > maximum:
        raise ValueError("release input size exceeds bounds")
    return result


def _read_member(reader: Any, size: int, *, capture: bool) -> tuple[str, bytes]:
    digest = hashlib.sha256()
    output = bytearray()
    remaining = size
    while remaining:
        chunk = reader.read_exact(min(native_capsule.CHUNK, remaining))
        digest.update(chunk)
        if capture:
            output.extend(chunk)
        remaining -= len(chunk)
    if any(reader.read_exact((-size) % 512)):
        raise ValueError("nonzero archive member padding")
    return digest.hexdigest(), bytes(output)


def _validate_member(header: bytes, name: str, record: dict[str, Any]) -> None:
    member = native_capsule._ordinary_header(header)
    if (member.name, member.size, member.mode) != (name, record["size"], record["mode"]):
        raise ValueError("archive member differs from manifest")
    if member.uid != 0 or member.gid != 0 or member.mtime != 0:
        raise ValueError("archive member has noncanonical ownership or time")


def validate_loader_profile(payload: bytes, signatures: dict[str, Any]) -> None:
    metadata = native_capsule._json(payload)
    if set(metadata) != {"schema", "images"} or metadata["schema"] != "specfact-native-signing-v1":
        raise ValueError("native signing metadata schema differs")
    images = metadata["images"]
    if not isinstance(images, dict) or set(images) != set(signatures):
        raise ValueError("native signing image coverage differs")
    if not set(images) >= REQUIRED_IMAGES:
        raise ValueError("required native image closure is incomplete")
    for name, record in images.items():
        expected = LOADER_ENTITLEMENTS if name in LOADER_IMAGES else {}
        if not isinstance(record, dict) or set(record) != {"signature", "entitlements"}:
            raise ValueError("native signing image descriptor differs")
        if native_capsule._canonical(record["signature"]) != native_capsule._canonical(
            signatures[name]
        ) or native_capsule._canonical(record["entitlements"]) != native_capsule._canonical(expected):
            raise ValueError("native signature or entitlement profile differs")


def _verify_archive(path: Path, document: dict[str, Any]) -> None:
    captured = b""
    with open_regular(path) as stream:
        before = os.fstat(stream.fileno())
        reader = native_capsule._ArchiveReader(stream, document["archive"], lambda *_args: None)
        for name, record in sorted(document["files"].items()):
            _validate_member(reader.read_exact(512), name, record)
            capture = name == SIGNING_METADATA
            if capture and record["size"] > 2 * 1024**2:
                raise ValueError("native signing metadata exceeds bounds")
            digest, content = _read_member(reader, record["size"], capture=capture)
            if digest != record["sha256"]:
                raise ValueError("archive file digest differs from manifest")
            if capture:
                captured = content
        if any(reader.read_exact(1024)):
            raise ValueError("nonzero archive end blocks")
        reader.finish()
        if native_capsule._stable(before) != native_capsule._stable(os.fstat(stream.fileno())):
            raise ValueError("archive changed during validation")
    validate_loader_profile(captured, document["native_signatures"])


def inspect_archive(directory: Path) -> ReleaseArtifact:
    """Reject changed bytes and broadened profiles before signing authority."""
    manifest = read_bounded(directory / "manifest.json", native_capsule.MAX_MANIFEST)
    document = native_capsule._json(manifest)
    native_capsule._manifest(
        document,
        str(document.get("environment_id", "")),
        native_backend.BACKEND_VERSION,
        native_backend.POLICY_VERSION,
    )
    _verify_archive(directory / "capsule.tar", document)
    return ReleaseArtifact(directory, manifest, document)
