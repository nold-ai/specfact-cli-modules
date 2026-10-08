"""Temporary sealed diagnostics preserve the default analyzer contract."""

import faulthandler
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from specfact_code_review.run import runner, target_bootstrap, target_launch
from specfact_code_review.run.sandbox import BubblewrapIdentity
from specfact_code_review.tools import contract_runner


MARKER = "SPECFACT_CODE_REVIEW_CROSSHAIR_STACK_SAMPLES"


@pytest.mark.parametrize("value", ["1", 1, None, [], {}])
def test_private_request_rejects_non_boolean_diagnosis(tmp_path, value):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"member": "contracts", "paths": ["source.py"], "stack_samples": value}))
    with pytest.raises(ValueError, match="stack sampling"):
        runner._load_capsule_request(request)


def test_private_request_restricts_enabled_diagnosis_to_contracts(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"member": "ruff", "paths": ["source.py"], "stack_samples": True}))
    with pytest.raises(ValueError, match="stack sampling"):
        runner._load_capsule_request(request)


@pytest.mark.parametrize("enabled", [False, True])
def test_private_request_retains_inputs_and_diagnosis(tmp_path, enabled):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"member": "contracts", "paths": ["source.py"], "stack_samples": enabled}))
    assert runner._load_capsule_request(request) == (
        "contracts",
        [Path("/opt/specfact/snapshot/source.py")],
        False,
        (),
        False,
        enabled,
    )


@pytest.mark.parametrize("failure", [None, RuntimeError, SystemExit])
def test_opt_in_arms_before_attachment_and_cancels_on_exit(monkeypatch, failure):
    events = []
    monkeypatch.setenv(MARKER, "1")
    monkeypatch.setattr(target_bootstrap, "BUILTIN", Path(target_bootstrap.__file__).parents[2])
    monkeypatch.setattr(sys, "argv", ["bootstrap", "crosshair", "check", "--per_path_timeout", "2", "source.py"])
    monkeypatch.setattr(faulthandler, "dump_traceback_later", lambda *a, **kw: events.append(("armed", a, kw)))
    monkeypatch.setattr(faulthandler, "cancel_dump_traceback_later", lambda: events.append("cancelled"))
    monkeypatch.setattr(target_bootstrap, "_configure_runtime", lambda domain: events.append(("attached", domain)))

    def dispatch(module, **kwargs):
        assert MARKER not in target_bootstrap.os.environ
        events.append((module, sys.argv.copy()))
        if failure:
            raise failure(7)

    monkeypatch.setattr(target_bootstrap.runpy, "run_module", dispatch)
    if failure:
        with pytest.raises(failure):
            target_bootstrap.main()
    else:
        target_bootstrap.main()
    assert events == [
        ("armed", (5,), {"repeat": True, "file": sys.stderr}),
        ("attached", "crosshair"),
        ("crosshair", ["bootstrap", "check", "--per_path_timeout", "2", "source.py"]),
        "cancelled",
    ]


def test_attachment_failure_still_cancels_samples(monkeypatch):
    events = []
    monkeypatch.setenv(MARKER, "1")
    monkeypatch.setattr(sys, "argv", ["bootstrap", "crosshair", "check", "source.py"])
    monkeypatch.setattr(faulthandler, "dump_traceback_later", lambda *a, **kw: events.append("armed"))
    monkeypatch.setattr(faulthandler, "cancel_dump_traceback_later", lambda: events.append("cancelled"))
    monkeypatch.setattr(target_bootstrap, "_configure_runtime", Mock(side_effect=RuntimeError("attachment_failed")))
    with pytest.raises(SystemExit) as failure:
        target_bootstrap.main()
    assert failure.value.code == 78
    assert events == ["armed", "cancelled"]


@pytest.mark.parametrize("module", ["crosshair", "pylint", "pytest-observe"])
def test_fixed_marker_is_forwarded_only_to_crosshair(monkeypatch, module):
    monkeypatch.setenv(MARKER, "1")
    monkeypatch.setattr(target_launch, "member_mounts", lambda domain: [])
    monkeypatch.setattr(target_launch, "interpreter_command", lambda arguments: ["python", *arguments])
    command = target_launch.target_command(module, ["check", "--per_path_timeout", "2", "source.py"])
    assert (MARKER in command) is (module == "crosshair")
    assert "--clearenv" in command and "--unshare-all" in command
    assert command[-5:] == [module, "check", "--per_path_timeout", "2", "source.py"]


