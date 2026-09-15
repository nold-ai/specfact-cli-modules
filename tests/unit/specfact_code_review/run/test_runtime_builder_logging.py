"""Untrusted build paths never select controller log files or retention targets."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runtime_build_driver, runtime_builder
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError
from specfact_code_review.run.runtime_sources import source_identity


KEY = "b" * 64
SUCCESS_SCRIPT = (
    "(staging/'artifact/site-packages').mkdir(parents=True); "
    "(staging/'artifact/inventory.json').write_text('{}'); print('success')"
)


def _capture_subprocess(monkeypatch, *, timeout: bool = False):
    captures = []
    native_run = subprocess.run

    def execute(command, **kwargs):
        captures.append(kwargs.get("stdout"))
        if timeout:
            kwargs["timeout"] = 0.3
        return native_run(command, check=kwargs.pop("check", False), **kwargs)

    monkeypatch.setattr(subprocess, "run", execute)
    return captures


def _builder(tmp_path: Path, monkeypatch, script: str, *, timeout: bool = False):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    plan = ProjectPlan(source, manager="pip", source_identity=source_identity(source))
    runtime = SimpleNamespace(
        root=tmp_path / "capsule",
        interpreter="/opt/specfact/python/bin/python",
        bubblewrap="bwrap",
        environment_id="linux-x86_64-cp312",
        identity="sha256:" + "a" * 64,
    )
    monkeypatch.setattr(runtime_builder, "stage_git", lambda *_args: None)
    monkeypatch.setattr(runtime_builder, "git_identity", lambda: "fixed-git")
    monkeypatch.setattr(runtime_builder, "document_digest", lambda _value: "sha256:" + KEY)
    monkeypatch.setattr(
        runtime_builder.sandbox, "_verified_bubblewrap_descriptor", lambda *_args: os.open(os.devnull, os.O_RDONLY)
    )
    monkeypatch.setattr(
        runtime_builder,
        "builder_command",
        lambda _runtime, *, staging, executable: [
            sys.executable,
            "-c",
            "import os,sys,time; from pathlib import Path; staging=Path(sys.argv[1]); " + script,
            str(staging),
        ],
    )
    captures = _capture_subprocess(monkeypatch, timeout=timeout)
    return plan, runtime, tmp_path / "cache", captures


def _retained_logs(cache: Path) -> list[Path]:
    return [path for path in cache.glob("failed-*.log") if not path.is_symlink() and path.is_file()]


def _failed_build(plan, runtime, cache: Path) -> ProjectRuntimeError:
    with pytest.raises(ProjectRuntimeError) as failure:
        runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=cache)
    assert not list(cache.glob(".preparing-*"))
    return failure.value


def test_staging_log_symlink_cannot_write_or_read_host_sentinel(tmp_path: Path, monkeypatch) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("PRIVATE_SENTINEL_UNCHANGED\n")
    script = f"(staging/'build.log').symlink_to({str(sentinel)!r}); print('private-builder-output'); sys.exit(1)"
    plan, runtime, cache, captures = _builder(tmp_path, monkeypatch, script)
    error = _failed_build(plan, runtime, cache)
    assert sentinel.read_text() == "PRIVATE_SENTINEL_UNCHANGED\n"
    logs = _retained_logs(cache)
    assert len(logs) == 1
    assert logs[0].read_text() == "private-builder-output\n"
    assert str(logs[0]) in str(error)
    assert "private-builder-output" not in str(error)
    assert logs[0].stat().st_mode & 0o777 == 0o600
    assert captures[0] is not None and captures[0].closed


@pytest.mark.parametrize("kind", ["fifo", "directory"])
def test_controller_never_opens_special_staging_log(tmp_path: Path, monkeypatch, kind: str) -> None:
    operation = "os.mkfifo(staging/'build.log')" if kind == "fifo" else "(staging/'build.log').mkdir()"
    plan, runtime, cache, _ = _builder(tmp_path, monkeypatch, operation + "; print('build-failed'); sys.exit(1)")
    native_open = Path.open

    def checked_open(path, *args, **kwargs):
        if path.name == "build.log" and path.parent.name.startswith(".preparing-"):
            raise AssertionError("controller attempted an untrusted special-file open")
        return native_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    _failed_build(plan, runtime, cache)
    assert _retained_logs(cache)[0].read_text() == "build-failed\n"


@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory"])
def test_failure_retention_never_reopens_predictable_destination(tmp_path: Path, monkeypatch, kind: str) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("UNCHANGED\n")
    plan, runtime, cache, _ = _builder(tmp_path, monkeypatch, "print('build-failed'); sys.exit(1)")
    cache.mkdir()
    old_name = cache / f"failed-{KEY}.log"
    if kind == "symlink":
        old_name.symlink_to(sentinel)
    elif kind == "fifo":
        os.mkfifo(old_name)
    else:
        old_name.mkdir()
    error = _failed_build(plan, runtime, cache)
    assert sentinel.read_text() == "UNCHANGED\n"
    logs = _retained_logs(cache)
    assert len(logs) == 1
    assert logs[0] != old_name and str(logs[0]) in str(error)
    assert logs[0].read_text() == "build-failed\n"


def test_timeout_retains_private_partial_output_and_closes_descriptor(tmp_path: Path, monkeypatch) -> None:
    plan, runtime, cache, captures = _builder(
        tmp_path, monkeypatch, "print('partial-builder-output', flush=True); time.sleep(10)", timeout=True
    )
    error = _failed_build(plan, runtime, cache)
    logs = _retained_logs(cache)
    assert len(logs) == 1 and logs[0].read_text() == "partial-builder-output\n"
    assert "partial-builder-output" not in str(error)
    assert captures[0] is not None and captures[0].closed


def test_launch_failure_closes_descriptor_and_retains_private_log(tmp_path: Path, monkeypatch) -> None:
    plan, runtime, cache, captures = _builder(tmp_path, monkeypatch, "pass")
    monkeypatch.setattr(
        runtime_builder, "builder_command", lambda *_args, **_kwargs: [str(tmp_path / "missing-builder")]
    )
    error = _failed_build(plan, runtime, cache)
    logs = _retained_logs(cache)
    assert len(logs) == 1 and str(logs[0]) in str(error)
    assert logs[0].read_text() == ""
    assert captures[0].closed


def test_log_creation_failure_never_starts_builder_or_claims_retained_log(tmp_path: Path, monkeypatch) -> None:
    plan, runtime, cache, captures = _builder(tmp_path, monkeypatch, "pass")

    def unavailable_log(**_kwargs):
        raise OSError("private log creation failed")

    monkeypatch.setattr(runtime_builder.tempfile, "NamedTemporaryFile", unavailable_log)
    with pytest.raises(OSError, match=r"^private log creation failed$"):
        runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=cache)
    assert not captures and not list(cache.iterdir())


def test_success_closes_and_removes_private_build_log(tmp_path: Path, monkeypatch) -> None:
    plan, runtime, cache, captures = _builder(tmp_path, monkeypatch, SUCCESS_SCRIPT)
    monkeypatch.setattr(runtime_builder, "inventory_native", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runtime_builder, "analyzer_dependency_conflicts", lambda *_args: {})
    monkeypatch.setattr(runtime_builder, "member_dependency_graphs", lambda *_args: {})
    prepared = runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=cache)
    assert prepared.descriptor_path.is_file()
    assert not list(cache.glob("failed-*.log")) and not list(cache.glob(".preparing-*"))
    assert captures[0] is not None and captures[0].closed


@pytest.mark.parametrize("stage", ["inventory_native", "seal_runtime", "publish_artifact", "load_runtime"])
def test_downstream_failure_retains_log_and_original_diagnostic(tmp_path: Path, monkeypatch, stage: str) -> None:
    plan, runtime, cache, captures = _builder(tmp_path, monkeypatch, SUCCESS_SCRIPT)
    monkeypatch.setattr(runtime_builder, "inventory_native", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runtime_builder, "analyzer_dependency_conflicts", lambda *_args: {})
    monkeypatch.setattr(runtime_builder, "member_dependency_graphs", lambda *_args: {})

    def failed_stage(*_args, **_kwargs):
        raise ProjectRuntimeError("project_native_library_missing:libcustomer.so")

    monkeypatch.setattr(runtime_builder, stage, failed_stage)
    error = _failed_build(plan, runtime, cache)
    logs = _retained_logs(cache)
    assert len(logs) == 1 and logs[0].read_text() == "success\n"
    assert "project_native_library_missing:libcustomer.so" in str(error)
    assert str(logs[0]) in str(error)
    assert captures[0].closed


def test_driver_forwards_diagnostics_without_opening_builder_log(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "project").mkdir()
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("UNCHANGED\n")
    (tmp_path / "build.log").symlink_to(sentinel)
    monkeypatch.setattr(runtime_build_driver, "ROOT", tmp_path)
    output = runtime_build_driver._run(
        [sys.executable, "-c", "import sys; print('native-out'); print('native-err', file=sys.stderr)"]
    )
    assert output == "native-out"
    assert sentinel.read_text() == "UNCHANGED\n"
    assert capsys.readouterr().out == "native-out\nnative-err\n"


def test_driver_forwards_native_timeout_partial_output(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "project").mkdir()
    monkeypatch.setattr(runtime_build_driver, "ROOT", tmp_path)
    _capture_subprocess(monkeypatch, timeout=True)
    with pytest.raises(subprocess.TimeoutExpired):
        runtime_build_driver._run(
            [sys.executable, "-c", "import time; print('native-partial', flush=True); time.sleep(10)"]
        )
    assert capsys.readouterr().out == "native-partial\n"
