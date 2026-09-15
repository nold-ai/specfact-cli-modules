"""Runtime payloads cannot retain external inode aliases or private build logs."""

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runtime_artifacts, runtime_builder
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError


@pytest.fixture(name="runtime_fixture")
def artifact_tree_fixture(tmp_path: Path):
    source, artifact = tmp_path / "source", tmp_path / "artifact"
    source.mkdir()
    (artifact / "site-packages").mkdir(parents=True)
    payload = artifact / "site-packages/customer.py"
    payload.write_text("VALUE = 1\n", encoding="utf-8")
    return discover_project(source), artifact, payload


def _seal(plan, artifact):
    return runtime_artifacts.seal_runtime(artifact, plan=plan, environment_id="test-abi", worker_identity="worker")


def _guard_bytes(monkeypatch: pytest.MonkeyPatch, forbidden: Path):
    original = Path.read_bytes

    def read(path):
        if path == forbidden:
            raise AssertionError("linked payload read before rejection")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)


@pytest.mark.parametrize("phase", ["build", "seal", "load"])
def test_linked_payload_is_rejected_before_read(runtime_fixture, tmp_path: Path, monkeypatch, phase: str) -> None:
    plan, artifact, payload = runtime_fixture
    prepared = _seal(plan, artifact) if phase == "load" else None
    os.link(payload, tmp_path / "external-alias")
    _guard_bytes(monkeypatch, payload)
    with pytest.raises(ProjectRuntimeError, match="hardlink"):
        if phase == "build":
            runtime_artifacts.validate_build_artifact(artifact)
        elif phase == "seal":
            _seal(plan, artifact)
        else:
            assert prepared is not None
            runtime_artifacts.load_runtime(
                prepared.descriptor_path, plan=plan, environment_id="test-abi", worker_identity="worker"
            )


def test_linked_descriptor_is_rejected_before_read(runtime_fixture, tmp_path: Path, monkeypatch) -> None:
    plan, artifact, _ = runtime_fixture
    prepared = _seal(plan, artifact)
    os.link(prepared.descriptor_path, tmp_path / "descriptor-alias")
    original = Path.read_text

    def read(path, *args, **kwargs):
        if path == prepared.descriptor_path:
            raise AssertionError("linked descriptor read before rejection")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(ProjectRuntimeError, match="hardlink"):
        runtime_artifacts.load_runtime(
            prepared.descriptor_path, plan=plan, environment_id="test-abi", worker_identity="worker"
        )


@pytest.mark.parametrize("linked_name", ["inventory.json", "site-packages/retained.log"])
def test_prepare_rejects_log_alias_before_inventory(tmp_path: Path, monkeypatch, linked_name: str) -> None:
    source = tmp_path / "source"
    source.mkdir()
    plan = discover_project(source)
    runtime = SimpleNamespace(environment_id="linux-x86_64-cp312", identity="worker", root=tmp_path / "capsule")
    cache = tmp_path / "cache"

    def build(_plan, _runtime, staging, *, build_log):
        artifact = staging / "artifact"
        (artifact / "site-packages").mkdir(parents=True)
        (artifact / "inventory.json").write_text("{}", encoding="utf-8")
        build_log.write(b"DISPOSABLE_PRIVATE_DIAGNOSTIC\n")
        build_log.flush()
        target = artifact / linked_name
        target.unlink(missing_ok=True)
        # Reconstruct the topology; this does not simulate Linux bind-mount traversal.
        os.link(build_log.name, target)
        return artifact

    original = Path.read_text

    def read(path, *args, **kwargs):
        if path.name == "inventory.json":
            raise AssertionError("inventory read before linked artifact rejection")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(runtime_builder, "_build", build)
    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(ProjectRuntimeError) as error:
        runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=cache)
    assert "hardlink" in str(error.value)
    assert "DISPOSABLE_PRIVATE_DIAGNOSTIC" not in str(error.value)
    logs = list(cache.glob("failed-*.log"))
    assert len(logs) == 1
    assert logs[0].read_text(encoding="utf-8") == "DISPOSABLE_PRIVATE_DIAGNOSTIC\n"
    assert logs[0].stat().st_nlink == 1
    assert not list(cache.glob("*/project-runtime.json"))
    assert not list(cache.glob(".preparing-*"))


def test_copied_distribution_aliases_produce_independent_payload(runtime_fixture, tmp_path: Path) -> None:
    plan, artifact, _ = runtime_fixture
    manager_cache = tmp_path / "manager-cache"
    environment = tmp_path / "environment"
    manager_cache.mkdir()
    environment.mkdir()
    cached = manager_cache / "distribution.py"
    cached.write_text("VALUE = 2\n", encoding="utf-8")
    os.link(cached, environment / cached.name)
    shutil.copytree(environment, artifact / "site-packages", dirs_exist_ok=True)
    runtime_artifacts.validate_build_artifact(artifact)
    prepared = _seal(plan, artifact)
    loaded = runtime_artifacts.load_runtime(
        prepared.descriptor_path, plan=plan, environment_id="test-abi", worker_identity="worker"
    )
    assert loaded.identity == prepared.identity
    assert (artifact / "site-packages" / cached.name).stat().st_nlink == 1
