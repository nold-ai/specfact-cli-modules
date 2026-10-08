"""Production CrossHair dispatch preserves policy without temporary stack sampling."""

import faulthandler
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from crosshair import core

from specfact_code_review.run import target_bootstrap
from specfact_code_review.tools import contract_runner


@pytest.mark.parametrize("bug_hunt", [False, True])
@pytest.mark.parametrize("raw", [str, lambda value: value.encode()])
def test_timeout_retains_unknown_and_discards_stderr(raw, bug_hunt, monkeypatch):
    stack = (
        '  File "/opt/specfact/config/member-analyzers/crosshair/core.py", line 1 in analyze_calltree\n'
        '  File "/private/secret/value.py", line 1 in PRIVATE_FUNCTION'
    )
    run = Mock(side_effect=subprocess.TimeoutExpired("crosshair", 120 if bug_hunt else 30, stderr=raw(stack)))
    monkeypatch.setattr(contract_runner.subprocess, "run", run)
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda args: args)
    result = contract_runner._execute_crosshair([Path("source.py")], bug_hunt=bug_hunt)
    assert result.execution_state == "error" and result.evidence_outcome == "UNKNOWN"
    assert result.message == "CrossHair timed out before mandatory evidence completed."
    assert run.call_args.kwargs["timeout"] == (120 if bug_hunt else 30)
    assert run.call_args.args[0] == ["crosshair", "check", "--per_path_timeout", "10" if bug_hunt else "2", "source.py"]


def test_production_dispatch_preserves_attachment_argv_and_exit_without_sampling(monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("temporary sampling must be removed")

    monkeypatch.setattr(faulthandler, "dump_traceback_later", unexpected)
    monkeypatch.setattr(
        target_bootstrap.sys, "argv", ["bootstrap", "crosshair", "check", "--per_path_timeout", "2", "source.py"]
    )
    events = []
    original = core.get_constructor_signature
    monkeypatch.setattr(target_bootstrap, "BUILTIN", Path(target_bootstrap.__file__).parents[2])
    monkeypatch.setattr(target_bootstrap, "_configure_runtime", lambda domain: events.append(("attached", domain)))

    def dispatch(module, **kwargs):
        events.append((module, kwargs, target_bootstrap.sys.argv.copy()))
        raise SystemExit(1)

    monkeypatch.setattr(target_bootstrap.runpy, "run_module", dispatch)
    with pytest.raises(SystemExit) as raised:
        target_bootstrap.main()
    assert raised.value.code == 1
    assert core.get_constructor_signature is original
    assert events == [
        ("attached", "crosshair"),
        (
            "crosshair",
            {"run_name": "__main__", "alter_sys": True},
            ["bootstrap", "check", "--per_path_timeout", "2", "source.py"],
        ),
    ]
