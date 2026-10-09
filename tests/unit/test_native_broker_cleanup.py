import json
from types import SimpleNamespace

import pytest

from tests.native import proof_macos_native_broker_wait as proof
from tests.native.proof_macos_native_broker_wait import (
    test_cleanup_does_not_signal_absent_or_reused_identity as test_cleanup_does_not_signal_absent_or_reused_identity,
    test_cleanup_preserves_permission_failure as test_cleanup_preserves_permission_failure,
    test_cleanup_tolerates_owned_pid_exit_between_observation_and_signal as test_cleanup_tolerates_owned_pid_exit_between_observation_and_signal,
)


@pytest.mark.parametrize("initial", ["", "12"])
def test_controller_waits_for_complete_pid_before_wait(tmp_path, monkeypatch, capsys, initial):
    marker = tmp_path / "native-self-test.pid"
    marker.write_text(initial)
    sent = []
    sleeps = []

    def complete_write(delay):
        sleeps.append(delay)
        marker.write_text("12345\n")

    monkeypatch.setattr(proof.time, "sleep", complete_write)
    monkeypatch.setattr(proof, "_receive", lambda _parent: None)
    with pytest.raises(AssertionError, match="held worker unexpectedly completed WAIT"):
        proof._hold_worker(SimpleNamespace(sendall=sent.append), SimpleNamespace(pid=54321), tmp_path, 9)
    lines = capsys.readouterr().out.splitlines()
    assert json.loads(lines[0]) == {"broker": 54321, "worker": 12345, "handle": 9}
    assert lines[1:] == ["WAIT_SENT"]
    assert sleeps == [0.01]
    assert len(sent) == 1
    assert proof.REQUEST.unpack(sent[0])[:5] == (0x53464E31, 1, 2, 0, 9)


@pytest.mark.parametrize("text", ["", "123"])
def test_controller_rejects_incomplete_pid_at_original_deadline(tmp_path, monkeypatch, text):
    (tmp_path / "native-self-test.pid").write_text(text)
    clock = iter([0, 0, 6])
    monkeypatch.setattr(proof.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(proof.time, "sleep", lambda _delay: None)
    with pytest.raises(AssertionError, match="held worker did not report its PID"):
        proof._hold_worker(None, SimpleNamespace(pid=54321), tmp_path, 9)


@pytest.mark.parametrize("text", ["0\n", "-1\n", "invalid\n"])
def test_controller_rejects_invalid_complete_pid_without_wait(tmp_path, text):
    (tmp_path / "native-self-test.pid").write_text(text)
    with pytest.raises((AssertionError, ValueError)):
        proof._hold_worker(None, SimpleNamespace(pid=54321), tmp_path, 9)
