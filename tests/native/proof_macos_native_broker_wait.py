"""Physical controller-loss proof for the ad-hoc-signed native broker."""

from __future__ import annotations

import json
import os
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path


SOURCE = Path(__file__).parents[2] / "packages/specfact-code-review/native/macos-arm64"
REQUEST = struct.Struct("<IHHIIIIQQQ1024s1024s1024s1024s")
REPLY = struct.Struct("<IHHIiI")


def _path(path: Path) -> bytes:
    return os.fsencode(path).ljust(1024, b"\0")


def _receive(channel: socket.socket) -> tuple[int, int, int, int, int, int]:
    data = bytearray()
    while len(data) < REPLY.size:
        chunk = channel.recv(REPLY.size - len(data))
        if not chunk:
            raise RuntimeError("broker closed before reply")
        data.extend(chunk)
    return REPLY.unpack(data)


def _assert_bootstrap_failure(parent, broker, invocation: Path, reply) -> None:
    assert reply == (0x53464E31, 1, 1, 168)
    diagnostic = json.loads((invocation / "broker.log").read_text())
    assert diagnostic["bootstrap_failure_phase"] == 68
    assert diagnostic["errno"] != 0
    assert not (invocation / "temporary/native-self-test.pid").exists()
    parent.close()
    assert broker.wait(timeout=5) == 0
    sys.stdout.write("REJECTED_BEFORE_READY\n")
    sys.stdout.flush()


def _worker_pid(temporary: Path) -> int:
    """Await the complete owned marker write within the existing launch deadline."""
    marker = temporary / "native-self-test.pid"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            contents = marker.read_text()
        except FileNotFoundError:
            contents = ""
        if contents.endswith("\n"):
            worker = int(contents.strip())
            assert worker > 0, "held worker reported an invalid PID"
            return worker
        time.sleep(0.01)
    raise AssertionError("held worker did not report its PID")


def _hold_worker(parent, broker, temporary: Path, handle: int) -> None:
    worker = _worker_pid(temporary)
    sys.stdout.write(json.dumps({"broker": broker.pid, "worker": worker, "handle": handle}) + "\n")
    sys.stdout.flush()
    parent.sendall(REQUEST.pack(0x53464E31, 1, 2, 0, handle, 900_000, 0, 0, 0, 0, b"", b"", b"", b""))
    sys.stdout.write("WAIT_SENT\n")
    sys.stdout.flush()
    _receive(parent)  # The parent kills this CLI while the worker is held.
    raise AssertionError("held worker unexpectedly completed WAIT")


def _launch_request(invocation: Path) -> bytes:
    paths = (
        _path(path) for path in (invocation, invocation / "project", invocation / "output", invocation / "temporary")
    )
    return REQUEST.pack(0x53464E31, 1, 1, 1, 0, 900_000, 1024, 16 << 30, 16 << 20, 8 << 20, *paths)


def _controller(capsule: Path, invocation: Path, *, fail_limits: bool = False) -> None:
    """Run the disposable CLI process; the test parent never owns its channel."""
    if fail_limits:
        import resource

        # A real hard-limit refusal before READY; production request/profile are unchanged.
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    parent, child = socket.socketpair()
    broker_path = capsule / "bin/specfact-native-broker"
    with (invocation / "broker.log").open("w") as log:
        broker = subprocess.Popen(
            [str(broker_path), "--control-fd", str(child.fileno()), "--capsule-root", str(capsule)],
            pass_fds=(child.fileno(),),
            env={"LANG": "C", "LC_ALL": "C", "SPECFACT_CAPSULE_ROOT": str(capsule)},
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
        )
    child.close()
    stopped, status = os.waitpid(broker.pid, os.WUNTRACED)
    assert stopped == broker.pid and os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP
    requirement = json.loads((capsule / "component.json").read_text())["broker_designated_requirement"]
    subprocess.run(
        [str(capsule / "bin/specfact-native-verifier"), str(broker.pid), requirement],
        check=True,
        timeout=5,
    )
    os.kill(broker.pid, signal.SIGCONT)
    temporary = invocation / "temporary"
    parent.sendall(_launch_request(invocation))
    magic, version, code, handle, _status, detail = _receive(parent)
    if fail_limits:
        _assert_bootstrap_failure(parent, broker, invocation, (magic, version, code, detail))
        return
    assert (magic, version, code, detail) == (0x53464E31, 1, 0, 0), (
        (magic, version, code, detail),
        (invocation / "broker.log").read_text(),
    )
    _hold_worker(parent, broker, temporary, handle)


