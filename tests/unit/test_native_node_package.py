"""The offline native Node packager rejects unsafe or unpinned inputs."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import struct
import sys
import tarfile
from pathlib import Path

import pytest


NODE_PREFIX = "node-v24.16.0-darwin-arm64"
ARM64 = struct.pack("<8I", 0xFEEDFACF, 0x100000C, 0, 2, 0, 0, 0, 0)
METADATA = {
    "name": "basedpyright",
    "version": "1.39.10",
    "license": "MIT",
    "bin": {"basedpyright": "index.js"},
    "optionalDependencies": {"fsevents": "~2.3.3"},
}


@pytest.fixture(name="packager")
def fixture_packager():
    """Load the script without executing its command-line entry point."""
    path = Path(__file__).parents[2] / "scripts/native_node_package.py"
    spec = importlib.util.spec_from_file_location("native_node_package", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive(path, members):
    """Write test tarballs with explicit member kinds and bytes."""
    with tarfile.open(path, "w:gz") as output:
        for name, data, kind in members:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.mode = 0o755 if name.endswith("bin/node") else 0o644
            member.size = len(data) if kind == tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = "../../outside"
            output.addfile(member, io.BytesIO(data) if member.size else None)
    return path


@pytest.fixture(name="inputs")
def fixture_inputs(tmp_path, packager, monkeypatch):
    """Build pinned synthetic archives inside this test's isolated directory."""

    def build_inputs(node=ARM64, metadata=None, extra=()):
        """Select only the payload variations required by a test."""
        node_path = archive(
            tmp_path / "node.tgz",
            [
                (NODE_PREFIX + "/bin/node", node, tarfile.REGTYPE),
                (NODE_PREFIX + "/LICENSE", b"Node license", tarfile.REGTYPE),
            ],
        )
        npm_path = archive(
            tmp_path / "npm.tgz",
            [
                (
                    "package/package.json",
                    json.dumps(METADATA if metadata is None else metadata).encode(),
                    tarfile.REGTYPE,
                ),
                ("package/index.js", b"// controlled test", tarfile.REGTYPE),
                ("package/LICENSE.txt", b"MIT", tarfile.REGTYPE),
                *extra,
            ],
        )
        monkeypatch.setattr(packager, "NODE_SHA256", hashlib.sha256(node_path.read_bytes()).hexdigest())
        integrity = "sha512-" + base64.b64encode(hashlib.sha512(npm_path.read_bytes()).digest()).decode()
        monkeypatch.setattr(packager, "NPM_INTEGRITY", integrity)
        return node_path, npm_path

    return build_inputs


def test_offline_payload_and_explicit_launch(packager, tmp_path, monkeypatch, inputs):
    node, npm = inputs()
    monkeypatch.setenv("PATH", "/hostile-or-empty")
    out = tmp_path / "output with spaces"
    result = packager.package(node, npm, out)
    assert result["experimental"] is True
    assert result["dependency_admitted"] is False
    assert result["production_eligible"] is False
    assert (out / "bin/node").read_bytes() == ARM64
    assert (out / "bin/node").stat().st_mode & 0o777 == 0o755
    assert packager.basedpyright_argv(out) == (str(out / "bin/node"), str(out / "basedpyright/index.js"))
    assert_payload_manifest(out, result)


def assert_payload_manifest(root, manifest):
    """Verify every emitted file is bound to its manifest digest."""
    payload = manifest["files"]
    assert set(payload) == {
        "bin/node",
        "licenses/node.txt",
        "basedpyright/package.json",
        "basedpyright/index.js",
        "basedpyright/LICENSE.txt",
    }
    for name, entry in payload.items():
        assert entry["sha256"] == hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert json.loads((root / "manifest.json").read_text()) == manifest


@pytest.mark.parametrize("which", ["node", "npm"])
def test_digest_failure_before_output(packager, tmp_path, which, inputs):
    node, npm = inputs()
    target = node if which == "node" else npm
    target.write_bytes(target.read_bytes() + b"tampered")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="digest"):
        packager.package(node, npm, out)
    assert not out.exists()


