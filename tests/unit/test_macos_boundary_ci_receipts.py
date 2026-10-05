"""CI acceptance cannot omit required controls or overlap timed-out native suites."""

from __future__ import annotations

import ast
import hashlib
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import CodeType

import pytest
import yaml


ROOT = Path(__file__).parents[2]


class _WorkflowDefinitionsLoader(importlib.machinery.SourceFileLoader):
    """Load actual CI definitions while excluding the workflow entry point."""

    def __init__(self, tree: ast.Module):
        super().__init__("boundary_ci_definitions", "code-review-macos-boundary.yml")
        self.tree = tree

    def get_code(self, fullname: str) -> CodeType:
        if fullname != self.name:
            raise ImportError("workflow definition identity mismatch")
        return compile(self.tree, self.path, "exec")


@pytest.fixture(name="boundary_ci")
def fixture_boundary_ci():
    tree = ast.parse((ROOT / "scripts/check_macos_boundary_ci_receipts.py").read_text())
    tree.body = [node for node in tree.body if not isinstance(node, ast.If)]
    loader = _WorkflowDefinitionsLoader(tree)
    spec = importlib.util.spec_from_file_location(loader.name, loader.path, loader=loader)
    assert spec
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    namespace = module.__dict__
    namespace["SOURCE"] = ROOT / "scripts/macos_managed_boundary"
    return namespace


@pytest.fixture(name="startup_receipt")
def fixture_startup_receipt(boundary_ci):
    sources = {"broker": "startup_broker.c", "worker": "startup_worker.c", "observer": "startup_observe.c"}
    trials = [{"mode": mode, "passed": True} for mode in boundary_ci["STARTUP_RACES"] for _ in range(100)]
    trials.extend(
        [
            {"mode": "normal", "passed": True},
            {"mode": "runtime-trap", "passed": True},
            {"mode": "pretrace", "passed": True, "abandon_process_group": True, "survived": True},
        ]
    )
    return {
        "schema_version": "specfact-managed-startup-experiment-v1",
        "architecture": "arm64",
        "os_build": "26A434",
        "repetitions": 100,
        "startup_subset_passed": True,
        "repetition_gate_passed": True,
        "production_approved": False,
        "signed_boundary_verified": False,
        "signing_mode": "ad-hoc",
        "hardened_runtime": True,
        "trials": trials,
        "completed_races": dict.fromkeys(boundary_ci["STARTUP_RACES"], 100),
        "probe_control": {"passed": True},
        "profile_sha256": boundary_ci["sha256"](boundary_ci["SOURCE"] / "fixture.sb"),
        "artifacts": [
            {
                "name": name,
                "source_sha256": boundary_ci["sha256"](boundary_ci["SOURCE"] / source),
                "sha256": "0" * 64,
                "signing": "flags=0x10002(adhoc,runtime)\nSignature=adhoc",
            }
            for name, source in sources.items()
        ],
    }


def test_complete_startup_controls_are_accepted(boundary_ci, startup_receipt):
    assert boundary_ci["checked_receipt"]("startup", startup_receipt, {"os_build": "26A434"})["result"] == "passed"


@pytest.mark.parametrize("mode", ["normal", "runtime-trap"])
def test_missing_mandatory_startup_control_is_rejected(boundary_ci, startup_receipt, mode):
    startup_receipt["trials"] = [item for item in startup_receipt["trials"] if item["mode"] != mode]
    with pytest.raises(AssertionError):
        boundary_ci["checked_receipt"]("startup", startup_receipt, {"os_build": "26A434"})


def test_timeout_never_starts_another_native_suite(boundary_ci, monkeypatch, tmp_path):
    root = tmp_path / "specfact-macos-boundary"
    root.mkdir()
    (root / "platform.json").write_text(json.dumps({"os_build": "26A434"}))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    calls = []

    def timeout(name, *_args):
        calls.append(name)
        return {"suite": name, "result": "failed", "category": "helper_timeout"}

    monkeypatch.setitem(boundary_ci, "run_suite", timeout)
    assert boundary_ci["main"]() == 1
    assert calls == ["startup"]


