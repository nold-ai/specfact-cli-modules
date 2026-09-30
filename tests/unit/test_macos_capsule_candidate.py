"""COPY-only candidates preserve bytes, never confer native execution authority."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import zlib
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(name="api")
def fixture_candidate_api() -> Any:
    """Load the standalone inspector for direct API tests."""
    path = Path(__file__).parents[2] / "scripts/macos_capsule_candidate.py"
    spec = importlib.util.spec_from_file_location("macos_capsule_candidate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(data: bytes) -> str:
    """Compute fixture descriptor identities from their exact content."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tar_bytes(entries: list[tuple[str, bytes, bytes, int]]) -> bytes:
    """Build small ordinary TAR fixtures with explicit member types."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, content, kind, mode in entries:
            member = tarfile.TarInfo(name)
            member.type, member.mode = kind, mode
            member.size = len(content) if kind == tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = "../../outside"
            archive.addfile(member, io.BytesIO(content))
    return output.getvalue()


def candidate_layers(expected: Path, change: str) -> tuple[bytes, bytes]:
    """Create a payload layer and inject the selected negative case."""
    entries = [
        ({"layer-slash": "proof//"}.get(change, "proof"), b"", tarfile.DIRTYPE, 0o755),
        ("proof/hello", (expected / "hello").read_bytes(), tarfile.REGTYPE, 0o755),
    ]
    if change == "payload":
        entries[1] = ("proof/hello", b"changed", tarfile.REGTYPE, 0o755)
    if change == "mode":
        entries[1] = (entries[1][0], entries[1][1], entries[1][2], 0o644)
    if change in ("symlink", "hardlink", "fifo"):
        kind = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE, "fifo": tarfile.FIFOTYPE}[change]
        entries.append(("proof/other", b"", kind, 0o644))
    if change in ("../escape", "/absolute", "proof/./hello", "proof//hello", "proof/../hello"):
        entries.append((change, b"bad", tarfile.REGTYPE, 0o644))
    if change == "duplicate":
        entries.append(entries[1])
    if change == "extra":
        entries.append(("proof/extra", b"extra", tarfile.REGTYPE, 0o644))
    raw = tar_bytes(entries)
    if change.startswith("layer-framing:"):
        raw = malformed_tar(raw, change.split(":", 1)[1])
    layer = candidate_gzip(raw, change)
    if change == "invalid-deflate":
        layer = bytes.fromhex("1f8b0800000000000000") + b"\xff" * 16
    return raw, layer


def candidate_descriptor(blobs: dict[str, bytes], data: bytes, media: str) -> dict[str, Any]:
    """Store fixture bytes and return their matching OCI descriptor."""
    identity = digest(data)
    blobs["blobs/sha256/" + identity.split(":")[1]] = data
    return {"digest": identity, "size": len(data), "mediaType": media}


def candidate_config(raw: bytes, change: str) -> Any:
    """Build native configuration metadata with optional corruption."""
    config: Any = {"os": "darwin", "architecture": "arm64", "rootfs": {"type": "layers", "diff_ids": [digest(raw)]}}
    if change in ("linux", "amd64"):
        config["os" if change == "linux" else "architecture"] = change
    if change in ("NaN", "Infinity", "-Infinity"):
        config["unused"] = float(change)
    if change == "diffid":
        config["rootfs"]["diff_ids"] = [digest(b"wrong")]
    if change == "config-type":
        config = []
    return config


def candidate_manifest(
    blobs: dict[str, bytes], layer_desc: dict[str, Any], config_desc: dict[str, Any], change: str
) -> dict[str, Any]:
    """Build a one-layer manifest with optional descriptor corruption."""
    if change == "size":
        layer_desc["size"] += 1
    if change == "size-type":
        layer_desc["size"] = True
    if change == "corrupt":
        blobs["blobs/sha256/" + layer_desc["digest"].split(":")[1]] = b"corrupted"
    manifest = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": config_desc,
        "layers": [layer_desc],
    }
    if change == "manifest-version-type":
        manifest["schemaVersion"] = 2.0
    if change == "layers-type":
        manifest["layers"] = {}
    return manifest


def candidate_index(manifest_desc: dict[str, Any], change: str) -> Any:
    """Build a single-platform index with optional invalid metadata."""
    manifest_desc["platform"] = {"os": "linux" if change == "index-platform" else "darwin", "architecture": "arm64"}
    index: Any = {"schemaVersion": 2, "manifests": [manifest_desc]}
    if change == "index-version-type":
        index["schemaVersion"] = 2.0
    if change == "index-type":
        index = []
    return index


def candidate_outer(blobs: dict[str, bytes], index: Any, change: str) -> bytes:
    """Package referenced blobs and optional invalid outer records."""
    outer = [
        ("oci-layout", candidate_metadata({"imageLayoutVersion": "1.0.0"}, "layout", change), tarfile.REGTYPE, 0o644),
        ("index.json", candidate_metadata(index, "index", change), tarfile.REGTYPE, 0o644),
    ]
    outer.extend((name, data, tarfile.REGTYPE, 0o644) for name, data in blobs.items())
    if change == "outer-duplicate":
        outer.append(outer[1])
    if change == "outer-link":
        outer.append(("other", b"", tarfile.SYMTYPE, 0o644))
    extra_entries = {
        "outer-slash": ("blobs//", b"", tarfile.DIRTYPE, 0o755),
        "outer-extra": ("unchecked", b"extra", tarfile.REGTYPE, 0o644),
        "outer-blob": ("blobs/sha256/" + "0" * 64, b"extra", tarfile.REGTYPE, 0o644),
        "outer-directory": ("unchecked", b"", tarfile.DIRTYPE, 0o755),
    }
    if change in extra_entries:
        outer.append(extra_entries[change])
    raw = tar_bytes(outer)
    return malformed_tar(raw, change.split(":", 1)[1]) if change.startswith("outer-framing:") else raw


def candidate(tmp_path: Path, change: str = "") -> tuple[Path, Path]:
    """Write a self-contained candidate and its expected payload tree."""
    expected = tmp_path / "expected"
    expected.mkdir()
    (expected / "hello").write_bytes(b"operator-supplied native bytes")
    (expected / "hello").chmod(0o755)
    raw, layer = candidate_layers(expected, change)
    blobs: dict[str, bytes] = {}
    config = candidate_config(raw, change)
    layer_desc = candidate_descriptor(blobs, layer, "application/vnd.oci.image.layer.v1.tar+gzip")
    config_desc = candidate_descriptor(
        blobs, candidate_metadata(config, "config", change), "application/vnd.oci.image.config.v1+json"
    )
    manifest = candidate_manifest(blobs, layer_desc, config_desc, change)
    manifest_desc = candidate_descriptor(
        blobs, candidate_metadata(manifest, "manifest", change), "application/vnd.oci.image.manifest.v1+json"
    )
    index = candidate_index(manifest_desc, change)
    path = tmp_path / "candidate.tar"
    path.write_bytes(candidate_outer(blobs, index, change))
    return path, expected


def test_valid_candidate_is_never_production_evidence(api: Any, tmp_path: Path) -> None:
    """Keep successful byte comparison separate from production authority."""
    archive, expected = candidate(tmp_path)
    result = api.verify_candidate(archive, expected)
    assert result["status"] == "PASS"
    assert result["experimental"] is True
    assert result["production_eligible"] is False
    assert result["native_evidence_authenticity"] == "unverified-operator-claim"
    assert result["native_execution_performed"] is False


@pytest.mark.parametrize(
    "change",
    [
        "linux",
        "amd64",
        "index-platform",
        "corrupt",
        "size",
        "size-type",
        "diffid",
        "payload",
        "mode",
        "symlink",
        "hardlink",
        "fifo",
        "../escape",
        "/absolute",
        "proof/./hello",
        "proof//hello",
        "proof/../hello",
        "duplicate",
        "extra",
        "config-type",
        "layers-type",
        "index-type",
        "manifest-version-type",
        "index-version-type",
        "outer-duplicate",
        "outer-link",
        "NaN",
        "Infinity",
        "-Infinity",
        "outer-extra",
        "outer-blob",
        "outer-directory",
    ],
)
def test_reject_invalid_candidate(api: Any, tmp_path: Path, change: str) -> None:
    """Reject invalid identities, metadata, paths and payload contents."""
    archive, expected = candidate(tmp_path, change)
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


def test_bounded_decompression(api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject layers exceeding the uncompressed byte budget."""
    archive, expected = candidate(tmp_path)
    monkeypatch.setattr(api, "MAX_LAYER_BYTES", 1024)
    with pytest.raises(ValueError, match="limit"):
        api.verify_candidate(archive, expected)