@pytest.mark.parametrize(
    "name,kind",
    [
        ("package/../escape", tarfile.REGTYPE),
        ("/package/absolute", tarfile.REGTYPE),
        ("package/alias", tarfile.SYMTYPE),
        ("package/hard", tarfile.LNKTYPE),
        ("package/device", tarfile.CHRTYPE),
        ("package/index.js", tarfile.REGTYPE),
        ("package/INDEX.js", tarfile.REGTYPE),
        ("package/a\\b", tarfile.REGTYPE),
    ],
)
def test_unsafe_archive_never_leaves_output(packager, tmp_path, name, kind, inputs):
    node, npm = inputs(extra=[(name, b"bad", kind)])
    with pytest.raises(ValueError):
        packager.package(node, npm, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"name": "wrong"},
        {"version": "0"},
        {"license": "unknown"},
        {"dependencies": {"surprise": "1"}},
        {"optionalDependencies": {}},
        {"bin": {"basedpyright": "missing.js"}},
    ],
)
def test_inconsistent_package_fields_rejected(packager, tmp_path, change, inputs):
    node, npm = inputs(metadata=METADATA | change)
    with pytest.raises(ValueError, match="metadata"):
        packager.package(node, npm, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("binary", [b"not macho", struct.pack("<8I", 0xFEEDFACF, 0x1000007, 0, 2, 0, 0, 0, 0)])
def test_non_arm64_node_rejected(packager, tmp_path, binary, inputs):
    node, npm = inputs(node=binary)
    with pytest.raises(ValueError, match="ARM64"):
        packager.package(node, npm, tmp_path / "out")


def test_existing_output_preserved(packager, tmp_path, inputs):
    node, npm = inputs()
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep").write_text("keep")
    with pytest.raises(FileExistsError):
        packager.package(node, npm, out)
    assert (out / "keep").read_text() == "keep"


def test_dangling_output_symlink_preserved(packager, tmp_path, inputs):
    node, npm = inputs()
    out = tmp_path / "out"
    out.symlink_to(tmp_path / "absent", target_is_directory=True)
    with pytest.raises(FileExistsError):
        packager.package(node, npm, out)
    assert out.is_symlink()
    assert not (tmp_path / "absent").exists()


def test_compressed_size_budget(packager, tmp_path, monkeypatch, inputs):
    node, npm = inputs()
    monkeypatch.setattr(packager, "MAX_ARCHIVE_BYTES", 4)
    with pytest.raises(ValueError, match="limit"):
        packager.package(node, npm, tmp_path / "out")


def test_payload_write_failure_removes_owned_output(packager, tmp_path, monkeypatch, inputs):
    node, npm = inputs()
    original = Path.write_bytes

    def broken(path, data):
        if path.name == "index.js":
            raise OSError("fixture write failed")
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", broken)
    with pytest.raises(OSError):
        packager.package(node, npm, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("budget", [("MAX_EXPANDED_BYTES", 1), ("MAX_MEMBERS", 1)])
def test_archive_resource_budgets(packager, tmp_path, monkeypatch, budget, inputs):
    """Authenticated input still obeys the maintainer resource budget."""
    node, npm = inputs()
    limit, value = budget
    monkeypatch.setattr(packager, limit, value)
    with pytest.raises(ValueError, match="limit"):
        packager.package(node, npm, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_repeated_outputs_are_identical(packager, tmp_path, inputs):
    """Location changes do not change the payload manifest or emitted bytes."""
    node, npm = inputs()
    first, second = tmp_path / "first", tmp_path / "second"
    assert packager.package(node, npm, first) == packager.package(node, npm, second)
    for path in first.rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()


@pytest.mark.parametrize("metadata", [[], "basedpyright", 1, {**METADATA, "bin": []}])
def test_malformed_package_fields_rejected(packager, tmp_path, inputs, metadata):
    """Malformed metadata fails before any output is created."""
    node, npm = inputs(metadata=metadata)
    with pytest.raises(ValueError, match="unsupported BasedPyright metadata"):
        packager.package(node, npm, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_file_directory_conflict_rejected(packager, tmp_path, inputs):
    """A payload file cannot also be a parent of another payload file."""
    node, npm = inputs(extra=[("package/index.js/child", b"conflict", tarfile.REGTYPE)])
    with pytest.raises(ValueError, match="file/directory path conflict"):
        packager.package(node, npm, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_cli_json_receipt(packager, tmp_path, inputs, monkeypatch, capsys):
    """The CLI emits one JSON receipt and a trailing newline on stdout."""
    node, npm = inputs()
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        ["native_node_package", "--node-archive", str(node), "--basedpyright-archive", str(npm), "--output", str(out)],
    )
    assert packager.main() == 0
    captured = capsys.readouterr()
    assert captured.out == json.dumps({"output": str(out.resolve()), "files": 5, "production_eligible": False}) + "\n"
    assert captured.err == ""