def test_failed_helper_reports_only_allowlisted_diagnostics(boundary_ci, monkeypatch, tmp_path):
    receipt = {
        "failure": "TimeoutError: private authority /secret/token 98765",
        "trials": [{"case": "cancel", "passed": True}, {"case": "private-host-path", "passed": True}],
        "audit_token": [98765],
    }

    def failed(_args, **options):
        options["stdout"].write(
            b'{"failed_case":"isolation-right","failure_origin":true,"diagnostic":"/private/secret"}\n'
        )
        (tmp_path / "control.json").write_text(json.dumps(receipt))
        return boundary_ci["subprocess"].CompletedProcess([], 1)

    monkeypatch.setattr(boundary_ci["subprocess"], "run", failed)
    result = boundary_ci["run_suite"]("control", tmp_path, {})
    assert result["result"] == "failed"
    assert result["failure_type"] == "TimeoutError"
    assert result["failed_case"] == "isolation-right"
    assert result["completed_cases"] == {"cancel": 1}
    assert not any(value in json.dumps(result) for value in ("secret", "98765", "authority", "private-host-path"))
    assert not (tmp_path / "control.json").exists()
    assert not (tmp_path / "control.log").exists()


def test_failure_diagnostics_reject_unknown_names(boundary_ci, monkeypatch, tmp_path):
    def failed(_args, **options):
        options["stdout"].write(b'{"failed_case":"/secret/98765","diagnostic":"/secret"}\n')
        (tmp_path / "control.json").write_text(json.dumps({"failure": "/secret/98765: private", "trials": []}))
        return boundary_ci["subprocess"].CompletedProcess([], 1)

    monkeypatch.setattr(boundary_ci["subprocess"], "run", failed)
    result = boundary_ci["run_suite"]("control", tmp_path, {})
    assert result["failed_case"] == "unknown"
    assert result["failure_type"] == "unknown"
    assert "secret" not in json.dumps(result)


def test_nested_cleanup_does_not_replace_first_failure_case(boundary_ci, monkeypatch, tmp_path):
    def failed(_args, **options):
        options["stdout"].write(
            b'{"failed_case":"isolation-right","failure_origin":true,'
            b'"failure_phase":"request-wait","diagnostic":"/secret"}\n'
            b'{"failed_case":"isolation-left","failure_origin":false,"diagnostic":"/secret"}\n'
        )
        (tmp_path / "control.json").write_text(json.dumps({"failure": "TimeoutError: private", "trials": []}))
        return boundary_ci["subprocess"].CompletedProcess([], 1)

    monkeypatch.setattr(boundary_ci["subprocess"], "run", failed)
    result = boundary_ci["run_suite"]("control", tmp_path, {})
    assert result["failed_case"] == "isolation-right"


def test_failure_phase_is_allowlisted_before_publication(boundary_ci, monkeypatch, tmp_path):
    for phase, expected in (
        ("request-wait", "request-wait"),
        ("cleanup", "cleanup"),
        ("/secret/audit/98765", "unknown"),
    ):

        def failed(_args, phase=phase, **options):
            marker = {
                "failed_case": "isolation-right",
                "failure_origin": True,
                "failure_phase": phase,
                "diagnostic": "/secret",
            }
            options["stdout"].write((json.dumps(marker) + "\n").encode())
            (tmp_path / "control.json").write_text(json.dumps({"failure": "TimeoutError: private", "trials": []}))
            return boundary_ci["subprocess"].CompletedProcess([], 1)

        monkeypatch.setattr(boundary_ci["subprocess"], "run", failed)
        result = boundary_ci["run_suite"]("control", tmp_path, {})
        assert result["failure_phase"] == expected
        assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("owner", [True, False, None, "true", 1])
def test_failure_case_requires_explicit_boolean_ownership(boundary_ci, monkeypatch, tmp_path, owner):
    def failed(_args, **options):
        markers = [
            {"failed_case": "isolation-right", "failure_origin": False, "failure_phase": "observe-worker"},
            {"failed_case": "isolation-left", "failure_origin": owner, "failure_phase": "request-launch"},
        ]
        options["stdout"].write(("\n".join(json.dumps(item) for item in markers) + "\n").encode())
        (tmp_path / "control.json").write_text(json.dumps({"failure": "TimeoutError: private", "trials": []}))
        return boundary_ci["subprocess"].CompletedProcess([], 1)

    monkeypatch.setattr(boundary_ci["subprocess"], "run", failed)
    result = boundary_ci["run_suite"]("control", tmp_path, {})
    assert result["failed_case"] == ("isolation-left" if owner is True else "unknown")
    assert result["failure_phase"] == ("request-launch" if owner is True else "unknown")