def test_operator_tree_links_rejected(api: Any, tmp_path: Path) -> None:
    """Reject symlinks in the operator-provided expected tree."""
    archive, expected = candidate(tmp_path)
    (expected / "alias").symlink_to(expected / "hello")
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


def test_malformed_gzip_is_value_error(api: Any, tmp_path: Path) -> None:
    """Normalize malformed compressed data into the public error contract."""
    archive, expected = candidate(tmp_path, "invalid-deflate")
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


@pytest.mark.parametrize("case", [("", 0), ("linux", 1), ("NaN", 1), ("Infinity", 1), ("-Infinity", 1)])
def test_cli_local_only_json(tmp_path: Path, case: tuple[str, int]) -> None:
    """Check real CLI exit codes and local-only JSON evidence."""
    change, code = case
    archive, expected = candidate(tmp_path, change)
    script = Path(__file__).parents[2] / "scripts/macos_capsule_candidate.py"
    process = subprocess.run(
        [sys.executable, str(script), str(archive), "--expected-payload", str(expected)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert process.returncode == code
    result = json.loads(process.stderr if code else process.stdout)
    assert result["production_eligible"] is False
    assert result["experimental"] is True
    assert not (tmp_path / "proof").exists()


FRAMING_CASES = (
    "format:unknown",
    "format:ustar-version",
    "format:gnu-version",
    "format:v7",
    "invalid-header",
    "trailing-data",
    "one-zero",
    "missing-end",
    "partial-header",
    "unaligned",
    "padding",
    "sparse",
    "pax",
    "global-pax",
    "long-name",
    "long-link",
)


def malformed_tar(data: bytes, change: str) -> bytes:
    """Inject physical framing faults while preserving OCI descriptor consistency."""
    if change.startswith("format:"):
        return tar_format(data, change.split(":", 1)[1])
    offset = 0
    while any(data[offset : offset + 512]):
        member = tarfile.TarInfo.frombuf(data[offset : offset + 512], "utf-8", "strict")
        offset += 512 + ((member.size + 511) // 512) * 512
    body = data[:offset]
    replacements = {
        "invalid-header": body + b"!" * 512 + bytes(1024),
        "trailing-data": body + bytes(1024) + b"!" * 512,
        "one-zero": body + bytes(512),
        "missing-end": body,
        "partial-header": body + b"!" * 32,
        "unaligned": data + bytes(1),
    }
    if change in replacements:
        return replacements[change]
    if change == "padding":
        patched = bytearray(data)
        first = tarfile.TarInfo.frombuf(data[:512], "utf-8", "strict")
        payload_offset = 512 if first.isfile() else 1024
        patched[payload_offset + 100] = 1
        return bytes(patched)
    member = tarfile.TarInfo("extension")
    member.type = {
        "sparse": tarfile.GNUTYPE_SPARSE,
        "pax": tarfile.XHDTYPE,
        "global-pax": tarfile.XGLTYPE,
        "long-name": tarfile.GNUTYPE_LONGNAME,
        "long-link": tarfile.GNUTYPE_LONGLINK,
    }[change]
    header = bytearray(member.tobuf(format=tarfile.GNU_FORMAT))
    if change == "sparse":
        header[482] = 1
        header[148:156] = b"        "
        header[148:156] = f"{sum(header):06o}\0 ".encode()
        return body + bytes(header)
    return bytes(header) + data


@pytest.mark.parametrize("change", FRAMING_CASES)
@pytest.mark.parametrize("location", ["outer", "layer"])
def test_malformed_tar_api(api: Any, tmp_path: Path, location: str, change: str) -> None:
    """Reject malformed outer and layer TAR records through ValueError."""
    archive, expected = candidate(tmp_path, f"{location}-framing:{change}")
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


@pytest.mark.parametrize("change", FRAMING_CASES)
@pytest.mark.parametrize("location", ["outer", "layer"])
def test_malformed_tar_cli(tmp_path: Path, location: str, change: str) -> None:
    """Require failure JSON without a traceback for malformed TAR records."""
    archive, expected = candidate(tmp_path, f"{location}-framing:{change}")
    script = Path(__file__).parents[2] / "scripts/macos_capsule_candidate.py"
    process = subprocess.run(
        [sys.executable, str(script), str(archive), "--expected-payload", str(expected)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert process.returncode == 1
    assert not process.stdout
    result = json.loads(process.stderr)
    assert result["status"] == "FAIL"
    assert result["production_eligible"] is False


def candidate_metadata(value: Any, field: str, change: str) -> bytes:
    """Encode one metadata record while keeping all descriptor hashes consistent."""
    encoding = change.rsplit(":", 1)[1] if change.startswith(f"metadata:{field}:") else "utf-8"
    return json.dumps(value).encode(encoding)


@pytest.mark.parametrize(
    "change",
    ["layer-slash", "outer-slash"]
    + [
        f"metadata:{field}:{encoding}"
        for field in ("layout", "index", "manifest", "config")
        for encoding in ("utf-16", "utf-32")
    ],
)
@pytest.mark.parametrize("interface", ["api", "cli"])
def test_reject_raw_paths_and_metadata_encoding(api: Any, tmp_path: Path, change: str, interface: str) -> None:
    """Reject inputs that permissive TAR/JSON decoders would normalize or detect."""
    archive, expected = candidate(tmp_path, change)
    if interface == "api":
        with pytest.raises(ValueError):
            api.verify_candidate(archive, expected)
        return
    script = Path(__file__).parents[2] / "scripts/macos_capsule_candidate.py"
    process = subprocess.run(
        [sys.executable, str(script), str(archive), "--expected-payload", str(expected)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert process.returncode == 1
    assert json.loads(process.stderr)["status"] == "FAIL"


def candidate_gzip(raw: bytes, change: str) -> bytes:
    """Mutate gzip framing independently of the TAR and recompute OCI hashes."""
    layer = gzip.compress(raw, mtime=0)
    if change.startswith("gzip-flag:"):
        return layer[:3] + bytes([int(change.split(":")[1])]) + layer[4:]
    if change in ("gzip-crc-valid", "gzip-crc-invalid"):
        header = layer[:3] + b"\x02" + layer[4:10]
        crc = zlib.crc32(header) & 0xFFFF
        crc ^= int(change == "gzip-crc-invalid")
        return header + crc.to_bytes(2, "little") + layer[10:]
    suffix = {"gzip-concatenated": gzip.compress(b"", mtime=0), "gzip-trailing": b"junk", "gzip-zero": b"\0"}
    if change == "gzip-truncated":
        return layer[:-1]
    return layer + suffix.get(change, b"")


@pytest.mark.parametrize(
    "change",
    [
        "gzip-flag:32",
        "gzip-flag:64",
        "gzip-flag:128",
        "gzip-crc-invalid",
        "gzip-concatenated",
        "gzip-trailing",
        "gzip-zero",
        "gzip-truncated",
    ],
)
@pytest.mark.parametrize("interface", ["api", "cli"])
def test_reject_gzip_framing(api: Any, tmp_path: Path, change: str, interface: str) -> None:
    """Reject malformed gzip despite matching descriptors and unchanged TAR bytes."""
    archive, expected = candidate(tmp_path, change)
    if interface == "api":
        with pytest.raises(ValueError):
            api.verify_candidate(archive, expected)
        return
    script = Path(__file__).parents[2] / "scripts/macos_capsule_candidate.py"
    process = subprocess.run(
        [sys.executable, str(script), str(archive), "--expected-payload", str(expected)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert process.returncode == 1
    assert json.loads(process.stderr)["status"] == "FAIL"


def test_valid_gzip_header_crc(api: Any, tmp_path: Path) -> None:
    """Accept a correctly checksummed optional gzip header."""
    archive, expected = candidate(tmp_path, "gzip-crc-valid")
    assert api.verify_candidate(archive, expected)["status"] == "PASS"


def tar_format(data: bytes, case: str) -> bytes:
    """Set a physical magic/version pair and repair its checksum."""
    identifiers = {
        "unknown": b"BADMAG!!",
        "ustar-version": b"ustar\0!!",
        "gnu-version": b"ustar !!",
        "v7": bytes(8),
        "ustar": b"ustar\0" + b"00",
        "gnu": b"ustar  \0",
    }
    header = bytearray(data[:512])
    header[257:265] = identifiers[case]
    header[148:156] = b"        "
    header[148:156] = f"{sum(header):06o}\0 ".encode()
    return bytes(header) + data[512:]


@pytest.mark.parametrize("format_name", ["ustar", "gnu"])
@pytest.mark.parametrize("location", ["outer", "layer"])
def test_supported_tar_format(api: Any, tmp_path: Path, location: str, format_name: str) -> None:
    """Accept both explicitly supported ordinary TAR format identifiers."""
    archive, expected = candidate(tmp_path, f"{location}-framing:format:{format_name}")
    assert api.verify_candidate(archive, expected)["status"] == "PASS"
