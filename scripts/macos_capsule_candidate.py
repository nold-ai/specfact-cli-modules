"""Inspect a small local COPY-only OCI proof; never execute, extract or publish it."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import stat
import sys
import tarfile
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TypeGuard

from icontract import ensure


MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_LAYER_BYTES = 16 * 1024 * 1024
MAX_MEMBERS = 256
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
CONFIG_TYPE = "application/vnd.oci.image.config.v1+json"
LAYER_TYPE = "application/vnd.oci.image.layer.v1.tar+gzip"


def _digest(data: bytes) -> str:
    """Return the OCI SHA-256 identity for exact bytes."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _bounded_file(path: Path) -> bytes:
    """Read a local file without exceeding the candidate byte budget."""
    with path.open("rb") as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("archive/file byte limit exceeded")
    return data


def _path(name: str) -> str:
    """Reject ambiguous or escaping archive path spellings."""
    if not name or "\\" in name or "\0" in name or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("noncanonical archive path")
    return name


def _raw_header_path(header: bytes, directory: bool) -> str:
    """Validate raw name and prefix fields before TarInfo can strip slashes."""
    name = header[:100].split(b"\0", 1)[0].decode("utf-8", "strict")
    prefix = header[345:500].split(b"\0", 1)[0].decode("utf-8", "strict")
    name = _path(name.removesuffix("/") if directory else name)
    return _path(prefix) + "/" + name if prefix else name


def _ordinary_header(header: bytes) -> tarfile.TarInfo:
    """Validate a checksum-bearing header before any extension processing."""
    member = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
    if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
        raise ValueError("TAR extensions, sparse, links and special files are forbidden")
    if member.size < 0 or member.size > MAX_ARCHIVE_BYTES or (member.isdir() and member.size):
        raise ValueError("invalid TAR member size")
    if _raw_header_path(header, member.isdir()) != member.name:
        raise ValueError("TAR path normalization is forbidden")
    return member