@pytest.mark.parametrize("field", ["wait_accepted", "wait_pending", "worker_reaped", "output_closed"])
@pytest.mark.parametrize("value", [False, True, 0, 1, "true", None])
def test_worker_state_publishes_only_complete_boolean_observations(boundary_ci, tmp_path, field, value):
    state = {"wait_accepted": True, "wait_pending": True, "worker_reaped": False, "output_closed": True}
    state[field] = value
    marker = {
        "failed_case": "cancel",
        "failure_origin": True,
        "failure_phase": "request-wait",
        "last_worker_state": {**state, "secret": "/private/98765"},
    }
    (tmp_path / "control.log").write_text(json.dumps(marker) + "\n")
    (tmp_path / "control.json").write_text(json.dumps({"failure": "TimeoutError: private", "trials": []}))
    result = boundary_ci["failure_summary"]("control", tmp_path / "control.json", tmp_path / "control.log")
    if isinstance(value, bool):
        assert result["last_worker_state"] == state
    else:
        assert "last_worker_state" not in result
    assert not any(item in json.dumps(result) for item in ("secret", "98765", "private"))


@pytest.mark.parametrize(
    "changes",
    [
        {"failure_origin": False},
        {"failure_phase": "cleanup"},
        {"last_worker_state": {}},
        {"last_worker_state": None},
    ],
)
def test_inapplicable_worker_state_remains_omitted(boundary_ci, tmp_path, changes):
    marker = {
        "failed_case": "cancel",
        "failure_origin": True,
        "failure_phase": "request-wait",
        "last_worker_state": dict.fromkeys(("wait_accepted", "wait_pending", "worker_reaped", "output_closed"), False),
        **changes,
    }
    (tmp_path / "control.log").write_text(json.dumps(marker) + "\n")
    (tmp_path / "control.json").write_text(json.dumps({"failure": "TimeoutError: private", "trials": []}))
    result = boundary_ci["failure_summary"]("control", tmp_path / "control.json", tmp_path / "control.log")
    assert "last_worker_state" not in result


@pytest.mark.parametrize(
    "state",
    [
        "socket_missing",
        "socket_mode_pending",
        "private_after_deadline",
        "directory_invalid",
        "socket_type_invalid",
        "socket_owner_invalid",
    ],
)
def test_socket_state_consumer_publishes_only_category(boundary_ci, tmp_path, state):
    marker = {
        "failed_case": "protocol",
        "failure_origin": True,
        "failure_phase": "bootstrap-socket",
        "bootstrap_socket_state": state,
        "diagnostic": "/secret/98765",
        "audit_token": [98765],
        "socket_path": "/secret/control.sock",
        "socket_uid": 98765,
        "socket_mode": "0777",
    }
    (tmp_path / "control.log").write_text(json.dumps(marker) + "\n")
    (tmp_path / "control.json").write_text(json.dumps({"failure": "RuntimeError: /secret/98765", "trials": []}))
    result = boundary_ci["failure_summary"]("control", tmp_path / "control.json", tmp_path / "control.log")
    assert result == {
        "failure_type": "RuntimeError",
        "failed_case": "protocol",
        "failure_phase": "bootstrap-socket",
        "completed_cases": {},
        "bootstrap_socket_state": state,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"bootstrap_socket_state": None},
        {"bootstrap_socket_state": False},
        {"bootstrap_socket_state": 1},
        {"bootstrap_socket_state": []},
        {"bootstrap_socket_state": {}},
        {"bootstrap_socket_state": "/secret/98765"},
        {"bootstrap_socket_state": "socket_missing /secret"},
        {"failure_origin": False},
        {"failure_origin": None},
        {"failure_origin": "true"},
        {"failure_origin": 1},
        {"failure_phase": "cleanup"},
        {"failure_phase": "bootstrap-register"},
        {"failure_phase": "request-wait"},
        {"failed_case": "/secret/98765"},
    ],
)
def test_socket_state_consumer_omits_inapplicable_or_malformed_evidence(boundary_ci, tmp_path, changes):
    marker = {
        "failed_case": "protocol",
        "failure_origin": True,
        "failure_phase": "bootstrap-socket",
        "bootstrap_socket_state": "socket_missing",
        "diagnostic": "/secret/98765",
        **changes,
    }
    (tmp_path / "control.log").write_text(json.dumps(marker) + "\n")
    result = boundary_ci["failure_summary"]("control", tmp_path / "control.json", tmp_path / "control.log")
    assert "bootstrap_socket_state" not in result
    assert not any(item in json.dumps(result) for item in ("secret", "98765", "diagnostic"))


