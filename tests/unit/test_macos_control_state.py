"""Only actual boolean states of the failing wait's owned worker may be exported."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest


SOURCE = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control_state.py"
FIELDS = ("wait_accepted", "wait_pending", "worker_reaped", "output_closed")


@pytest.fixture(name="control_state")
def fixture_control_state():
    spec = importlib.util.spec_from_file_location("control_state_fixture", SOURCE)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def requests():
    return [
        {"opcode": 1, "response": {"handle": 42, "pid": 98765, "output": "private"}},
        {"opcode": 2, "fields": {"handle": 42}},
    ]


def snapshot(pid=98765, **changes):
    return {"control_state": pid, **dict.fromkeys(FIELDS, False), **changes}


def test_last_matching_snapshot_exports_only_booleans(control_state):
    latest = snapshot(wait_accepted=True, wait_pending=True, worker_reaped=True)
    events = "\n".join(
        json.dumps(item)
        for item in (
            snapshot(),
            {**latest, "secret": "/private/capability"},
            snapshot(pid=98766),
        )
    )
    result = control_state.last_worker_state(events, requests(), "request-wait")
    assert result == {field: latest[field] for field in FIELDS}
    assert not any(item in json.dumps(result) for item in ("98765", "98766", "42", "secret", "private"))


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [0, 1, "true", None])
def test_untyped_snapshot_fields_are_not_evidence(control_state, field, value):
    event = json.dumps(snapshot(**{field: value}))
    assert control_state.last_worker_state(event, requests(), "request-wait") == {}


@pytest.mark.parametrize("events", ["", "not-json", '{"control_state":98765}', json.dumps(snapshot(pid=98766))])
def test_missing_or_foreign_state_stays_unknown(control_state, events):
    assert control_state.last_worker_state(events, requests(), "request-wait") == {}


def test_state_is_bound_to_last_failing_wait(control_state):
    history = [*requests(), {"opcode": 2, "fields": {"handle": 43}}]
    assert control_state.last_worker_state(json.dumps(snapshot()), history, "request-wait") == {}


def test_other_failure_phase_exports_no_worker_state(control_state):
    assert control_state.last_worker_state(json.dumps(snapshot()), requests(), "cleanup") == {}


def test_oversize_input_stays_unknown(control_state):
    assert control_state.last_worker_state(" " * 8193, requests(), "request-wait") == {}
    assert control_state.last_worker_state(json.dumps(snapshot()), requests() * 33, "request-wait") == {}


def test_controller_exports_only_owned_last_observation(monkeypatch, tmp_path):
    source = SOURCE.with_name("control.py")
    spec = importlib.util.spec_from_file_location("control_state_integration", source)
    assert spec and spec.loader
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    invocation = object.__new__(control.Invocation)
    invocation.case = "cancel"
    invocation.directory = tmp_path
    invocation.observer = tmp_path / "observer"
    invocation.broker = tmp_path / "broker"
    invocation.service = "private-service"
    invocation.identities = []
    invocation.client = type("ClientHistory", (), {"history": requests()})()
    state = snapshot(wait_accepted=True, wait_pending=True, output_closed=True)
    (tmp_path / "events").write_text(json.dumps({**state, "output": "private"}) + "\n")
    markers = []
    monkeypatch.setattr(control, "_emit_json", markers.append)
    monkeypatch.setattr(control, "_write_diagnostic", lambda _record: tmp_path / "private-diagnostic")
    control._activate_operation(invocation, "request-wait")  # pylint: disable=protected-access
    invocation.retain_failure(TimeoutError("private"))
    assert markers[0]["last_worker_state"] == {field: state[field] for field in FIELDS}
    assert all(isinstance(value, bool) for value in markers[0]["last_worker_state"].values())
    control._activate_operation(None, "request-wait")  # pylint: disable=protected-access
    invocation.retain_failure(TimeoutError("other invocation"))
    assert "last_worker_state" not in markers[-1]


@pytest.fixture(name="control")
def fixture_control():
    spec = importlib.util.spec_from_file_location("raw_wait_control_fixture", SOURCE.with_name("control.py"))
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def raw_wait_client(control, owner=None):
    client = object.__new__(control.Client)
    client.owner = owner
    client.capability = b"x" * 32
    client.history = requests()[:1]
    client.stream = Mock()
    return client


def test_complete_raw_wait_records_before_send(control, monkeypatch):
    client = raw_wait_client(control)
    monkeypatch.setattr(control.time, "monotonic", lambda: 123.5)
    monkeypatch.setattr(control.select, "select", lambda *_args: ([], [], []))
    expected = {"opcode": 2, "fields": {"handle": 42}, "started": 123.5}

    def check_send(packet):
        assert client.history[-1] == expected
        assert packet == control.frame(client.capability, 2, control.FrameFields(handle=42))

    client.stream.sendall.side_effect = check_send
    control._prepare_wait(client, 42, "eof-wait")  # pylint: disable=protected-access
    assert client.history == [requests()[0], expected]
    client.stream.sendall.assert_called_once()


@pytest.mark.parametrize("case", ["eof-wait", "eof-partial", "partial-timeout"])
def test_raw_wait_send_failure_retains_only_complete_attempt(control, monkeypatch, case):
    client = raw_wait_client(control)
    monkeypatch.setattr(control.time, "monotonic", lambda: 123.5)
    client.stream.sendall.side_effect = OSError("send failed")
    with pytest.raises(OSError, match="send failed"):
        control._prepare_wait(client, 42, case)  # pylint: disable=protected-access
    expected = requests()[:1]
    if case == "eof-wait":
        expected.append({"opcode": 2, "fields": {"handle": 42}, "started": 123.5})
    assert client.history == expected


@pytest.mark.parametrize("raw", [True, False])
def test_wait_history_keeps_newest_64_records(control, monkeypatch, raw):
    client = raw_wait_client(control)
    client.history = [{"opcode": 3, "fields": {"handle": handle}} for handle in range(64)]
    retained = client.history[1:]
    monkeypatch.setattr(control.select, "select", lambda *_args: ([], [], []))
    monkeypatch.setattr(control, "response", lambda _stream: {"version": 1, "ok": True})
    if raw:
        control._prepare_wait(client, 42, "eof-wait")  # pylint: disable=protected-access
    else:
        client.request(2, handle=42)
    assert len(client.history) == 64
    assert client.history[:-1] == retained
    assert client.history[-1]["opcode"] == 2
    assert client.history[-1]["fields"] == {"handle": 42}


@pytest.mark.parametrize("case", ["eof-wait", "eof-partial", "partial-timeout"])
def test_raw_wait_controller_exports_state_only_for_complete_frame(control, monkeypatch, tmp_path, case):
    invocation = object.__new__(control.Invocation)
    invocation.case = case
    invocation.directory = tmp_path
    invocation.observer = tmp_path / "observer"
    invocation.broker = tmp_path / "broker"
    invocation.service = "private-service"
    invocation.identities = []
    client = raw_wait_client(control, invocation)
    invocation.client = client
    state = snapshot(wait_accepted=True, wait_pending=True, output_closed=True)
    (tmp_path / "events").write_text(json.dumps(state) + "\n")
    markers, diagnostics = [], []
    monkeypatch.setattr(control.select, "select", lambda *_args: ([], [], []))
    monkeypatch.setattr(control, "_emit_json", markers.append)

    def retain(record):
        diagnostics.append(record)
        return tmp_path / "private-diagnostic"

    monkeypatch.setattr(control, "_write_diagnostic", retain)
    try:
        control._prepare_wait(client, 42, case)  # pylint: disable=protected-access
        invocation.retain_failure(TimeoutError("observation failed"))
    finally:
        control._activate_operation(None, "unknown")  # pylint: disable=protected-access
    packet = control.frame(client.capability, 2, control.FrameFields(handle=42))
    client.stream.sendall.assert_called_once_with(packet if case == "eof-wait" else packet[:13])
    assert diagnostics[0]["failure_phase"] == "request-wait"
    assert markers[0]["failure_origin"] is True
    if case == "eof-wait":
        assert markers[0]["last_worker_state"] == {field: state[field] for field in FIELDS}
        assert diagnostics[0]["requests"][-1]["fields"] == {"handle": 42}
    else:
        assert client.history == requests()[:1]
        assert "last_worker_state" not in markers[0]
