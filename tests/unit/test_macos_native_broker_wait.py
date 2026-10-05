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
    project, output, temporary = (invocation / name for name in ("project", "output", "temporary"))
    parent.sendall(
        REQUEST.pack(
            0x53464E31,
            1,
            1,
            1,
            0,
            900_000,
            1024,
            16 << 30,
            16 << 20,
            8 << 20,
            _path(invocation),
            _path(project),
            _path(output),
            _path(temporary),
        )
    )
    magic, version, code, handle, _status, detail = _receive(parent)
    if fail_limits:
        assert (magic, version, code, detail) == (0x53464E31, 1, 1, 168)
        diagnostic = json.loads((invocation / "broker.log").read_text())
        assert diagnostic["bootstrap_failure_phase"] == 68
        assert diagnostic["errno"] != 0
        assert not (temporary / "native-self-test.pid").exists()
        parent.close()
        assert broker.wait(timeout=5) == 0
        print("REJECTED_BEFORE_READY", flush=True)
        return
    assert (magic, version, code, detail) == (0x53464E31, 1, 0, 0), (
        (magic, version, code, detail),
        (invocation / "broker.log").read_text(),
    )
    marker = temporary / "native-self-test.pid"
    deadline = time.monotonic() + 5
    while not marker.is_file() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.is_file(), "held worker did not report its PID"
    worker = int(marker.read_text().strip())
    print(json.dumps({"broker": broker.pid, "worker": worker, "handle": handle}), flush=True)
    parent.sendall(REQUEST.pack(0x53464E31, 1, 2, 0, handle, 900_000, 0, 0, 0, 0, b"", b"", b"", b""))
    print("WAIT_SENT", flush=True)
    _receive(parent)  # The parent kills this CLI while the worker is held.
    raise AssertionError("held worker unexpectedly completed WAIT")


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
    observed = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True, timeout=2)
    assert not observed.stderr, observed.stderr
    assert observed.returncode in (0, 1), observed.returncode
    return observed.stdout.strip() or None


def _exercise_controller(*, fail_limits: bool = False) -> None:
    """A 900-second WAIT cannot hide controller death from the signed broker."""
    if sys.platform != "darwin" or os.uname().machine != "arm64" or os.environ.get("SPECFACT_NATIVE_CONTROL") != "1":
        import pytest

        pytest.skip("explicit physical ARM64 native broker run")
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-native-wait-") as directory:
        root = Path(directory).resolve()
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
        for path in capsule.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o500)
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
            assert birth, "worker was not independently visible after launch"
            assert broker_birth, "broker was not independently visible after launch"
            assert _line(controller, 5) == "WAIT_SENT"
            time.sleep(0.1)
            assert controller.poll() is None and _identity(worker_pid) == birth
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
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.wait(timeout=2)
            if worker_pid is not None and birth is not None and _identity(worker_pid) == birth:
                os.kill(worker_pid, signal.SIGKILL)
            if broker_pid is not None and broker_birth is not None and _identity(broker_pid) == broker_birth:
                os.kill(broker_pid, signal.SIGKILL)
            if controller.stdout:
                controller.stdout.close()
            if controller.stderr:
                controller.stderr.close()


def test_cli_death_during_wait_kills_worker_within_five_seconds() -> None:
    _exercise_controller()


def test_failed_bootstrap_reports_numeric_reason_without_running_target() -> None:
    _exercise_controller(fail_limits=True)


if __name__ == "__main__" and sys.argv[1:2] == ["--controller"]:
    _controller(Path(sys.argv[2]), Path(sys.argv[3]))
elif __name__ == "__main__" and sys.argv[1:2] == ["--failure-controller"]:
    _controller(Path(sys.argv[2]), Path(sys.argv[3]), fail_limits=True)
elif __name__ == "__main__" and sys.argv[1:2] == ["--failure-self-test"]:
    test_failed_bootstrap_reports_numeric_reason_without_running_target()
elif __name__ == "__main__" and sys.argv[1:2] == ["--self-test"]:
    test_cli_death_during_wait_kills_worker_within_five_seconds()
