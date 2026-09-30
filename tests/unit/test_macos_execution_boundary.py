"""Native execution-boundary receipts must fail closed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(name="boundary")
def fixture_boundary():
    """Load the standalone experimental boundary runner."""
    path = Path(__file__).parents[2] / "scripts/macos_execution_boundary/run.py"
    spec = importlib.util.spec_from_file_location("macos_boundary", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "case",
    [
        {"ready": False, "survivors": [], "emergency_cleanup": False},
        {"ready": True, "survivors": [42], "emergency_cleanup": True},
        {"ready": True, "survivors": [], "emergency_cleanup": True},
    ],
)
def test_failed_cases_cannot_pass(boundary, case):
    """Startup failure and emergency cleanup cannot become successful evidence."""
    assert boundary.case_passed(case) is False


def test_positive_control(boundary):
    """A ready run with no survivors or rescue can pass its individual case."""
    assert boundary.case_passed({"ready": True, "survivors": [], "emergency_cleanup": False})


@pytest.mark.parametrize("case", [{}, {"ready": True}, {"ready": True, "survivors": []}])
def test_incomplete_receipt_fails(boundary, case):
    """Missing evidence never becomes a passing case."""
    assert boundary.case_passed(case) is False


def test_reused_pid_not_same_process(boundary, monkeypatch):
    """Independent birth identity distinguishes a reused process identifier."""
    monkeypatch.setattr(boundary, "identity", lambda *_: {"pid": 42, "start_sec": 11, "start_usec": 7})
    assert not boundary.same_process(Path("observer"), {"pid": 42, "start_sec": 10, "start_usec": 7})


def test_cleanup_does_not_signal_reused_pid(boundary, monkeypatch):
    """Emergency cleanup never signals an identity already known to differ."""
    monkeypatch.setattr(boundary, "same_process", lambda *_: False)
    monkeypatch.setattr(boundary.os, "kill", lambda *_: pytest.fail("unexpected signal"))
    boundary.signal_exact(Path("observer"), {"pid": 42})


def test_partial_events_are_not_readiness(boundary, tmp_path):
    """Truncated JSON cannot manufacture a ready worker."""
    path = tmp_path / "events.jsonl"
    path.write_text('{"pid": 42}\n{"pid":')
    assert boundary.events(path) == [{"pid": 42}]


def test_intermediate_process_is_not_child_readiness(boundary):
    """Double-fork injection waits for the final child rather than an intermediate."""
    rows = [
        {"event": "ready", "role": "root", "pid": 10, "errno": 0},
        {"event": "ready", "role": "intermediate", "pid": 11, "errno": 0},
    ]
    assert not boundary.fixtures_ready(rows, {10: {}, 11: {}}, "double-fork")


def test_readiness_requires_successful_child(boundary):
    """An error event cannot substitute for a successfully launched subprocess."""
    rows = [
        {"event": "ready", "role": "root", "pid": 10, "errno": 0},
        {"event": "error", "role": "child", "pid": 11, "errno": 1},
    ]
    assert not boundary.fixtures_ready(rows, {10: {}, 11: {}}, "child")


def test_observer_failure_is_not_absence(boundary, monkeypatch):
    """A broken observer must raise instead of clearing live process evidence."""
    from types import SimpleNamespace

    monkeypatch.setattr(boundary.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=3, stdout=""))
    with pytest.raises(RuntimeError):
        boundary.identity(Path("observer"), 42)


def test_completion_requires_receipt(boundary):
    """Disappearance without a normal completion receipt is incomplete."""
    assert not boundary.completion_ok([], "hold", 0)


def test_completion_rejects_error_receipt(boundary):
    """A failed native receipt cannot pass through process disappearance."""
    assert not boundary.completion_ok(
        [{"event": "receipt", "reason": "exit", "ok": False, "root_reaped": True}], "hold", 0
    )
