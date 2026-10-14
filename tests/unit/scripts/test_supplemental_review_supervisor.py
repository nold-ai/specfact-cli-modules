"""Owned process timeout distinctions and finite cleanup behavior."""

import importlib.util
import json
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from specfact_code_review.run import supplemental_diagnostics as diagnostic


spec = importlib.util.spec_from_file_location(
    "supplemental_supervisor", Path(__file__).parents[3] / "scripts/supplemental_review_supervisor.py"
)
assert spec and spec.loader
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


@pytest.fixture
def observation(tmp_path):
    directory = tmp_path / "observations"
    directory.mkdir(mode=0o700)
    binding: dict[str, str] = dict(zip(("base_commit", "head_commit"), diagnostic.EXPECTED_COMMITS, strict=True))
    binding.update(zip(("base_tree", "head_tree"), diagnostic.EXPECTED_TREES, strict=True))
    binding.update(
        mode="full",
        nonce="a" * 64,
        producer_commit="b" * 40,
        payload_sha256="c" * 64,
        workflow_sha256="d" * 64,
        supervisor_sha256="e" * 64,
    )
    return directory, binding


@pytest.mark.parametrize(
    "program, category, expected",
    [
        ("raise SystemExit(124)", "child_exit", 124),
        ("import time; time.sleep(20)", "wrapper_expired", 124),
        ("import os,signal; os.kill(os.getpid(),signal.SIGTERM)", "signal_termination", 1),
    ],
)
def test_child_124_is_distinct_from_wrapper_expiry(observation, program, category, expected):
    directory, binding = observation
    assert supervisor.supervise([sys.executable, "-c", program], directory, binding, timeout=0.15) == expected
    terminal = diagnostic.read_record(directory, "terminal.json", diagnostic.TERMINAL_LIMIT)
    diagnostic.validate_terminal(terminal, binding)
    assert terminal["category"] == category
    assert terminal["cleanup"] == "complete"
    assert terminal["elapsed_ms"] < 11000


def test_owned_cleanup_preserves_sibling_and_supervisor_with_inherited_pipe(observation, tmp_path):
    directory, binding = observation
    sibling = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    started = time.monotonic()
    try:
        program = "import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); os.fork(); time.sleep(30)"
        read_fd, write_fd = os.pipe()
        os.set_inheritable(write_fd, True)
        saved_stdout = os.dup(1)
        try:
            os.dup2(write_fd, 1)
            assert supervisor.supervise([sys.executable, "-c", program], directory, binding, timeout=0.1) == 124
        finally:
            os.dup2(saved_stdout, 1)
            os.close(saved_stdout)
            os.close(write_fd)
        assert select.select([read_fd], [], [], 1)[0], "owned descendants must release inherited pipe"
        assert os.read(read_fd, 1) == b""
        os.close(read_fd)
        assert sibling.poll() is None
        assert time.monotonic() - started < 11
        assert os.getpid() > 0
    finally:
        os.killpg(sibling.pid, signal.SIGKILL)
        sibling.wait(timeout=5)


def test_missing_child_is_supervisor_error(observation):
    directory, binding = observation
    with pytest.raises(FileNotFoundError):
        supervisor.supervise(["/nonexistent/supplemental-review"], directory, binding)
    terminal = json.loads((directory / "terminal.json").read_text())
    assert terminal["category"] == "supervisor_error"
    assert terminal["cleanup"] == "complete"


@pytest.mark.parametrize("error", [PermissionError, OSError, ValueError, IndexError])
def test_unreadable_descendant_is_not_gone(monkeypatch, error):
    def denied(*args, **kwargs):
        raise error("unreadable")

    monkeypatch.setattr(Path, "open", denied)
    assert supervisor._descendants_gone({4242: "start"}) is False


def test_unreadable_inventory_keeps_cleanup_incomplete(observation, monkeypatch):
    directory, binding = observation

    def denied(_pid):
        pending = diagnostic.read_record(directory, "terminal.json", diagnostic.TERMINAL_LIMIT)
        assert pending["category"] == "wrapper_expired"
        assert pending["cleanup"] == "pending"
        raise PermissionError("private-process-error")

    monkeypatch.setattr(supervisor, "_linux_descendants", denied)
    assert (
        supervisor.supervise([sys.executable, "-c", "import time;time.sleep(30)"], directory, binding, timeout=0.1) == 1
    )
    terminal = diagnostic.read_record(directory, "terminal.json", diagnostic.TERMINAL_LIMIT)
    assert terminal["cleanup"] == "incomplete"
    assert "private-process-error" not in json.dumps(terminal)
