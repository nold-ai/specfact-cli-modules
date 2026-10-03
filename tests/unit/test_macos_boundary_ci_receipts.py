"""CI acceptance cannot omit required controls or overlap timed-out native suites."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
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
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text())
    code = workflow["jobs"]["native-boundary"]["steps"][-1]["run"]
    tree = ast.parse(code.split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0])
    tree.body = [node for node in tree.body if not isinstance(node, ast.Raise)]
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