def test_socket_state_consumer_omits_startup_suite(boundary_ci, tmp_path):
    marker = {
        "failed_case": "normal",
        "failure_origin": True,
        "failure_phase": "bootstrap-socket",
        "bootstrap_socket_state": "socket_missing",
    }
    (tmp_path / "startup.log").write_text(json.dumps(marker) + "\n")
    result = boundary_ci["failure_summary"]("startup", tmp_path / "startup.json", tmp_path / "startup.log")
    assert "bootstrap_socket_state" not in result


def test_socket_state_consumer_never_borrows_nested_or_receipt_evidence(boundary_ci, tmp_path):
    markers = [
        {
            "failed_case": "protocol",
            "failure_origin": False,
            "failure_phase": "bootstrap-socket",
            "bootstrap_socket_state": "socket_missing",
        },
        {"failed_case": "protocol", "failure_origin": True, "failure_phase": "bootstrap-socket"},
        {
            "failed_case": "protocol",
            "failure_origin": True,
            "failure_phase": "bootstrap-socket",
            "bootstrap_socket_state": "socket_owner_invalid",
        },
    ]
    (tmp_path / "control.log").write_text("\n".join(json.dumps(marker) for marker in markers) + "\n")
    (tmp_path / "control.json").write_text(json.dumps({"bootstrap_socket_state": "directory_invalid"}))
    result = boundary_ci["failure_summary"]("control", tmp_path / "control.json", tmp_path / "control.log")
    assert "bootstrap_socket_state" not in result


_EXPECTED_CASE_NAMES = {
    "lifecycle": "exec-cancel exec-eof exec-broker-kill exec-cancel-held exec-eof-held exec-broker-kill-held",
    "protocol": "exec-status exec-runtime-trap exec-bootstrap-trap exec-failed exec-second-image exec-modified-target",
    "broker_inputs": (
        "mach-exception-defs mach_exc_server.c mach_exc_server.h mach_exc_user.h "
        "control_mach.inc control_mach_policy.h control_mach_reply.h control_exec_policy.h"
    ),
}
EXEC_LIFECYCLE = tuple(_EXPECTED_CASE_NAMES["lifecycle"].split())
EXEC_PROTOCOL = tuple(_EXPECTED_CASE_NAMES["protocol"].split())
BROKER_INPUTS = tuple(_EXPECTED_CASE_NAMES["broker_inputs"].split())


def _control_input(boundary_ci, name):
    """Capture repository inputs while supplying fixed generated SDK byte hashes."""
    path = boundary_ci["SOURCE"] / name
    return {"name": name, "sha256": boundary_ci["sha256"](path) if path.exists() else "1" * 64}


def _control_artifact(boundary_ci, name, source):
    """Build one valid role-specific signed artifact fixture."""
    item = {
        "name": name,
        "source_sha256": boundary_ci["sha256"](boundary_ci["SOURCE"] / source),
        "sha256": "0" * 64,
        "signing": "flags=0x10002(adhoc,runtime)\nSignature=adhoc\nCDHash=" + "a" * 40,
        "entitlements": "",
    }
    inputs = {
        "broker": BROKER_INPUTS,
        "worker": ("control_probes.h", "control_resource.h"),
        "target": ("control_probes.h",),
    }
    if name in inputs:
        item["build_inputs"] = [_control_input(boundary_ci, filename) for filename in inputs[name]]
    if name == "broker":
        item["signal_transport"] = "mach-exception-v1"
    return item


