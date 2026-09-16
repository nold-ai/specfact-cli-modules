"""Timing replay retains failed-hook authority and bounded actual output."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest


HELPER = Path(__file__).resolve().parents[2] / "scripts/native_review_timing_diagnostic.py"


def _helper():
    assert HELPER.is_file(), "bounded review timing diagnostic is not implemented"
    spec = importlib.util.spec_from_file_location("native_review_timing_diagnostic", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_capture_keeps_complete_stream_identity_when_prefix_is_bounded(tmp_path):
    diagnostic = _helper()
    command = [sys.executable, "-c", "import sys;sys.stdout.write('x'*10000);sys.stderr.write('err')"]
    result = diagnostic.capture_command(
        command, tmp_path, dict(os.environ), tmp_path, limits=diagnostic.CaptureLimits(timeout=5, prefix_bytes=32)
    )
    assert result["exit_code"] == 0
    assert result["stdout"]["bytes"] == 10000
    assert result["stdout"]["sha256"] == hashlib.sha256(b"x" * 10000).hexdigest()
    assert result["stdout"]["truncated"] is True
    assert (tmp_path / "review.stdout").read_bytes() == b"x" * 32
    assert (tmp_path / "review.stderr").read_bytes() == b"err"


def test_capture_timeout_retains_real_partial_output(tmp_path):
    diagnostic = _helper()
    command = [sys.executable, "-u", "-c", "import time;print('started');time.sleep(10)"]
    result = diagnostic.capture_command(
        command, tmp_path, dict(os.environ), tmp_path, limits=diagnostic.CaptureLimits(timeout=0.1)
    )
    assert result["timed_out"] is True
    assert result["exit_code"] != 0
    assert (tmp_path / "review.stdout").read_text() == "started\n"
    assert result["elapsed_seconds"] < 5


def test_only_original_timeout_without_report_is_replayed(tmp_path):
    diagnostic = _helper()
    log = tmp_path / "hooks.log"
    log.write_text("ordinary test failure")
    assert diagnostic.is_review_timeout(tmp_path) is False
    log.write_text("Code review gate timed out after 300s (command: original).")
    assert diagnostic.is_review_timeout(tmp_path) is True
    (tmp_path / "code-review.json").write_text("{}")
    assert diagnostic.is_review_timeout(tmp_path) is False


def test_replay_command_preserves_targets_and_changes_only_evidence_sink(tmp_path):
    diagnostic = _helper()
    files = [tmp_path / "a.py", tmp_path / "tests/test_a.py"]
    original, replay = diagnostic.review_commands(tmp_path, files, tmp_path / "evidence")
    assert original[0] == str(tmp_path / ".venv/bin/python")
    assert original[1:8] == ["-m", "specfact_cli.cli", "code", "review", "run", "--json", "--out"]
    assert original[8:] == [".specfact/code-review.json", "--enforcement", "changed", "a.py", "tests/test_a.py"]
    assert replay[:8] == original[:8]
    assert replay[9:] == original[9:]
    assert replay[8] == str(tmp_path / "evidence/review.raw")


def test_failed_runtime_profile_cannot_be_reported_as_acceptance(tmp_path, monkeypatch):
    diagnostic = _helper()
    (tmp_path / "hooks.log").write_text("Code review gate timed out after 300s")
    monkeypatch.setattr(diagnostic, "staged_files", lambda _repo: [tmp_path / "a.py"])
    monkeypatch.setattr(diagnostic, "source_state", lambda _repo: {"tree": "same"})

    def fail_profile(*_args):
        raise ValueError("invalid worker")

    monkeypatch.setattr(diagnostic, "profile_cached_runtime", fail_profile)
    assert diagnostic.diagnose(tmp_path, tmp_path) == 1
    report = json.loads((tmp_path / "review-timing/diagnostic.json").read_text())
    assert report["acceptance"] is False
    assert report["authority"] == "diagnostic-only"
    assert "invalid worker" in report["failure"]
    assert not (tmp_path / "code-review.json").exists()


def _running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    status = Path(f"/proc/{pid}/stat")
    return not status.is_file() or status.read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0] != "Z"


def test_timeout_kills_owned_grandchild_without_killing_unrelated_child(tmp_path):
    diagnostic = _helper()
    command = [
        sys.executable,
        "-u",
        "-c",
        "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
        "print(p.pid,flush=True);time.sleep(60)",
    ]
    with subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"]) as unrelated:
        try:
            result = diagnostic.capture_command(
                command, tmp_path, dict(os.environ), tmp_path, limits=diagnostic.CaptureLimits(timeout=0.3)
            )
            descendant = int((tmp_path / "review.stdout").read_text().strip())
            deadline = time.monotonic() + 2
            while _running(descendant) and time.monotonic() < deadline:
                time.sleep(0.02)
            assert result["timed_out"] and result["stdout"]["complete"]
            assert not _running(descendant)
            assert unrelated.poll() is None
        finally:
            unrelated.kill()
            unrelated.wait()


def test_parent_termination_cleans_review_subgroup(tmp_path):
    child = "import os,time;print(os.getpid(),flush=True);time.sleep(60)"
    script = (
        "import importlib.util,sys,os;from pathlib import Path;"
        f"s=importlib.util.spec_from_file_location('probe',{str(HELPER)!r});"
        "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);"
        f"m.capture_command([sys.executable,'-u','-c',{child!r}],Path({str(tmp_path)!r}),"
        f"dict(os.environ),Path({str(tmp_path)!r}),limits=m.CaptureLimits(timeout=60))"
    )
    with subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
    ) as parent:
        try:
            output = tmp_path / "review.stdout"
            deadline = time.monotonic() + 5
            while (not output.exists() or not output.read_text().strip()) and time.monotonic() < deadline:
                time.sleep(0.02)
            child_pid = int(output.read_text().strip())
            parent.send_signal(signal.SIGTERM)
            _, errors = parent.communicate(timeout=5)
            assert b"diagnostic replay cancelled" in errors
            deadline = time.monotonic() + 2
            while _running(child_pid) and time.monotonic() < deadline:
                time.sleep(0.02)
            assert not _running(child_pid)
        finally:
            if parent.poll() is None:
                parent.kill()
            parent.communicate()


@pytest.mark.parametrize("reason", ["project_runtime_offline_cache_miss: retry", "project_runtime_corrupt_cache"])
def test_profile_online_fallback_only_for_exact_cache_miss(tmp_path, monkeypatch, reason):
    diagnostic = _helper()
    worker = SimpleNamespace(identity="worker", environment_id="cp312")
    plan = SimpleNamespace(source_identity="source", identity="project")
    observed = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(diagnostic.runner, "_prepare_capsule_runtime", lambda: (worker, ""))
    monkeypatch.setattr(diagnostic.runner, "_cleanup_capsule_runtime", lambda _worker: None)

    def snapshot(_files, destination):
        assert destination.stat().st_mode & 0o777 == 0o700
        return SimpleNamespace(root=destination)

    monkeypatch.setattr(diagnostic.runner, "_cached_analysis_snapshot", snapshot)
    monkeypatch.setattr(diagnostic, "discover_snapshot", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(diagnostic, "project_worker", lambda *_args: nullcontext(worker))

    def prepare(_plan, *, runtime, offline=False):
        assert runtime is worker
        observed.append(offline)
        if offline:
            raise diagnostic.ProjectRuntimeError(reason)
        return SimpleNamespace(identity="runtime")

    monkeypatch.setattr(diagnostic, "prepare_runtime", prepare)
    if "offline_cache_miss" in reason:
        result = diagnostic.profile_cached_runtime(tmp_path, [])
        assert observed == [True, False]
        assert result["offline_cache_miss"] and not result["acceptance"]
        assert result["project_identity"] == "project"
    else:
        with pytest.raises(diagnostic.ProjectRuntimeError, match="corrupt"):
            diagnostic.profile_cached_runtime(tmp_path, [])
        assert observed == [True]


@pytest.mark.parametrize("state", ["match", "mismatch", "unavailable"])
def test_replay_runtime_identity_comparison(tmp_path, state):
    diagnostic = _helper()
    preparation = {
        "project_identity": "project",
        "runtime_identity": "runtime",
        "environment_id": "cp312",
        "bound_capsule_identity": "bound",
    }
    report = {
        "scope_evidence": {
            "project_runtime": {
                "status": "PASS",
                "project_identity": "project",
                "identity": "runtime",
                "environment_id": "cp312",
            }
        },
        "analyzer_evidence": [{"id": "basedpyright", "capsule_identity": "bound"}],
    }
    if state == "mismatch":
        report["scope_evidence"]["project_runtime"]["identity"] = "other"
    elif state == "unavailable":
        report["analyzer_evidence"] = []
    raw = json.dumps(report).encode()
    (tmp_path / "review.raw").write_bytes(raw)
    result = diagnostic.wrap_report(tmp_path, preparation)
    assert result["runtime_comparison"]["status"] == state
    assert result["runtime_comparison"]["warm_runtime_identity_verified"] is (state == "match")
    assert (tmp_path / "review.raw").read_bytes() == raw
    assert json.loads((tmp_path / "review.json").read_text())["acceptance"] is False


def test_changed_source_fails_even_when_diagnostic_replay_completes(tmp_path, monkeypatch):
    diagnostic = _helper()
    (tmp_path / "hooks.log").write_text("Code review gate timed out after 300s")
    states = iter([{"tree": "before"}, {"tree": "after"}])
    monkeypatch.setattr(diagnostic, "source_state", lambda _repo: next(states))
    monkeypatch.setattr(diagnostic, "staged_files", lambda _repo: [tmp_path / "a.py"])
    monkeypatch.setattr(diagnostic, "profile_cached_runtime", lambda *_args: {})
    monkeypatch.setattr(diagnostic, "capture_command", lambda *_args: {"exit_code": 0})
    assert diagnostic.diagnose(tmp_path, tmp_path) == 1
    result = json.loads((tmp_path / "review-timing/diagnostic.json").read_text())
    assert "identity changed" in result["failure"]
    assert result["acceptance"] is False
