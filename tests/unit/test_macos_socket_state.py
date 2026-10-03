"""Socket evidence projects only fixed categories from the original owning failure."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOCKET_STATES = (
    "directory_invalid",
    "private_after_deadline",
    "socket_missing",
    "socket_mode_pending",
    "socket_owner_invalid",
    "socket_type_invalid",
)


@pytest.fixture(name="control")
def fixture_control():
    spec = importlib.util.spec_from_file_location(
        "socket_state_control", ROOT / "scripts/macos_managed_boundary/control.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="invocation")
def fixture_invocation(control, tmp_path):
    invocation = object.__new__(control.Invocation)
    invocation.case = "protocol"
    invocation.phase = "cleanup"  # The original failure stamp, not mutable phase, is authoritative.
    invocation.service = "private-service-98765"
    invocation.directory = tmp_path
    invocation.identities = []
    invocation.client = None
    invocation.broker = tmp_path / "absent-broker"
    invocation.observer = tmp_path / "absent-observer"
    return invocation


def emitted_marker(control, invocation, error):
    with (
        patch.object(control, "_write_diagnostic", return_value=Path("diagnostic")),
        patch.object(control, "_emit_json") as emit,
    ):
        invocation.retain_failure(error)
    emit.assert_called_once()
    marker = emit.call_args.args[0]
    assert not any(
        item in json.dumps(marker) for item in ("secret", "98765", "authority", '"audit_token"', '"socket_mode"')
    )
    return marker


@pytest.mark.parametrize("state", SOCKET_STATES)
def test_socket_state_projects_original_owning_bootstrap_failure(control, invocation, state):
    error = RuntimeError("/secret/authority UID 98765 socket_mode 0777")
    error.__dict__.update(
        _native_socket_state=state,
        _control_failure_origin=(invocation, "bootstrap-socket"),
        audit_token=[98765],
    )
    marker = emitted_marker(control, invocation, error)
    assert marker["bootstrap_socket_state"] == state
    assert marker["failure_origin"] is True
    assert marker["failure_phase"] == "bootstrap-socket"


@pytest.mark.parametrize(
    "state", [None, False, 1, [], {}, b"socket_missing", "/secret/98765", "socket_missing /secret"]
)
def test_socket_state_rejects_unknown_and_malformed_values(control, invocation, state):
    error = RuntimeError("/secret/98765")
    error.__dict__.update(_native_socket_state=state, _control_failure_origin=(invocation, "bootstrap-socket"))
    assert "bootstrap_socket_state" not in emitted_marker(control, invocation, error)


@pytest.mark.parametrize("phase", ["cleanup", "bootstrap-register", "request-wait", "unknown"])
def test_socket_state_rejects_other_original_phases(control, invocation, phase):
    error = RuntimeError("/secret/98765")
    error.__dict__.update(_native_socket_state="socket_missing", _control_failure_origin=(invocation, phase))
    invocation.phase = "bootstrap-socket"
    assert "bootstrap_socket_state" not in emitted_marker(control, invocation, error)


@pytest.mark.parametrize("owner", [None, object(), SimpleNamespace()])
def test_socket_state_rejects_nonowning_failures(control, invocation, owner):
    error = RuntimeError("/secret/98765")
    error.__dict__.update(_native_socket_state="socket_missing", _control_failure_origin=(owner, "bootstrap-socket"))
    assert "bootstrap_socket_state" not in emitted_marker(control, invocation, error)


def test_socket_state_absent_attribute_is_omitted(control, invocation):
    error = RuntimeError("socket_missing /secret/98765")
    error.__dict__["_control_failure_origin"] = (invocation, "bootstrap-socket")
    assert "bootstrap_socket_state" not in emitted_marker(control, invocation, error)


def test_socket_state_rejects_string_subclass(control, invocation):
    class PrivateString(str):
        def __str__(self):
            return "/secret/98765"

    error = RuntimeError("/secret/98765")
    error.__dict__.update(
        _native_socket_state=PrivateString("socket_missing"), _control_failure_origin=(invocation, "bootstrap-socket")
    )
    assert "bootstrap_socket_state" not in emitted_marker(control, invocation, error)