def _cancel_status(held):
    """Represent the native wait result after cancellation of an exec fixture."""
    return {
        "state": "exited",
        "exit": -1,
        "signal": 9,
        "reason": "cancel",
        "traced": True,
        "output": "" if held else "target-denials-ok",
    }


def _identity_swap_fields():
    fields = _exec_lifecycle_fields("exec-eof-held")
    fields.pop("image_stop")
    fields["foreign_payload"] = {
        "source_sha256": hashlib.sha256(
            (ROOT / "scripts/macos_managed_boundary/control_target.c").read_bytes()
            + b"\nvolatile const unsigned int foreign_identity = 1;\n"
        ).hexdigest(),
        "sha256": "a" * 64,
        "signing": "flags=0x10002(adhoc,runtime)\nSignature=adhoc",
        "entitlements": "",
        "positive_output": "target-initializer-ns=99\ntarget-positive-ok\n",
    }
    fields["image_rejection"] = {
        "exec_identity_failure": 400,
        "stage": "foreign",
        "status": -67050,
        "output_complete": True,
        "initializer_seen": False,
    }
    return fields


def _exec_lifecycle_fields(case):
    """Supply complete independent birth, tracing and bounded removal observations."""
    held, cancel = case.endswith("-held"), "cancel" in case
    return {
        "worker_identity": {
            "pid": 400,
            "ppid": 300,
            "pgid": 300 if held else 400,
            "flags": 2,
            "start_sec": 123,
            "start_usec": 456,
        },
        "bootstrap_identity": {"bootstrap_identity": 400, "suspended": True, "output_empty": True},
        "image_stop": {"exec": 400, "verified_ns": 100, "held": held},
        "observation_seconds": 0.2,
        "job_removed": None if cancel else True,
        "native_proof_deadline_ns": None if cancel else 200,
        "status": _cancel_status(held) if cancel else None,
    }


def _exec_protocol_output(case, admitted):
    """Return fixed target markers for admitted images and failed exec."""
    output = "target-initializer-ns=101\ntarget-entry\ntarget-denials-ok\n" if admitted else "exec-failed"
    if case == "exec-second-image":
        output += "target-second-exec\n"
    return output


def _exec_protocol_fields(case):
    """Supply native handoff markers and actual exit or trap outcomes."""
    if case == "exec-modified-target":
        return {"response": {"ok": False, "error": "signature"}, "substitutions_checked": 2}
    admitted = case in ("exec-status", "exec-runtime-trap", "exec-second-image")
    exit_status = {"exec-status": (37, 0), "exec-failed": (38, 0)}.get(case, (-1, 5))
    return {
        "image_stop": {"exec": 400, "verified_ns": 100, "held": False} if admitted else None,
        "status": {
            "state": "exited",
            "traced": True,
            "output": _exec_protocol_output(case, admitted),
            "exit": exit_status[0],
            "signal": exit_status[1],
        },
    }


def _control_trial(case):
    """Attach exec evidence only to the matching lifecycle or protocol fixture."""
    trial = {"case": case, "passed": True}
    if case == "bootstrap-identity":
        trial.update(
            {
                "bootstrap_identity": {
                    "bootstrap_identity": 400,
                    "suspended": True,
                    "output_empty": True,
                },
                "status": {"pid": 400, "state": "exited", "exit": 37, "signal": 0, "traced": True},
            }
        )
    elif case == "exec-identity-swap":
        trial.update(_identity_swap_fields())
    elif case in EXEC_LIFECYCLE:
        trial.update(_exec_lifecycle_fields(case))
    elif case.startswith("exec-exception-"):
        kind = case.removeprefix("exec-exception-")
        trial.update(
            {
                "installed": False,
                "status": {
                    "state": "exited",
                    "exit": 37,
                    "signal": 0,
                    "traced": True,
                    "output": f"exception-port-{kind}-status=0-installed=0\nexception-swap-{kind}-installed=0\nexception-clear-{kind}-preserved=1",
                },
            }
        )
    elif case in EXEC_PROTOCOL:
        trial.update(_exec_protocol_fields(case))
    return trial


