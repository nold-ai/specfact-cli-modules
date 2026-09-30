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
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(name="api")
def fixture_candidate_api() -> Any:
    path = Path(__file__).parents[2] / "scripts/macos_capsule_candidate.py"
    spec = importlib.util.spec_from_file_location("macos_capsule_candidate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tar_bytes(entries: list[tuple[str, bytes, bytes, int]]) -> bytes:
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
    entries = [
        ("proof", b"", tarfile.DIRTYPE, 0o755),
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
    layer = gzip.compress(raw, mtime=0)
    if change == "invalid-deflate":
        layer = bytes.fromhex("1f8b0800000000000000") + b"\xff" * 16
    return raw, layer


def candidate_descriptor(blobs: dict[str, bytes], data: bytes, media: str) -> dict[str, Any]:
    identity = digest(data)
    blobs["blobs/sha256/" + identity.split(":")[1]] = data
    return {"digest": identity, "size": len(data), "mediaType": media}


def candidate_config(raw: bytes, change: str) -> Any:
    config: Any = {"os": "darwin", "architecture": "arm64", "rootfs": {"type": "layers", "diff_ids": [digest(raw)]}}
    if change in ("linux", "amd64"):
        config["os" if change == "linux" else "architecture"] = change
    if change == "diffid":
        config["rootfs"]["diff_ids"] = [digest(b"wrong")]
    if change == "config-type":
        config = []
    return config


def candidate_manifest(
    blobs: dict[str, bytes], layer_desc: dict[str, Any], config_desc: dict[str, Any], change: str
) -> dict[str, Any]:
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
    manifest_desc["platform"] = {"os": "linux" if change == "index-platform" else "darwin", "architecture": "arm64"}
    index: Any = {"schemaVersion": 2, "manifests": [manifest_desc]}
    if change == "index-version-type":
        index["schemaVersion"] = 2.0
    if change == "index-type":
        index = []
    return index


def candidate_outer(blobs: dict[str, bytes], index: Any, change: str) -> bytes:
    outer = [
        ("oci-layout", b'{"imageLayoutVersion":"1.0.0"}', tarfile.REGTYPE, 0o644),
        ("index.json", json.dumps(index).encode(), tarfile.REGTYPE, 0o644),
    ]
    outer.extend((name, data, tarfile.REGTYPE, 0o644) for name, data in blobs.items())
    if change == "outer-duplicate":
        outer.append(outer[1])
    if change == "outer-link":
        outer.append(("other", b"", tarfile.SYMTYPE, 0o644))
    extra_entries = {
        "outer-extra": ("unchecked", b"extra", tarfile.REGTYPE, 0o644),
        "outer-blob": ("blobs/sha256/" + "0" * 64, b"extra", tarfile.REGTYPE, 0o644),
        "outer-directory": ("unchecked", b"", tarfile.DIRTYPE, 0o755),
    }
    if change in extra_entries:
        outer.append(extra_entries[change])
    return tar_bytes(outer)


def candidate(tmp_path: Path, change: str = "") -> tuple[Path, Path]:
    expected = tmp_path / "expected"
    expected.mkdir()
    (expected / "hello").write_bytes(b"operator-supplied native bytes")
    (expected / "hello").chmod(0o755)
    raw, layer = candidate_layers(expected, change)
    blobs: dict[str, bytes] = {}
    config = candidate_config(raw, change)
    layer_desc = candidate_descriptor(blobs, layer, "application/vnd.oci.image.layer.v1.tar+gzip")
    config_desc = candidate_descriptor(blobs, json.dumps(config).encode(), "application/vnd.oci.image.config.v1+json")
    manifest = candidate_manifest(blobs, layer_desc, config_desc, change)
    manifest_desc = candidate_descriptor(
        blobs, json.dumps(manifest).encode(), "application/vnd.oci.image.manifest.v1+json"
    )
    index = candidate_index(manifest_desc, change)
    path = tmp_path / "candidate.tar"
    path.write_bytes(candidate_outer(blobs, index, change))
    return path, expected


def test_valid_candidate_is_never_production_evidence(api: Any, tmp_path: Path) -> None:
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
        "outer-extra",
        "outer-blob",
        "outer-directory",
    ],
)
def test_reject_invalid_candidate(api: Any, tmp_path: Path, change: str) -> None:
    archive, expected = candidate(tmp_path, change)
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


def test_bounded_decompression(api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive, expected = candidate(tmp_path)
    monkeypatch.setattr(api, "MAX_LAYER_BYTES", 1024)
    with pytest.raises(ValueError, match="limit"):
        api.verify_candidate(archive, expected)


def test_operator_tree_links_rejected(api: Any, tmp_path: Path) -> None:
    archive, expected = candidate(tmp_path)
    (expected / "alias").symlink_to(expected / "hello")
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


def test_malformed_gzip_is_value_error(api: Any, tmp_path: Path) -> None:
    archive, expected = candidate(tmp_path, "invalid-deflate")
    with pytest.raises(ValueError):
        api.verify_candidate(archive, expected)


@pytest.mark.parametrize("case", [("", 0), ("linux", 1)], ids=["-0", "linux-1"])
def test_cli_local_only_json(tmp_path: Path, case: tuple[str, int]) -> None:
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