def _physical_members(data: bytes) -> Iterator[tuple[tarfile.TarInfo, bytes]]:
    """Read bounded physical records without interpreting TAR extension headers."""
    if len(data) % 512:
        raise ValueError("unaligned TAR framing")
    offset = 0
    while offset < len(data):
        header = data[offset : offset + 512]
        if not any(header):
            if len(data) - offset < 1024 or any(data[offset:]):
                raise ValueError("invalid TAR end markers or trailing data")
            return
        member = _ordinary_header(header)
        start = offset + 512
        end = start + member.size
        offset = start + ((member.size + 511) // 512) * 512
        if offset > len(data) or any(data[end:offset]):
            raise ValueError("truncated TAR member or nonzero padding")
        yield member, data[start:end]
    raise ValueError("missing TAR end markers")


def _tar(data: bytes) -> tuple[dict[str, tuple[bytes, int]], set[str]]:
    """Validate canonical unique paths and collect regular files and directories."""
    files: dict[str, tuple[bytes, int]] = {}
    directories: set[str] = set()
    seen: set[str] = set()
    total = 0
    for member, payload in _physical_members(data):
        name = _path(member.name.removesuffix("/") if member.isdir() else member.name)
        if name in seen or len(seen) >= MAX_MEMBERS:
            raise ValueError("duplicate archive path or member limit exceeded")
        seen.add(name)
        if member.isdir():
            directories.add(name)
            continue
        total += member.size
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("tar content byte limit exceeded")
        files[name] = (payload, member.mode)
    return files, directories


def _object(value: object) -> dict[str, Any]:
    """Require JSON object metadata before reading its fields."""
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys instead of accepting ambiguous JSON."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    """Reject Python extensions that are not valid JSON numeric values."""
    raise ValueError(f"invalid JSON constant: {value}")


def _json(data: bytes) -> dict[str, Any]:
    """Decode JSON metadata with duplicate-key rejection."""
    return _object(
        json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    )


def _single(value: object) -> object:
    """Require exactly one manifest or layer descriptor."""
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError("exactly one descriptor required")
    return value[0]


def _integer(value: object) -> TypeGuard[int]:
    """Accept JSON integers while rejecting booleans and floats."""
    return isinstance(value, int) and not isinstance(value, bool)


def _blob(files: dict[str, tuple[bytes, int]], value: object, media: str) -> bytes:
    """Resolve a descriptor only after validating type, size and digest."""
    descriptor = _object(value)
    identity, size = descriptor.get("digest"), descriptor.get("size")
    if not isinstance(identity, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
        raise ValueError("invalid descriptor digest")
    if not _integer(size) or size < 0 or descriptor.get("mediaType") != media:
        raise ValueError("invalid descriptor size or media type")
    record = files.get("blobs/sha256/" + identity[7:])
    if record is None or len(record[0]) != size or _digest(record[0]) != identity:
        raise ValueError("blob digest or size mismatch")
    return record[0]


def _expected(root: Path) -> tuple[dict[str, tuple[bytes, int]], set[str]]:
    """Inventory the bounded operator-owned tree without following links."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("expected payload must be an ordinary directory")
    files: dict[str, tuple[bytes, int]] = {}
    directories = {"proof"}
    total = 0
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        name = _path("proof/" + path.relative_to(root).as_posix())
        if len(files) + len(directories) >= MAX_MEMBERS:
            raise ValueError("expected tree member limit exceeded")
        if stat.S_ISDIR(mode):
            directories.add(name)
            continue
        if not stat.S_ISREG(mode):
            raise ValueError("expected payload contains a link or special file")
        payload = _bounded_file(path)
        total += len(payload)
        if total > MAX_LAYER_BYTES:
            raise ValueError("expected payload byte limit exceeded")
        files[name] = (payload, stat.S_IMODE(mode))
    if not files:
        raise ValueError("expected payload must not be empty")
    return files, directories


def _manifest(files: dict[str, tuple[bytes, int]]) -> bytes:
    """Validate the OCI layout and native platform index."""
    if _json(files["oci-layout"][0]) != {"imageLayoutVersion": "1.0.0"}:
        raise ValueError("unsupported OCI layout")
    index = _json(files["index.json"][0])
    descriptor = _object(_single(index.get("manifests")))
    if (
        not _integer(index.get("schemaVersion"))
        or index.get("schemaVersion") != 2
        or descriptor.get("platform") != {"os": "darwin", "architecture": "arm64"}
    ):
        raise ValueError("index must describe darwin/arm64")
    return _blob(files, descriptor, MANIFEST_TYPE)


def _config(files: dict[str, tuple[bytes, int]], manifest: dict[str, Any]) -> bytes:
    """Validate manifest schema and the Darwin ARM64 configuration."""
    if (
        not _integer(manifest.get("schemaVersion"))
        or manifest.get("schemaVersion") != 2
        or manifest.get("mediaType") != MANIFEST_TYPE
    ):
        raise ValueError("unsupported OCI manifest")
    config_data = _blob(files, manifest.get("config"), CONFIG_TYPE)
    config = _json(config_data)
    if config.get("os") != "darwin" or config.get("architecture") != "arm64":
        raise ValueError("config must describe darwin/arm64")
    return config_data


def _layer_bytes(layer: bytes, config: dict[str, Any]) -> bytes:
    """Bound decompression and verify the uncompressed layer digest."""
    with gzip.GzipFile(fileobj=io.BytesIO(layer)) as compressed:
        raw = compressed.read(MAX_LAYER_BYTES + 1)
    if len(raw) > MAX_LAYER_BYTES:
        raise ValueError("decompressed layer byte limit exceeded")
    rootfs = _object(config.get("rootfs"))
    if rootfs.get("type") != "layers" or rootfs.get("diff_ids") != [_digest(raw)]:
        raise ValueError("layer diff_id mismatch")
    return raw


def _inspect(archive: Path, expected: Path) -> dict[str, object]:
    """Compare a verified OCI payload with the operator-provided tree."""
    files, directories = _tar(_bounded_file(archive))
    manifest_data = _manifest(files)
    manifest = _json(manifest_data)
    config_data = _config(files, manifest)
    layer = _blob(files, _single(manifest.get("layers")), LAYER_TYPE)
    referenced = {"blobs/sha256/" + _digest(data)[7:] for data in (manifest_data, config_data, layer)}
    if set(files) != {"oci-layout", "index.json"} | referenced or not directories <= {"blobs", "blobs/sha256"}:
        raise ValueError("unreferenced OCI archive entries")
    raw = _layer_bytes(layer, _json(config_data))
    observed = _tar(raw)
    if observed != _expected(expected):
        raise ValueError("payload tree bytes or modes differ from operator input")
    return {
        "status": "PASS",
        "experimental": True,
        "production_eligible": False,
        "os": "darwin",
        "architecture": "arm64",
        "manifest_digest": _digest(manifest_data),
        "config_digest": _digest(config_data),
        "layer_digest": _digest(layer),
        "diff_id": _digest(raw),
        "native_evidence_authenticity": "unverified-operator-claim",
        "native_execution_performed": False,
        "dependency_closure_validated": False,
        "payload": {name: {"sha256": _digest(data), "mode": oct(mode)} for name, (data, mode) in observed[0].items()},
    }


@ensure(lambda result: result["production_eligible"] is False)
def verify_candidate(archive: Path, expected: Path) -> dict[str, object]:
    """Compare a bounded archive against operator input, not an authenticated closure."""
    try:
        return _inspect(archive, expected)
    except (OSError, EOFError, tarfile.TarError, zlib.error, UnicodeError, KeyError, TypeError, RecursionError) as exc:
        raise ValueError(f"invalid candidate: {exc}") from exc


def _main() -> int:
    """Emit JSON success or failure without conferring publication authority."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-payload", type=Path, required=True, help="operator-owned tree copied to /proof")
    args = parser.parse_args()
    try:
        result = verify_candidate(args.archive, args.expected_payload)
    except ValueError as exc:
        sys.stderr.write(
            json.dumps({"status": "FAIL", "experimental": True, "production_eligible": False, "error": str(exc)}) + "\n"
        )
        return 1
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
