"""Bound OCI allocation without weakening signed extraction checks."""

from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from specfact_code_review.run import toolchain


def test_signed_budget_does_not_become_a_decompressor_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"small verified layer"
    payload = gzip.compress(content)
    original_read = gzip.GzipFile.read
    requests: list[int] = []

    def bounded_read(self: gzip.GzipFile, size: int = -1) -> bytes:
        requests.append(size)
        assert 0 < size <= 1024 * 1024, "the signed ceiling is not a buffer allocation size"
        return original_read(self, size)

    monkeypatch.setattr(gzip.GzipFile, "read", bounded_read)
    assert toolchain._bounded_gzip_decompress(payload, max_bytes=4 * 1024**3) == content
    assert requests


@pytest.mark.parametrize("size", [0, 1, 1024 * 1024, 1024 * 1024 + 1])
def test_decompression_retains_exact_bound_and_one_byte_overflow(size: int) -> None:
    content = b"x" * size
    assert toolchain._bounded_gzip_decompress(gzip.compress(content), max_bytes=size) == content
    with pytest.raises(ValueError, match="signed unpacked-byte bound"):
        toolchain._bounded_gzip_decompress(gzip.compress(content + b"x"), max_bytes=size)


def _layer(names: tuple[str, ...]) -> tuple[bytes, dict[str, object]]:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:") as archive:
        for name in names:
            member = tarfile.TarInfo(name)
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))
    raw = stream.getvalue()
    payload = gzip.compress(raw)
    return payload, {
        "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "diff_id": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }


@pytest.mark.parametrize("field", ["digest", "diff_id"])
def test_layer_digest_rejection_precedes_filesystem_changes(tmp_path: Path, field: str) -> None:
    root = tmp_path / "root"
    root.mkdir()
    marker = root / "keep"
    marker.write_bytes(b"unchanged")
    payload, descriptor = _layer(("keep",))
    descriptor[field] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match=r"digest mismatch|diff-ID mismatch"):
        toolchain._apply_oci_layer(root, payload, descriptor)
    assert marker.read_bytes() == b"unchanged"
    assert list(root.iterdir()) == [marker]


@pytest.mark.parametrize("names,max_files", [(("keep", "./keep"), 2), (("keep", "other"), 1)])
def test_archive_count_and_duplicate_checks_remain_before_application(
    tmp_path: Path, names: tuple[str, ...], max_files: int
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    marker = root / "keep"
    marker.write_bytes(b"unchanged")
    payload, descriptor = _layer(names)
    with pytest.raises(ValueError, match=r"duplicate paths|signed file-count bound"):
        toolchain._apply_oci_layer(root, payload, descriptor, max_files=max_files)
    assert marker.read_bytes() == b"unchanged"
    assert list(root.iterdir()) == [marker]