@pytest.fixture(name="control_receipt")
def fixture_control_receipt(boundary_ci, startup_receipt):
    """Build a complete v3 receipt with the exact native artifact and trial closure."""
    races = tuple(dict.fromkeys(boundary_ci["CONTROL_RACES"] + EXEC_LIFECYCLE))
    protocol = tuple(dict.fromkeys(boundary_ci["PROTOCOL_CASES"] + EXEC_PROTOCOL))
    sources = {
        "broker": "control_broker.c",
        "worker": "control_worker.c",
        "observer": "startup_observe.c",
        "target": "control_target.c",
    }
    return {
        **startup_receipt,
        "schema_version": "specfact-managed-control-experiment-v4",
        "control_subset_passed": True,
        "trials": [_control_trial(case) for case in races for _ in range(100)]
        + [_control_trial(case) for case in protocol],
        "completed_lifecycle_cases": dict.fromkeys(races, 100),
        "artifacts": [_control_artifact(boundary_ci, name, source) for name, source in sources.items()],
    }


def test_complete_control_v4_receipt_is_accepted(boundary_ci, control_receipt):
    checks = boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})
    assert checks["result"] == "passed"
    assert checks["protocol_checks"] == 28
    assert len(checks["completed_races"]) == 20
    assert set(checks["artifacts"]) == {"broker", "worker", "observer", "target"}


