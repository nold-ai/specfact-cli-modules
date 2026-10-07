"""Bound temporary diagnostics without changing CrossHair execution policy."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from specfact_code_review.run import target_bootstrap
from specfact_code_review.tools import contract_runner


@pytest.mark.parametrize("exit_type", [None, RuntimeError, SystemExit])
def test_sampling_cancels_on_every_exit(exit_type, monkeypatch):
    events = []
    handler = Mock()
    handler.dump_traceback_later.side_effect = lambda *a, **kw: events.append((a, kw))
    handler.cancel_dump_traceback_later.side_effect = lambda: events.append("cancel")
    monkeypatch.setattr(target_bootstrap, "faulthandler", handler, raising=False)
    if exit_type is None:
        with target_bootstrap._crosshair_stack_samples("crosshair"):
            events.append("dispatch")
    else:
        with pytest.raises(exit_type), target_bootstrap._crosshair_stack_samples("crosshair"):
            events.append("dispatch")
            raise exit_type("existing exit")
    assert events == [((5,), {"repeat": True, "file": target_bootstrap.sys.stderr}), "dispatch", "cancel"]


def test_sampling_leaves_other_domains_untouched(monkeypatch):
    handler = Mock()
    monkeypatch.setattr(target_bootstrap, "faulthandler", handler, raising=False)
    for domain in ("pylint", "pytest-observe", "basedpyright", "project-python"):
        with target_bootstrap._crosshair_stack_samples(domain):
            pass
    assert handler.mock_calls == []


@pytest.mark.parametrize("raw", [str, lambda value: value.encode()])
def test_timeout_projects_only_known_frames(raw, monkeypatch):
    stack = "\n".join(
        [
            "Timeout (0:00:05)!",
            '  File "/opt/specfact/builtin/specfact_code_review/run/target_bootstrap.py", line 1 in _configure_runtime',
            '  File "/opt/specfact/config/member-analyzers/crosshair/core.py", line 1 in analyze_calltree',
            '  File "/opt/specfact/snapshot/packages/specfact-code-review/src/specfact_code_review/run/portable_worker.py", line 1 in select_test_paths',
            '  File "/private/secret/value.py", line 1 in PRIVATE_FUNCTION',
        ]
    )
    run = Mock(side_effect=subprocess.TimeoutExpired("crosshair", 30, stderr=raw(stack)))
    monkeypatch.setattr(contract_runner.subprocess, "run", run)
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda args: args)
    result = contract_runner._execute_crosshair([Path("source.py")], bug_hunt=False)
    assert result.execution_state == "error" and result.evidence_outcome == "UNKNOWN"
    assert result.message == (
        "CrossHair timed out before mandatory evidence completed. "
        "sampled_frames=bootstrap_attachment,select_test_paths,symbolic_search"
    )
    assert run.call_args.kwargs["timeout"] == 30
    assert run.call_args.args[0] == ["crosshair", "check", "--per_path_timeout", "2", "source.py"]


def test_timeout_observations_ignore_older_and_unknown_stacks(monkeypatch):
    prefix = '  File "/opt/specfact/config/member-analyzers/crosshair/core.py", line 1 in analyze_calltree\n'
    run = Mock(side_effect=subprocess.TimeoutExpired("crosshair", 120, stderr=prefix + "x" * 65536))
    monkeypatch.setattr(contract_runner.subprocess, "run", run)
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda args: args)
    result = contract_runner._execute_crosshair([Path("source.py")], bug_hunt=True)
    assert result.message == "CrossHair timed out before mandatory evidence completed."
    assert run.call_args.kwargs["timeout"] == 120
    assert run.call_args.args[0] == ["crosshair", "check", "--per_path_timeout", "10", "source.py"]


def test_sampling_surrounds_attachment_and_retains_module_dispatch(monkeypatch):
    events = []
    handler = Mock()
    handler.dump_traceback_later.side_effect = lambda *a, **kw: events.append("armed")
    handler.cancel_dump_traceback_later.side_effect = lambda: events.append("cancelled")
    monkeypatch.setattr(target_bootstrap, "faulthandler", handler)
    monkeypatch.setattr(
        target_bootstrap.sys, "argv", ["bootstrap", "crosshair", "check", "--per_path_timeout", "2", "source.py"]
    )
    monkeypatch.setattr(target_bootstrap, "_configure_runtime", lambda domain: events.append(("attached", domain)))

    def dispatch(module, **kwargs):
        events.append((module, kwargs, target_bootstrap.sys.argv.copy()))
        raise SystemExit(1)

    monkeypatch.setattr(target_bootstrap.runpy, "run_module", dispatch)
    with pytest.raises(SystemExit) as raised:
        target_bootstrap.main()
    assert raised.value.code == 1
    assert events == [
        "armed",
        ("attached", "crosshair"),
        (
            "crosshair",
            {"run_name": "__main__", "alter_sys": True},
            ["bootstrap", "check", "--per_path_timeout", "2", "source.py"],
        ),
        "cancelled",
    ]