def _line(process: subprocess.Popen[str], timeout: float) -> str:
    stream = process.stdout
    assert stream is not None
    deadline = time.monotonic() + timeout
    line = bytearray()
    while time.monotonic() < deadline:
        ready, _, _ = select.select([stream], [], [], max(0, deadline - time.monotonic()))
        if not ready:
            break
        byte = os.read(stream.fileno(), 1)
        if byte == b"\n":
            return line.decode()
        if not byte:
            break
        line.extend(byte)
    diagnostic = process.stderr.read() if process.poll() is not None and process.stderr else ""
    raise AssertionError(f"controller did not report launch and WAIT: {process.poll()}: {diagnostic}")


def _identity(pid: int) -> str | None:
    """Observe a process externally; a reused PID has a different start time."""
    observed = subprocess.run(
        ["/bin/ps", "-p", str(pid), "-o", "lstart="], check=False, capture_output=True, text=True, timeout=2
    )
    assert not observed.stderr, observed.stderr
    assert observed.returncode in (0, 1), observed.returncode
    return observed.stdout.strip() or None


def _cleanup_owned_process(pid: int | None, birth: str | None) -> None:
    if pid is None or birth is None or _identity(pid) != birth:
        return
    with suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)


def test_cleanup_tolerates_owned_pid_exit_between_observation_and_signal(monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "_identity", lambda _pid: "observed-birth")
    signaled = []

    def signal_exited(pid, value):
        signaled.append((pid, value))
        raise ProcessLookupError("owned process has exited")

    monkeypatch.setattr(os, "kill", signal_exited)
    _cleanup_owned_process(42, "observed-birth")
    import pytest

    with pytest.raises(AssertionError, match="original proof failure"):
        try:
            raise AssertionError("original proof failure")
        finally:
            _cleanup_owned_process(42, "observed-birth")
    assert signaled == [(42, signal.SIGKILL)] * 2


def test_cleanup_preserves_permission_failure(monkeypatch):
    import pytest

    monkeypatch.setattr(sys.modules[__name__], "_identity", lambda _pid: "observed-birth")

    def denied(*_args):
        raise PermissionError("controlled denial")

    monkeypatch.setattr(os, "kill", denied)
    with pytest.raises(PermissionError, match="controlled denial"):
        _cleanup_owned_process(42, "observed-birth")


def test_cleanup_does_not_signal_absent_or_reused_identity(monkeypatch):
    calls = []
    monkeypatch.setattr(os, "kill", lambda *args: calls.append(args))
    for observed in (None, "other-birth"):
        monkeypatch.setattr(sys.modules[__name__], "_identity", lambda _pid, expected=observed: expected)
        for pid, birth in ((None, "observed-birth"), (42, None), (42, "observed-birth")):
            _cleanup_owned_process(pid, birth)
    assert calls == []


def _prepare_invocation(root: Path, probe_exceptions: bool) -> tuple[Path, Path]:
    capsule, invocation = root / "capsule", root / "invocation"
    capsule.mkdir(mode=0o700)
    invocation.mkdir(mode=0o700)
    for name, mode in (("project", 0o500), ("output", 0o700), ("temporary", 0o700)):
        (invocation / name).mkdir(mode=mode)
    (invocation / "temporary/hold").touch()
    requirement = root / "python.requirement"
    requirement.write_text('cdhash H"0000000000000000000000000000000000000000"\n')
    subprocess.run(
        [str(SOURCE / "build.sh")],
        check=True,
        timeout=60,
        capture_output=True,
        env={
            **os.environ,
            "SPECFACT_NATIVE_BUILD_DIR": str(capsule),
            "SPECFACT_PYTHON_REQUIREMENT_FILE": str(requirement),
        },
    )
    if probe_exceptions:
        positive = root / "positive"
        positive.mkdir()
        (positive / "exception-port-probe").touch()
        completed = subprocess.run(
            [str(capsule / "bin/specfact-native-self-test"), str(positive)],
            capture_output=True,
            timeout=5,
            check=False,
        )
        assert completed.returncode == 37
        values = json.loads((positive / "exception-port-results.json").read_text())
        assert values == [0, 0, 0, 0], "exception-port positive controls are not valid"
        (invocation / "temporary/exception-port-probe").touch()
    for path in capsule.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o500)
    return capsule, invocation