@pytest.mark.parametrize(
    "marker",
    [
        None,
        {},
        {"bootstrap_identity": 401, "suspended": True, "output_empty": True},
        {"bootstrap_identity": 400, "suspended": False, "output_empty": True},
        {"bootstrap_identity": 400, "suspended": True, "output_empty": False},
    ],
)
def test_bootstrap_identity_protocol_requires_exact_suspended_process(boundary_ci, control_receipt, marker):
    trial = next(item for item in control_receipt["trials"] if item["case"] == "bootstrap-identity")
    trial["bootstrap_identity"] = marker
    with pytest.raises((AssertionError, KeyError, TypeError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("case", EXEC_LIFECYCLE + EXEC_PROTOCOL)
def test_missing_exec_case_is_rejected(boundary_ci, control_receipt, case):
    control_receipt["trials"] = [item for item in control_receipt["trials"] if item["case"] != case]
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("case", EXEC_LIFECYCLE)
def test_exec_lifecycle_requires_100_actual_trials(boundary_ci, control_receipt, case):
    control_receipt["trials"].remove(next(item for item in control_receipt["trials"] if item["case"] == case))
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("name", ["broker", "worker", "target"])
def test_missing_snapshot_inputs_are_rejected(boundary_ci, control_receipt, name):
    next(item for item in control_receipt["artifacts"] if item["name"] == name).pop("build_inputs")
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("name", ["broker", "worker", "target"])
def test_stale_captured_header_is_rejected(boundary_ci, control_receipt, name):
    artifact = next(item for item in control_receipt["artifacts"] if item["name"] == name)
    artifact["build_inputs"][-1]["sha256"] = "f" * 64
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


def test_old_control_receipt_cannot_admit_handoff(boundary_ci, control_receipt):
    control_receipt["schema_version"] = "specfact-managed-control-experiment-v1"
    control_receipt["artifacts"] = [item for item in control_receipt["artifacts"] if item["name"] != "target"]
    control_receipt["trials"] = [item for item in control_receipt["trials"] if not item["case"].startswith("exec-")]
    control_receipt["completed_lifecycle_cases"] = {
        case: 100 for case in boundary_ci["CONTROL_RACES"] if not case.startswith("exec-")
    }
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("case", ["exec-status", "exec-runtime-trap", "exec-second-image"])
@pytest.mark.parametrize(
    "marker",
    [None, {}, {"exec": 400, "verified_ns": True, "held": False}, {"exec": 400, "verified_ns": 100, "held": True}],
)
def test_missing_or_malformed_image_stop_is_rejected(boundary_ci, control_receipt, case, marker):
    next(item for item in control_receipt["trials"] if item["case"] == case)["image_stop"] = marker
    with pytest.raises((AssertionError, KeyError, ValueError, TypeError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize(
    "output",
    [
        "target-entry\ntarget-denials-ok",
        "target-initializer-ns=99\ntarget-entry\ntarget-denials-ok",
        "target-initializer-ns=101\ntarget-initializer-ns=102\ntarget-entry\ntarget-denials-ok",
        "target-initializer-ns=101\ntarget-entry\ntarget-entry\ntarget-denials-ok",
        "target-initializer-ns=101\ntarget-entry",
        "target-initializer-ns=101\ntarget-entry\ntarget-denials-ok\ntarget-trap-was-suppressed",
    ],
)
def test_incomplete_or_misordered_target_evidence_is_rejected(boundary_ci, control_receipt, output):
    next(item for item in control_receipt["trials"] if item["case"] == "exec-status")["status"]["output"] = output
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("case", EXEC_PROTOCOL[:-1])
def test_wrong_exec_wait_status_is_rejected(boundary_ci, control_receipt, case):
    next(item for item in control_receipt["trials"] if item["case"] == case)["status"]["signal"] = 9
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize(
    "field,value",
    [("stage", "lookup"), ("output_complete", False), ("initializer_seen", True), ("exec_identity_failure", 401)],
)
def test_live_identity_swap_requires_observed_preinitializer_rejection(boundary_ci, control_receipt, field, value):
    trial = {"case": "exec-identity-swap", "passed": True, **_identity_swap_fields()}
    trial["image_rejection"][field] = value
    check = boundary_ci["checked_identity_swap"]
    with pytest.raises((AssertionError, KeyError, ValueError, TypeError)):
        check(trial)


@pytest.mark.parametrize("case", EXEC_LIFECYCLE)
@pytest.mark.parametrize(
    "marker",
    [None, {}, {"exec": 401, "verified_ns": 100, "held": False}, {"exec": 400, "verified_ns": True, "held": False}],
)
def test_lifecycle_without_matching_verified_image_is_rejected(boundary_ci, control_receipt, case, marker):
    next(item for item in control_receipt["trials"] if item["case"] == case)["image_stop"] = marker
    with pytest.raises((AssertionError, KeyError, ValueError, TypeError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("case", EXEC_LIFECYCLE)
def test_lifecycle_with_wrong_image_hold_state_is_rejected(boundary_ci, control_receipt, case):
    trial = next(item for item in control_receipt["trials"] if item["case"] == case)
    trial["image_stop"]["held"] = not case.endswith("-held")
    with pytest.raises(AssertionError):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("seconds", [5.001, float("nan"), float("inf"), -1, True, None])
def test_exec_lifecycle_removal_bound_is_mandatory(boundary_ci, control_receipt, seconds):
    next(item for item in control_receipt["trials"] if item["case"] == "exec-eof")["observation_seconds"] = seconds
    with pytest.raises((AssertionError, KeyError, ValueError, TypeError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("field", ["pid", "ppid", "pgid", "flags", "start_sec", "start_usec"])
def test_exec_lifecycle_requires_kernel_birth_and_ownership_fields(boundary_ci, control_receipt, field):
    next(item for item in control_receipt["trials"] if item["case"] == "exec-eof")["worker_identity"].pop(field)
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("flag", ["production_approved", "signed_boundary_verified"])
def test_control_production_flags_cannot_be_true(boundary_ci, control_receipt, flag):
    control_receipt[flag] = True
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


def test_control_summary_uses_only_digests_and_fixed_checks(boundary_ci, control_receipt):
    for artifact in control_receipt["artifacts"]:
        artifact["path"] = "/secret/98765"
        artifact["extra"] = "secret"
        for item in artifact.get("build_inputs", []):
            item["path"] = "/secret/98765"
    checks = boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})
    assert not any(
        value in json.dumps(checks)
        for value in ("secret", "98765", "image_stop", "verified_ns", "target-entry", "CDHash")
    )
    for artifact in control_receipt["artifacts"]:
        assert checks["artifacts"][artifact["name"]]["binary_sha256"] == artifact["sha256"]
        if artifact.get("build_inputs"):
            assert checks["artifacts"][artifact["name"]]["build_inputs"] == {
                item["name"]: item["sha256"] for item in artifact["build_inputs"]
            }


@pytest.mark.parametrize("name", ["broker", "worker", "observer", "target"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "not-a-digest"),
        ("source_sha256", "f" * 64),
        ("signing", "Signature=adhoc"),
        ("entitlements", "<plist>unexpected grants</plist>"),
    ],
)
def test_control_artifact_integrity_is_mandatory(boundary_ci, control_receipt, name, field, value):
    next(item for item in control_receipt["artifacts"] if item["name"] == name)[field] = value
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("change", ["missing-target", "extra-artifact", "duplicate-input", "extra-input"])
def test_control_artifact_allowance_is_exact(boundary_ci, control_receipt, change):
    artifacts = control_receipt["artifacts"]
    if change == "missing-target":
        control_receipt["artifacts"] = [item for item in artifacts if item["name"] != "target"]
    elif change == "extra-artifact":
        artifacts.append({**artifacts[0], "name": "unapproved"})
    else:
        inputs = next(item for item in artifacts if item["name"] == "broker")["build_inputs"]
        if change == "duplicate-input":
            inputs[-1] = inputs[0].copy()
        else:
            inputs.append({"name": "unapproved.h", "sha256": "f" * 64})
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


@pytest.mark.parametrize("case", EXEC_LIFECYCLE + EXEC_PROTOCOL)
def test_new_failure_cases_publish_only_allowlisted_categories(boundary_ci, tmp_path, case):
    (tmp_path / "control.log").write_text(
        json.dumps(
            {
                "failed_case": case,
                "failure_origin": True,
                "failure_phase": "marker-exec",
                "image_stop": {"exec": 98765, "verified_ns": 98765, "held": True},
                "output": "/secret",
                "audit_token": [98765],
            }
        )
        + "\n"
    )
    (tmp_path / "control.json").write_text(json.dumps({"failure": "RuntimeError: /secret", "trials": []}))
    result = boundary_ci["failure_summary"]("control", tmp_path / "control.json", tmp_path / "control.log")
    assert result["failed_case"] == case
    assert result["failure_phase"] == "marker-exec"
    assert not any(value in json.dumps(result) for value in ("secret", "98765", "image_stop", "audit_token"))


def test_workflow_runs_tested_checker_without_upload_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text())
    steps = workflow["jobs"]["native-boundary"]["steps"]
    assert steps[-1]["run"].strip() == "python -B scripts/check_macos_boundary_ci_receipts.py"
    assert not any("upload-artifact" in step.get("uses", "") for step in steps)
    assert workflow["permissions"] == {"contents": "read"}


@pytest.mark.parametrize("count", [None, 0, 1, 3, True, False, 2.0, "2"])
def test_modified_target_requires_exactly_two_substitutions(boundary_ci, control_receipt, count):
    trial = next(item for item in control_receipt["trials"] if item["case"] == "exec-modified-target")
    if count is None:
        trial.pop("substitutions_checked")
    else:
        trial["substitutions_checked"] = count
    with pytest.raises((AssertionError, KeyError, ValueError)):
        boundary_ci["checked_receipt"]("control", control_receipt, {"os_build": "26A434"})


def test_optimized_python_cannot_admit_empty_evidence():
    """Optimization must not turn removed assertions into successful admission."""
    command = (
        "import importlib.util, sys; "
        "spec = importlib.util.spec_from_file_location('receipt', sys.argv[1]); "
        "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
        "module.checked_receipt('control', {'trials': [], 'artifacts': []}, {'os_build': 'test'})"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", command, str(ROOT / "scripts/check_macos_boundary_ci_receipts.py")],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert "requires enabled assertions" in result.stderr


def test_native_workflow_covers_runtime_integration_paths():
    import fnmatch

    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text())
    paths = workflow.get("on", workflow.get(True))["pull_request"]["paths"]
    for basename in (
        "runtime_native.py",
        "runtime_builder.py",
        "runtime_interpreter.py",
        "runtime_domains.py",
        "target_bootstrap.py",
    ):
        path = f"packages/specfact-code-review/src/specfact_code_review/run/{basename}"
        assert any(fnmatch.fnmatch(path, pattern) for pattern in paths), path


@pytest.mark.parametrize("kind", ["task", "thread"])
def test_exception_receipt_accepts_explicit_kernel_policy_denial(boundary_ci, kind):
    trial = _control_trial(f"exec-exception-{kind}")
    trial["status"]["output"] = trial["status"]["output"].replace("status=0", "status=53")
    boundary_ci["checked_exception_port"](trial)
    trial["status"]["output"] = trial["status"]["output"].replace("preserved=1", "preserved=0")
    with pytest.raises(AssertionError):
        boundary_ci["checked_exception_port"](trial)