@pytest.mark.parametrize("raw", [str, lambda s: s.encode()])
def test_opt_in_timeout_projects_fixed_frames_only(monkeypatch, raw):
    monkeypatch.setenv(MARKER, "1")
    stack = (
        '  File "/opt/specfact/config/member-analyzers/crosshair/core.py", line 123 in gen_args\n'
        '  File "/opt/specfact/snapshot/portable_worker.py", line 1 in run_portable_pytest\n'
        '  File "/secret/private.py", line 456 in PRIVATE_FUNCTION\n'
    )
    run = Mock(side_effect=subprocess.TimeoutExpired("crosshair", 30, stderr=raw(stack)))
    monkeypatch.setattr(contract_runner.subprocess, "run", run)
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda argv: argv)
    finding = contract_runner._execute_crosshair([Path("source.py")], bug_hunt=False)
    assert finding.execution_state == "error" and finding.evidence_outcome == "UNKNOWN"
    assert (
        finding.message
        == "CrossHair timed out before mandatory evidence completed. sampled_frames=argument_generation,run_portable_pytest"
    )
    assert run.call_args.kwargs["timeout"] == 30
    assert run.call_args.args[0] == ["crosshair", "check", "--per_path_timeout", "2", "source.py"]
    assert "PRIVATE_FUNCTION" not in finding.message and "/secret" not in finding.message


def test_private_stack_tail_is_bounded(monkeypatch):
    monkeypatch.setenv(MARKER, "1")
    stack = '  File "/owned/crosshair/core.py", line 1 in gen_args\n' + "X" * 65536
    monkeypatch.setattr(
        contract_runner.subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired("crosshair", 30, stderr=stack))
    )
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda argv: argv)
    finding = contract_runner._execute_crosshair([Path("source.py")], bug_hunt=False)
    assert finding.message == "CrossHair timed out before mandatory evidence completed."


@pytest.fixture
def capsule_runtime(tmp_path):
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    return runner.CapsuleRuntime(
        root=capsule,
        identity="sha256:" + "a" * 64,
        interpreter="/opt/specfact/python/bin/python",
        bootstrap="/opt/specfact/bootstrap/runner.py",
        bubblewrap=BubblewrapIdentity(
            path="/fixture/bwrap",
            format="ELF",
            architecture="x86_64",
            linkage="static",
            interpreter=(),
            needed=(),
            sha256="a" * 64,
            descriptor_digest="b" * 64,
        ),
        environment_id="test-environment",
    )


@pytest.fixture
def captured_request(monkeypatch):
    monkeypatch.setattr(runner, "preflight_reserved_imports", lambda context: SimpleNamespace(status="PASS"))
    observed = {}

    def execute(plan, bubblewrap, *, extra_argv):
        observed.update(json.loads((plan.mount_for("policy").source / "request.json").read_text()))
        (plan.mount_for("output").source / "result.json").write_text(
            json.dumps(
                {
                    "member": observed["member"],
                    "execution_state": "ran",
                    "evidence_outcome": "PASS",
                    "findings": [],
                    "diagnostic": "",
                }
            )
        )
        return SimpleNamespace(status="PASS")

    monkeypatch.setattr(runner, "execute_launch_plan", execute)
    return observed


@pytest.mark.parametrize("member,enabled", [("ruff", False), ("ruff", True), ("contracts", False), ("contracts", True)])
def test_controller_opt_in_uses_existing_private_request(
    monkeypatch, capsule_runtime, captured_request, member, enabled
):
    snapshot = capsule_runtime.root.parent / "snapshot"
    snapshot.mkdir()
    source = snapshot / "source.py"
    source.write_text("value = 1\n")
    monkeypatch.setenv(MARKER, "1" if enabled else "0")
    response = runner._execute_capsule_member(
        runner.CapsuleMemberExecutionRequest(
            runtime=capsule_runtime,
            member=member,
            invocation_id="diagnostic-fixture",
            snapshot_root=snapshot,
            files=[source],
            options=runner.ReviewOptions(),
        )
    )
    assert response["evidence_outcome"] == "PASS"
    expected = {
        "adapter_argv": [],
        "bug_hunt": False,
        "complete_pytest_inventory": False,
        "member": member,
        "paths": ["source.py"],
    }
    if enabled and member == "contracts":
        expected["stack_samples"] = True
    assert captured_request == expected


