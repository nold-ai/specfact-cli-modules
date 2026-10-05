"""Socket evidence projects only fixed categories from the original owning failure."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

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


@pytest.mark.parametrize("failure", [ConnectionRefusedError, PermissionError, ConnectionResetError])
def test_private_socket_connect_waits_only_for_refused_listener(control, tmp_path, failure):
    first, second = Mock(), Mock()
    first.connect.side_effect = failure("private detail")
    with (
        patch.object(control.SOCKET, "_private_socket_state", return_value="private"),
        patch.object(control.SOCKET.socket, "socket", side_effect=[first, second]) as factory,
        patch.object(control.SOCKET.time, "monotonic", return_value=10.0),
        patch.object(control.SOCKET.time, "sleep") as sleep,
    ):
        if failure is ConnectionRefusedError:
            assert control.SOCKET.connect_private_socket(tmp_path / "control.sock") is second
            first.close.assert_called_once()
            second.close.assert_not_called()
            assert factory.call_count == 2
            sleep.assert_called_once()
        else:
            with pytest.raises(failure):
                control.SOCKET.connect_private_socket(tmp_path / "control.sock")
            first.close.assert_called_once()
            assert factory.call_count == 1
            sleep.assert_not_called()
        first.sendall.assert_not_called()
        second.sendall.assert_not_called()


def test_private_socket_connection_cannot_extend_original_budget(control, tmp_path):
    stream = Mock()
    refused = ConnectionRefusedError("private detail")
    stream.connect.side_effect = refused
    with (
        patch.object(control.SOCKET, "_private_socket_state", return_value="private"),
        patch.object(control.SOCKET.socket, "socket", return_value=stream) as factory,
        patch.object(control.SOCKET.time, "monotonic", side_effect=[10.0, 10.0, 10.0, 17.0]),
        patch.object(control.SOCKET.time, "sleep") as sleep,
        pytest.raises(ConnectionRefusedError) as raised,
    ):
        control.SOCKET.connect_private_socket(tmp_path / "control.sock")
    assert raised.value is refused
    factory.assert_called_once()
    stream.settimeout.assert_called_once_with(7.0)
    stream.close.assert_called_once()
    sleep.assert_not_called()


def test_client_authenticates_once_after_listener_becomes_ready(control, tmp_path):
    first, second = Mock(), Mock()
    first.connect.side_effect = ConnectionRefusedError("not listening")
    with (
        patch.object(control.SOCKET, "_private_socket_state", return_value="private"),
        patch.object(control.socket, "socket", side_effect=[first, second]),
        patch.object(control.SOCKET.time, "monotonic", return_value=10.0),
        patch.object(control.SOCKET.time, "sleep"),
        patch.object(control.Client, "request", return_value={"state": "authenticated"}) as authenticate,
    ):
        client = control.Client(tmp_path / "control.sock", b"x" * 32)
    assert client.stream is second
    first.close.assert_called_once()
    authenticate.assert_called_once_with(0)


@pytest.mark.parametrize("changed_state", ["socket_missing", "socket_mode_pending", "socket_owner_invalid"])
def test_refused_listener_rechecks_private_metadata_before_next_socket(control, tmp_path, changed_state):
    stream = Mock()
    stream.connect.side_effect = ConnectionRefusedError()
    with (
        patch.object(control.SOCKET, "_private_socket_state", side_effect=["private", changed_state]),
        patch.object(control.SOCKET.socket, "socket", return_value=stream) as factory,
        patch.object(control.SOCKET.time, "monotonic", return_value=10.0),
        patch.object(control.SOCKET.time, "sleep"),
        pytest.raises(RuntimeError, match="private socket changed"),
    ):
        control.SOCKET.connect_private_socket(tmp_path / "control.sock")
    factory.assert_called_once()
    stream.close.assert_called_once()
    stream.sendall.assert_not_called()


def test_connected_socket_after_deadline_is_closed(control, tmp_path):
    stream = Mock()
    with (
        patch.object(control.SOCKET, "_private_socket_state", return_value="private"),
        patch.object(control.SOCKET.socket, "socket", return_value=stream) as factory,
        patch.object(control.SOCKET.time, "monotonic", side_effect=[10.0, 10.0, 10.0, 17.0]),
        pytest.raises(TimeoutError, match="connection budget exceeded"),
    ):
        control.SOCKET.connect_private_socket(tmp_path / "control.sock")
    factory.assert_called_once()
    stream.close.assert_called_once()
    stream.sendall.assert_not_called()


def test_failed_authentication_closes_stream_without_reconnecting(control, tmp_path):
    stream = Mock()
    with (
        patch.object(control.SOCKET, "connect_private_socket", return_value=stream) as connect,
        patch.object(control.Client, "request", return_value={"state": "rejected"}) as authenticate,
        pytest.raises(RuntimeError, match="authentication failed"),
    ):
        control.Client(tmp_path / "control.sock", b"x" * 32)
    connect.assert_called_once()
    authenticate.assert_called_once_with(0)
    stream.close.assert_called_once()


@pytest.mark.parametrize("after_metadata", [16.0, 17.0])
def test_metadata_checks_cannot_extend_connection_budget(control, tmp_path, after_metadata):
    stream = Mock()
    with (
        patch.object(control.SOCKET, "_private_socket_state", return_value="private"),
        patch.object(control.SOCKET.socket, "socket", return_value=stream),
        patch.object(control.SOCKET.time, "monotonic", side_effect=[10.0, 10.0, after_metadata, 16.5]),
    ):
        if after_metadata == 17.0:
            with pytest.raises(TimeoutError):
                control.SOCKET.connect_private_socket(tmp_path / "control.sock")
            stream.connect.assert_not_called()
            stream.close.assert_called_once()
        else:
            assert control.SOCKET.connect_private_socket(tmp_path / "control.sock") is stream
            stream.settimeout.assert_called_once_with(1.0)
            stream.close.assert_not_called()
