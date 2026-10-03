"""Only actual boolean states of the failing wait's owned worker may be exported."""

import importlib.util
import json
from pathlib import Path

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
