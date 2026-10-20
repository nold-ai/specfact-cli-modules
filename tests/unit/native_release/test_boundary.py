import errno
import hashlib
import json
import os
import socket
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.native_release import boundary


@pytest.fixture
def delivered_component(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "provenance").mkdir()
    records = {}
    for name in boundary.COMPONENT_FILES:
        path = source / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(name.encode())
        records[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (source / "provenance/native-component.json").write_text(json.dumps({"files": records}))
    return source


def test_delivered_component_copy_rejects_substitution_before_launch(delivered_component, tmp_path):
    source = delivered_component
    (source / "bin/specfact-native-broker").write_bytes(b"substitution")
    with pytest.raises(ValueError, match="component"):
        boundary.copy_component(source, tmp_path / "copy")
    assert not (tmp_path / "copy").exists()


def test_delivered_component_has_broker_required_private_readonly_modes(delivered_component, tmp_path):
    destination = tmp_path / "copy"
    boundary.copy_component(delivered_component, destination)
    for path in [destination, *destination.rglob("*")]:
        expected = 0o700 if path.is_dir() else 0o500 if path.parent.name == "bin" else 0o400
        assert path.stat().st_mode & 0o777 == expected


def test_worker_cleanup_rejects_observation_after_five_seconds(monkeypatch, tmp_path):
    from types import SimpleNamespace

    clock = [0.0]
    killed = [False]
    lines = iter([json.dumps({"worker": 11, "broker": 12}), "WAIT_SENT"])

    def kill():
        killed[0] = True

    def wait(*, timeout):
        clock[0] = 2.0

    def identity(pid):
        if killed[0]:
            clock[0] = 6.0
            return None
        return str(pid)

    monkeypatch.setattr(boundary.harness, "_line", lambda *_args: next(lines))
    monkeypatch.setattr(boundary.harness, "_identity", identity)
    monkeypatch.setattr(boundary.time, "monotonic", lambda: clock[0])
    controller = SimpleNamespace(kill=kill, wait=wait)
    with pytest.raises(ValueError, match="controller loss"):
        boundary._assert_worker_cleanup(controller, tmp_path, exception_probe=False)


def _hold_worker_pid(temporary, capsys):
    parent, peer = socket.socketpair()
    parent.settimeout(2)
    peer.settimeout(2)
    requests = []
    peer_errors = []
    broker = SimpleNamespace(pid=os.getpid())
    handle = 41

    def reply_to_wait():
        try:
            request = bytearray()
            while len(request) < boundary.harness.REQUEST.size:
                chunk = peer.recv(boundary.harness.REQUEST.size - len(request))
                if not chunk:
                    return
                request.extend(chunk)
            requests.append(bytes(request))
            peer.sendall(boundary.harness.REPLY.pack(0x53464E31, 1, 0, handle, 0, 0))
        except OSError as error:
            peer_errors.append(error)

    responder = threading.Thread(target=reply_to_wait, name="pid-observation-wait-peer")
    responder.start()
    try:
        try:
            boundary.harness._hold_worker(parent, broker, temporary, handle)
        except AssertionError as error:
            if str(error) != "held worker unexpectedly completed WAIT":
                raise
        else:
            pytest.fail("held worker returned without its unexpected-WAIT-completion assertion")
    finally:
        parent.close()
        responder.join(timeout=3)
        peer.close()
        assert not responder.is_alive(), "WAIT peer did not stop"
    assert not peer_errors
    assert requests == [
        boundary.harness.REQUEST.pack(0x53464E31, 1, 2, 0, handle, 900_000, 0, 0, 0, 0, b"", b"", b"", b"")
    ]
    output = capsys.readouterr()
    assert output.err == ""
    lines = output.out.splitlines()
    assert len(lines) == 2
    reported = json.loads(lines[0])
    assert reported == {"broker": broker.pid, "worker": reported["worker"], "handle": handle}
    assert lines[1] == "WAIT_SENT"
    return reported["worker"]


@pytest.fixture(params=["controller", "sibling"])
def observe_pid(request, capsys):
    if request.param == "controller":
        return lambda temporary: _hold_worker_pid(temporary, capsys)
    from tests.unit.specfact_code_review.run.test_native_execution import _worker_pid

    return _worker_pid


@pytest.fixture
def pid_clock(monkeypatch):
    clock = SimpleNamespace(now=0.0, sleeps=[])

    def sleep(seconds):
        assert 0 < seconds <= 0.01
        assert len(clock.sleeps) < 502, "PID observation renewed its deadline"
        clock.sleeps.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(boundary.harness.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(boundary.harness.time, "sleep", sleep)
    return clock


@pytest.mark.parametrize("record", [b"7\n", b"0007\n", b"1" * 30 + b"\n"], ids=["positive", "leading-zero", "31-bytes"])
def test_pid_observation_accepts_complete_record(observe_pid, tmp_path, monkeypatch, record):
    (tmp_path / "native-self-test.pid").write_bytes(record)

    def unexpected_sleep(_seconds):
        pytest.fail("complete PID record was treated as pending")

    monkeypatch.setattr(boundary.harness.time, "sleep", unexpected_sleep)
    assert observe_pid(tmp_path) == int(record)


@pytest.mark.parametrize("initial", ["empty", "numeric-prefix"])
def test_pid_observation_waits_for_publication(observe_pid, tmp_path, monkeypatch, initial):
    marker = tmp_path / "native-self-test.pid"
    pid = os.getpid()
    record = f"{pid}\n".encode("ascii")
    prefix = b"" if initial == "empty" else record[:1]
    created = threading.Event()
    publish = threading.Event()
    writer_errors = []
    polls = []

    def write_pid():
        try:
            descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                if prefix:
                    assert os.write(descriptor, prefix) == len(prefix)
                created.set()
                assert publish.wait(timeout=3), "reader never released PID publication"
                assert os.write(descriptor, record[len(prefix) :]) == len(record) - len(prefix)
            finally:
                os.close(descriptor)
        except BaseException as error:
            writer_errors.append(error)
            created.set()

    writer = threading.Thread(target=write_pid, name="pid-observation-writer")

    def finish_publication(seconds):
        assert 0 < seconds <= 0.01
        polls.append(seconds)
        publish.set()
        writer.join(timeout=2)
        assert not writer.is_alive(), "PID writer did not stop after publication"
        assert not writer_errors

    writer.start()
    try:
        assert created.wait(timeout=2), "PID marker was not created"
        assert not writer_errors
        assert marker.read_bytes() == prefix
        monkeypatch.setattr(boundary.harness.time, "sleep", finish_publication)
        assert observe_pid(tmp_path) == pid
        assert polls, "reader accepted incomplete publication before pending poll"
    finally:
        publish.set()
        writer.join(timeout=3)
        assert not writer.is_alive(), "PID writer survived cleanup"
        assert not writer_errors
    assert marker.read_bytes() == record


@pytest.mark.parametrize("pending", ["absent", "empty", "incomplete"])
def test_pid_observation_pending_times_out(observe_pid, tmp_path, pid_clock, capsys, pending):
    marker = tmp_path / "native-self-test.pid"
    if pending != "absent":
        marker.write_bytes(b"" if pending == "empty" else b"123")
    with pytest.raises(AssertionError):
        observe_pid(tmp_path)
    assert pid_clock.now == pytest.approx(5.0)
    assert sum(pid_clock.sleeps) == pytest.approx(5.0)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "record",
    [
        b"0\n",
        b"-1\n",
        b"+1\n",
        b" 1\n",
        b"1 \n",
        b"\n",
        b"1\n2\n",
        b"1\nx",
        b"\xff\n",
        b"1" * 31 + b"\n",
        b"1" * 32,
        b"x",
        b"1\r\n",
    ],
    ids=[
        "zero",
        "negative",
        "plus",
        "leading-space",
        "trailing-space",
        "empty-line",
        "multiline",
        "trailing-bytes",
        "non-ascii",
        "32-bytes",
        "oversize-incomplete",
        "nondigit-incomplete",
        "crlf",
    ],
)
def test_pid_observation_rejects_invalid_record(observe_pid, tmp_path, monkeypatch, capsys, record):
    (tmp_path / "native-self-test.pid").write_bytes(record)

    def unexpected_sleep(_seconds):
        pytest.fail("invalid PID record was retried")

    monkeypatch.setattr(boundary.harness.time, "sleep", unexpected_sleep)
    with pytest.raises(ValueError):
        observe_pid(tmp_path)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("late", [5.0, 5.1], ids=["at-deadline", "after-deadline"])
def test_pid_observation_rejects_late_record(observe_pid, tmp_path, monkeypatch, capsys, late):
    (tmp_path / "native-self-test.pid").write_bytes(b"123\n")
    observations = iter([0.0, 0.0])
    monkeypatch.setattr(boundary.harness.time, "monotonic", lambda: next(observations, late))
    with pytest.raises(AssertionError):
        observe_pid(tmp_path)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_pid_observation_rejects_nonregular_marker(observe_pid, tmp_path, pid_clock, capsys, kind):
    marker = tmp_path / "native-self-test.pid"
    if kind == "symlink":
        target = tmp_path / "actual-pid"
        target.write_bytes(b"123\n")
        marker.symlink_to(target)
    elif kind == "directory":
        marker.mkdir()
    else:
        os.mkfifo(marker, 0o600)
    with pytest.raises((ValueError, OSError)):
        observe_pid(tmp_path)
    assert pid_clock.sleeps == []
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("error_number", [errno.EACCES, errno.EIO], ids=["permission", "io"])
def test_pid_observation_propagates_io_error(observe_pid, tmp_path, monkeypatch, capsys, error_number):
    marker = tmp_path / "native-self-test.pid"
    marker.write_bytes(b"123\n")
    failure = OSError(error_number, "PID marker unavailable")
    original_open = os.open
    original_path_open = Path.open

    def fail_open(path, *args, **kwargs):
        if Path(path) == marker:
            raise failure
        return original_open(path, *args, **kwargs)

    def fail_path_open(path, *args, **kwargs):
        if path == marker:
            raise failure
        return original_path_open(path, *args, **kwargs)

    def unexpected_sleep(_seconds):
        pytest.fail("ordinary PID marker I/O failure was retried")

    monkeypatch.setattr(os, "open", fail_open)
    monkeypatch.setattr(Path, "open", fail_path_open)
    monkeypatch.setattr(boundary.harness.time, "sleep", unexpected_sleep)
    with pytest.raises(OSError) as caught:
        observe_pid(tmp_path)
    assert caught.value is failure
    assert capsys.readouterr().out == ""