def _assert_held_controller(
    controller, invocation: Path, probe_exceptions: bool, identities: tuple[int, str | None, str | None]
) -> str:
    worker_pid, birth, broker_birth = identities
    if probe_exceptions:
        values = json.loads((invocation / "temporary/exception-port-results.json").read_text())
        assert len(values) == 4 and all(value != 0 for value in values), "exception-port change escaped confinement"
    assert birth, "worker was not independently visible after launch"
    assert broker_birth, "broker was not independently visible after launch"
    assert _line(controller, 5) == "WAIT_SENT"
    time.sleep(0.1)
    assert controller.poll() is None and _identity(worker_pid) == birth
    return birth


def _assert_worker_dies_with_controller(controller, worker_pid: int, birth: str) -> None:
    started = time.monotonic()
    controller.kill()
    controller.wait(timeout=2)
    deadline = started + 5
    observed_absent_at = None
    while time.monotonic() < deadline:
        if _identity(worker_pid) != birth:
            observed_absent_at = time.monotonic()
            break
        time.sleep(0.02)
    assert observed_absent_at is not None, "worker survived controller death during WAIT for five seconds"
    assert observed_absent_at - started <= 5


def _stop_controller(controller) -> None:
    if controller.poll() is None:
        controller.kill()
        controller.wait(timeout=2)


def _close_streams(controller) -> None:
    for stream in (controller.stdout, controller.stderr):
        if stream:
            stream.close()


def _exercise_controller(*, fail_limits: bool = False, probe_exceptions: bool = False) -> None:
    """A 900-second WAIT cannot hide controller death from the signed broker."""
    if sys.platform != "darwin" or os.uname().machine != "arm64" or os.environ.get("SPECFACT_NATIVE_CONTROL") != "1":
        import pytest

        pytest.skip("explicit physical ARM64 native broker run")
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-native-wait-") as directory:
        root = Path(directory).resolve()
        capsule, invocation = _prepare_invocation(root, probe_exceptions)
        controller = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--failure-controller" if fail_limits else "--controller",
                str(capsule),
                str(invocation),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        worker_pid = broker_pid = None
        birth = broker_birth = None
        try:
            if fail_limits:
                assert _line(controller, 20) == "REJECTED_BEFORE_READY"
                assert controller.wait(timeout=5) == 0
                return
            launched = json.loads(_line(controller, 20))
            worker_pid, broker_pid = launched["worker"], launched["broker"]
            birth = _identity(worker_pid)
            broker_birth = _identity(broker_pid)
            birth = _assert_held_controller(controller, invocation, probe_exceptions, (worker_pid, birth, broker_birth))
            _assert_worker_dies_with_controller(controller, worker_pid, birth)
        finally:
            _stop_controller(controller)
            _cleanup_owned_process(worker_pid, birth)
            _cleanup_owned_process(broker_pid, broker_birth)
            _close_streams(controller)


def test_cli_death_during_wait_kills_worker_within_five_seconds() -> None:
    _exercise_controller()


def test_failed_bootstrap_reports_numeric_reason_without_running_target() -> None:
    _exercise_controller(fail_limits=True)


def test_task_and_thread_exception_changes_are_denied_by_kernel() -> None:
    _exercise_controller(probe_exceptions=True)


if __name__ == "__main__" and sys.argv[1:2] == ["--controller"]:
    _controller(Path(sys.argv[2]), Path(sys.argv[3]))
elif __name__ == "__main__" and sys.argv[1:2] == ["--exception-self-test"]:
    test_task_and_thread_exception_changes_are_denied_by_kernel()
elif __name__ == "__main__" and sys.argv[1:2] == ["--failure-controller"]:
    _controller(Path(sys.argv[2]), Path(sys.argv[3]), fail_limits=True)
elif __name__ == "__main__" and sys.argv[1:2] == ["--failure-self-test"]:
    test_failed_bootstrap_reports_numeric_reason_without_running_target()
elif __name__ == "__main__" and sys.argv[1:2] == ["--self-test"]:
    test_cli_death_during_wait_kills_worker_within_five_seconds()
