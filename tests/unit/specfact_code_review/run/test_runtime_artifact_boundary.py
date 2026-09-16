"""Reject builder-owned filesystem indirection before controller-side processing."""

import json
import os
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runtime_artifacts, runtime_builder, runtime_native
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def _prepare_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_builder, "capture_public_trust", lambda _root: b"synthetic public trust")
    source = tmp_path / "source"
    source.mkdir()
    plan = discover_project(source)
    runtime = SimpleNamespace(
        environment_id="linux-x86_64-cp312", identity="sha256:" + "a" * 64, root=tmp_path / "capsule"
    )
    runtime.root.mkdir()
    monkeypatch.setattr(runtime_builder, "analyzer_dependency_conflicts", lambda *_args: {})
    monkeypatch.setattr(runtime_builder, "member_dependency_graphs", lambda *_args: {})
    return plan, runtime


def _artifact(staging: Path) -> Path:
    artifact = staging / "artifact"
    (artifact / "site-packages").mkdir(parents=True)
    (artifact / "inventory.json").write_text("{}")
    return artifact


def _mutate_artifact(artifact: Path, outside: Path, mutation: str) -> Path:
    if mutation == "root":
        artifact.rename(outside / "payload")
        artifact.symlink_to(outside / "payload", target_is_directory=True)
        return artifact
    if mutation == "native-directory":
        (artifact / "native").symlink_to(outside, target_is_directory=True)
        return artifact
    if mutation == "inventory":
        (artifact / "inventory.json").unlink()
        (artifact / "inventory.json").symlink_to(outside / "sentinel.json")
        return artifact
    if mutation == "nested-file":
        (artifact / "site-packages/customer.so").symlink_to(outside / "sentinel.json")
        return artifact
    os.mkfifo(artifact / "site-packages/customer.fifo")
    return artifact


@pytest.mark.parametrize("mutation", ["root", "native-directory", "inventory", "nested-file", "fifo"])
def test_prepare_rejects_artifact_topology_before_inventory_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    plan, runtime = _prepare_fixture(tmp_path, monkeypatch)
    outside = tmp_path / "simulated-host"
    outside.mkdir()
    sentinel = outside / "sentinel.json"
    sentinel.write_text('{"private": "disposable sentinel"}')
    original = sentinel.read_bytes()

    def build(_plan, _runtime, staging, **_kwargs):
        return _mutate_artifact(_artifact(staging), outside, mutation)

    original_read_text = Path.read_text

    def guarded_read(path, *args, **kwargs):
        if path.name == "inventory.json":
            raise AssertionError("controller read inventory before rejecting untrusted artifact topology")
        return original_read_text(path, *args, **kwargs)

    def forbidden_native(*_args, **_kwargs):
        raise AssertionError("controller entered native enrichment before rejecting untrusted artifact topology")

    monkeypatch.setattr(runtime_builder, "_build", build)
    monkeypatch.setattr(Path, "read_text", guarded_read)
    monkeypatch.setattr(runtime_builder, "inventory_native", forbidden_native)
    with pytest.raises(ProjectRuntimeError) as error:
        runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache")
    assert "project_runtime_build_artifact_invalid" in str(error.value)
    assert sentinel.read_bytes() == original


def test_prepare_native_directory_cannot_overwrite_external_sentinels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, runtime = _prepare_fixture(tmp_path, monkeypatch)
    outside, system = tmp_path / "simulated-host", tmp_path / "system-fixtures"
    outside.mkdir()
    system.mkdir()
    payload = bytearray(64)
    payload[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", payload, 18, 62)
    names = ("libreviewfixture.so", "ld-linux-x86-64.so.2")
    for name in names:
        (system / name).write_bytes(payload)
        (outside / name).write_bytes(b"UNCHANGED-SENTINEL")

    def build(_plan, _runtime, staging, **_kwargs):
        return _mutate_artifact(_artifact(staging), outside, "native-directory")

    def native(artifact, **kwargs):
        return runtime_native.inventory_native(
            artifact,
            capsule_root=kwargs["capsule_root"],
            declared=(names[0],),
            system_roots=(system,),
            target_loader=True,
        )

    monkeypatch.setattr(runtime_builder, "_build", build)
    monkeypatch.setattr(runtime_builder, "inventory_native", native)
    with pytest.raises(ProjectRuntimeError):
        runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache")
    assert all((outside / name).read_bytes() == b"UNCHANGED-SENTINEL" for name in names)


def test_regular_artifact_remains_sealed_and_reusable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan, runtime = _prepare_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_builder, "_build", lambda _plan, _runtime, staging, **_kwargs: _artifact(staging))
    monkeypatch.setattr(runtime_builder, "inventory_native", lambda *_args, **_kwargs: [])
    prepared = runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache")
    reused = runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache", offline=True)
    assert reused.identity == prepared.identity
    assert (
        json.loads(prepared.descriptor_path.read_text(encoding="utf-8"))["payload"]["inventory.json"]["kind"] == "file"
    )


def test_build_artifact_validation_never_reads_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = _artifact(tmp_path)

    def forbidden_read(*_args, **_kwargs):
        raise AssertionError("topology validation must not read payload bytes")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    monkeypatch.setattr(Path, "read_text", forbidden_read)
    runtime_artifacts.validate_build_artifact(artifact)
