"""Maintainer-only uv build boundary tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts import build_macos_managed_uv as builder


def _git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


@pytest.fixture
def upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = tmp_path / "upstream"
    source.mkdir()
    _git("init", "-q", cwd=source)
    _git("config", "user.email", "test@example.invalid", cwd=source)
    _git("config", "user.name", "Test", cwd=source)
    for name, data in {
        "Cargo.lock": "pinned lock\n",
        "Cargo.toml": "[workspace]\n",
        "LICENSE-MIT": "MIT license\n",
        "LICENSE-APACHE": "Apache license\n",
    }.items():
        (source / name).write_text(data)
    _git("add", ".", cwd=source)
    _git("commit", "-qm", "fixture", cwd=source)
    monkeypatch.setattr(builder, "UPSTREAM_COMMIT", _git("rev-parse", "HEAD", cwd=source))
    monkeypatch.setattr(builder, "LOCK_SHA256", hashlib.sha256((source / "Cargo.lock").read_bytes()).hexdigest())
    return source


def test_source_rejects_dirty_substituted_and_untracked_inputs(upstream: Path) -> None:
    builder.validate_source(upstream)
    (upstream / "Cargo.lock").write_text("changed\n")
    with pytest.raises(ValueError, match="dirty"):
        builder.validate_source(upstream)
    _git("checkout", "--", "Cargo.lock", cwd=upstream)
    (upstream / "new.rs").write_text("untracked")
    with pytest.raises(ValueError, match="dirty"):
        builder.validate_source(upstream)
    (upstream / "new.rs").unlink()
    with pytest.raises(ValueError, match="commit"):
        builder.validate_source(upstream, expected_commit="0" * 40)


def test_lock_and_reviewed_inputs_are_pinned(upstream: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "LOCK_SHA256", "0" * 64)
    with pytest.raises(ValueError, match=r"Cargo\.lock"):
        builder.validate_source(upstream)
    with pytest.raises(ValueError, match="reviewed patch"):
        builder.validate_reviewed_inputs(builder.REPOSITORY_ROOT / "missing.patch", builder.BRIDGE)


def test_build_command_is_locked_offline_and_private(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    toolchain = tmp_path / "rust"
    cargo_home = tmp_path / "cargo-home"
    command, environment = builder.cargo_invocation(source, target, toolchain, cargo_home)
    assert command == [
        str(toolchain / "bin/cargo"),
        "build",
        "--locked",
        "--offline",
        "--release",
        "--bin",
        "uv",
        "--no-default-features",
    ]
    assert environment["CARGO_HOME"] == str(cargo_home)
    assert environment["CARGO_TARGET_DIR"] == str(target)
    assert environment["CARGO_NET_OFFLINE"] == "true"


def test_candidate_admission_rejects_substituted_binary_before_copy(tmp_path: Path, upstream: Path):
    binary = tmp_path / "uv"
    binary.write_bytes(b"signed fixture")
    toolchain = tmp_path / "rust"
    (toolchain / "bin").mkdir(parents=True)
    for name in ("rustc", "cargo"):
        (toolchain / "bin" / name).write_bytes(b"tool")
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    builder.write_artifacts(artifact, binary, "1.96.0", upstream, toolchain, "e" * 64)
    builder.validate_artifact(artifact)
    (artifact / "bin/uv").write_bytes(b"substituted")
    with pytest.raises(ValueError, match="digest"):
        builder.validate_artifact(artifact)


def test_output_provenance_records_signed_binary_and_inputs(tmp_path: Path, upstream: Path) -> None:
    binary = tmp_path / "uv"
    binary.write_bytes(b"signed arm64 fixture")
    toolchain = tmp_path / "rust"
    (toolchain / "bin").mkdir(parents=True)
    for name in ("rustc", "cargo"):
        (toolchain / "bin" / name).write_bytes(name.encode())
    output = tmp_path / "output"
    output.mkdir()
    artifacts = builder.write_artifacts(output, binary, "1.96.0", upstream, toolchain, "a" * 64)
    provenance = json.loads(artifacts["provenance"].read_text())
    assert provenance["upstream_commit"] == builder.UPSTREAM_COMMIT
    assert provenance["cargo_lock_sha256"] == builder.LOCK_SHA256
    assert provenance["source_archive_sha256"] == "a" * 64
    assert provenance["toolchain_sha256"]["rustc"] == hashlib.sha256(b"rustc").hexdigest()
    assert provenance["signature"] == {
        "mode": "adhoc",
        "identifier": builder.SIGNING_IDENTIFIER,
        "hardened_runtime": True,
    }
    assert provenance["binary_sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()
    for name in ("LICENSE-MIT", "LICENSE-APACHE", "uv-managed-launch.patch", "uv_managed.rs"):
        assert (output / "licenses" / name).is_file() or (output / "sources" / name).is_file()


def test_existing_output_fails_before_build(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(ValueError, match="output"):
        builder.require_new_output(output)


def test_non_arm64_host_fails_before_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder.platform, "machine", lambda: "x86_64")
    with pytest.raises(ValueError, match="macOS ARM64"):
        builder.build(tmp_path / "missing", tmp_path / "output", tmp_path / "rust", tmp_path / "cargo")