@pytest.mark.parametrize("failure", [None, RuntimeError, SystemExit])
def test_sealed_parent_marker_is_scoped_and_restored(monkeypatch, failure):
    monkeypatch.setenv(MARKER, "previous")
    with runner._crosshair_diagnostic_scope(False):
        assert MARKER not in runner.os.environ
    assert runner.os.environ[MARKER] == "previous"

    def invoke():
        with runner._crosshair_diagnostic_scope(True):
            assert runner.os.environ[MARKER] == "1"
            if failure:
                raise failure(7)

    if failure:
        with pytest.raises(failure):
            invoke()
    else:
        invoke()
    assert runner.os.environ[MARKER] == "previous"


SAMPLE = (
    "Timeout (0:00:05)!\n"
    "Thread 0x000000abcd (most recent call first):\n"
    '  File "/private/SAMPLE_SECRET/crosshair/core.py", line 123 in gen_args\n'
    '  File "/private/SAMPLE_SECRET/private.py", line 456 in SAMPLE_SECRET_FUNCTION\n'
    "\n"
)


@pytest.mark.parametrize("exit_code", [1, 2])
@pytest.mark.parametrize("quoted_filename", [False, True])
def test_completed_error_strips_samples_and_retains_native_error(monkeypatch, exit_code, quoted_filename):
    monkeypatch.setenv(MARKER, "1")
    native_error = "Traceback (most recent call last):\nTypeError: original constructor error\n"
    sample = SAMPLE.replace("/private/SAMPLE_SECRET/", '/private/SAMPLE_SECRET"quoted/') if quoted_filename else SAMPLE
    monkeypatch.setattr(contract_runner, "skip_if_tool_missing", lambda *args: [])
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda argv: argv)
    monkeypatch.setattr(
        contract_runner.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess("crosshair", exit_code, "", sample + native_error + sample)),
    )
    finding = contract_runner._run_crosshair([Path("source.py")], bug_hunt=False)[0]
    assert finding.execution_state == "error" and finding.evidence_outcome == "UNKNOWN"
    assert finding.message == (
        "CrossHair process error: " + native_error.strip() + " sampled_frames=argument_generation"
    )
    assert "SAMPLE_SECRET" not in finding.message and "Timeout (" not in finding.message


def test_completed_error_with_only_samples_retains_failed_exit(monkeypatch):
    monkeypatch.setenv(MARKER, "1")
    monkeypatch.setattr(contract_runner, "skip_if_tool_missing", lambda *args: [])
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda argv: argv)
    monkeypatch.setattr(
        contract_runner.subprocess, "run", Mock(return_value=subprocess.CompletedProcess("crosshair", 1, "", SAMPLE))
    )
    finding = contract_runner._run_crosshair([Path("source.py")], bug_hunt=False)[0]
    assert finding.execution_state == "error" and finding.evidence_outcome == "UNKNOWN"
    assert finding.message == "CrossHair process error: process exit 1 sampled_frames=argument_generation"


def test_ordinary_completed_error_retains_original_stderr(monkeypatch):
    monkeypatch.delenv(MARKER, raising=False)
    monkeypatch.setattr(contract_runner, "skip_if_tool_missing", lambda *args: [])
    monkeypatch.setattr(contract_runner, "analyzer_command", lambda argv: argv)
    monkeypatch.setattr(
        contract_runner.subprocess, "run", Mock(return_value=subprocess.CompletedProcess("crosshair", 2, "", SAMPLE))
    )
    finding = contract_runner._run_crosshair([Path("source.py")], bug_hunt=False)[0]
    assert finding.message == "CrossHair process error: " + SAMPLE.strip()
