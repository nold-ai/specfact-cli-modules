from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import native_execution
from tests.native.proof_macos_native_broker_wait import wait_worker_pid as _worker_pid
from tests.unit.specfact_code_review.run.test_native_execution import request


NATIVE_REPETITIONS = range(int(os.environ.get("SPECFACT_NATIVE_EXECUTION_REPETITIONS", "1")))


def _physical_lease(source: Path, tmp_path: Path) -> tuple[SimpleNamespace, dict[str, Path], dict[str, int]]:
    capsule = tmp_path / "capsule"
    shutil.copytree(source, capsule)
    for directory, _children, files in os.walk(capsule):
        Path(directory).chmod(0o700)
        for name in files:
            path = Path(directory) / name
            path.chmod(0o500 if path.parent.name == "bin" else 0o400)
    invocation = tmp_path / "invocation"
    project = invocation / "project"
    output = invocation / "output"
    temporary = invocation / "tmp"
    for path in (invocation, project, output, temporary):
        path.mkdir()
        path.chmod(0o700)
    project.chmod(0o500)
    members = {
        "bin/specfact-native-broker": capsule / "bin/specfact-native-broker",
        "bin/specfact-native-bootstrap": capsule / "bin/specfact-native-bootstrap",
        "bin/specfact-native-verifier": capsule / "bin/specfact-native-verifier",
    }
    fds = {name: os.open(path, os.O_RDONLY) for name, path in members.items()}
    lease = SimpleNamespace(
        path=capsule,
        identity="b" * 64,
        fds=fds,
        code_identities={name: (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for name, fd in fds.items()},
        evidence={
            "status": "VERIFIED_CACHE_CANDIDATE",
            "native_signing_mode": "adhoc",
            "native_signing_verified": True,
        },
    )
    return lease, {"invocation": invocation, "project": project, "output": output, "temporary": temporary}, fds


def _assert_dead(pid: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    raise AssertionError(f"worker {pid} survived longer than five seconds")


def _assert_no_bootstrap(capsule: Path) -> None:
    observed = subprocess.run(["/bin/ps", "-axo", "command="], check=True, capture_output=True, text=True)
    assert str(capsule / "bin/specfact-native-bootstrap") not in observed.stdout


@pytest.mark.skipif("SPECFACT_NATIVE_EXECUTION_BUILD" not in os.environ, reason="maintainer native proof only")
@pytest.mark.parametrize("_repetition", NATIVE_REPETITIONS)
def test_prebuilt_native_broker_executes_fixed_self_test_plan(tmp_path: Path, _repetition: int) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_EXECUTION_BUILD"]), tmp_path)
    try:
        prepared = request(lease, paths, plan_id="boundary.self-test.v1")
        with native_execution.NativeExecutionSession(native_execution.NativeBrokerTransport(lease)) as session:
            result = session.wait(session.launch(prepared), 5_000)
        assert result.returncode == 37
        assert result.stdout == b"specfact-native-stdout-v1\n"
        assert result.stderr == b"specfact-native-stderr-v1\n"
        assert (paths["output"] / "managed-stdout.bin").stat().st_mode & 0o777 == 0o600
        assert (paths["output"] / "managed-stderr.bin").stat().st_mode & 0o777 == 0o600
        assert (paths["temporary"] / "native-self-test").read_text(encoding="utf-8") == "specfact-native-self-test-v1\n"
    finally:
        for fd in fds.values():
            os.close(fd)


@pytest.mark.skipif("SPECFACT_NATIVE_EXECUTION_BUILD" not in os.environ, reason="maintainer native proof only")
@pytest.mark.parametrize("operation", ["cancel", "timeout", "eof"])
@pytest.mark.parametrize("_repetition", NATIVE_REPETITIONS)
def test_prebuilt_native_broker_reaps_held_worker(tmp_path: Path, operation: str, _repetition: int) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_EXECUTION_BUILD"]), tmp_path)
    (paths["temporary"] / "hold").write_text("1", encoding="utf-8")
    transport = native_execution.NativeBrokerTransport(lease)
    session = native_execution.NativeExecutionSession(transport)
    try:
        handle = session.launch(request(lease, paths, plan_id="boundary.self-test.v1"))
        pid = _worker_pid(paths["temporary"])
        if operation == "cancel":
            session.cancel(handle)
        elif operation == "timeout":
            with pytest.raises(native_execution.NativeExecutionIncompleteError, match="native_broker_error"):
                session.wait(handle, 50)
        else:
            session.close()
        _assert_dead(pid)
    finally:
        session.close()
        for fd in fds.values():
            os.close(fd)


@pytest.mark.skipif("SPECFACT_NATIVE_EXECUTION_BUILD" not in os.environ, reason="maintainer native proof only")
@pytest.mark.parametrize("_repetition", NATIVE_REPETITIONS)
def test_prebuilt_native_broker_cancels_after_postlaunch_file_storm(tmp_path: Path, _repetition: int) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_EXECUTION_BUILD"]), tmp_path)
    (paths["temporary"] / "hold").write_text("1", encoding="utf-8")
    session = native_execution.NativeExecutionSession(native_execution.NativeBrokerTransport(lease))
    try:
        handle = session.launch(request(lease, paths, plan_id="boundary.self-test.v1"))
        pid = _worker_pid(paths["temporary"])
        for index in range(32):
            directory = paths["output"] / f"worker-{index}"
            directory.mkdir()
            for leaf in range(128):
                (directory / f"leaf-{leaf}").touch()
        (paths["output"] / "host-link").symlink_to(tmp_path)
        started = time.monotonic()
        session.cancel(handle)
        _assert_dead(pid)
        assert time.monotonic() - started < 5
    finally:
        session.close()
        for fd in fds.values():
            os.close(fd)


@pytest.mark.skipif("SPECFACT_NATIVE_EXECUTION_BUILD" not in os.environ, reason="maintainer native proof only")
def test_prebuilt_native_broker_rejects_unsafe_tree_at_launch(tmp_path: Path) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_EXECUTION_BUILD"]), tmp_path)
    session = native_execution.NativeExecutionSession(native_execution.NativeBrokerTransport(lease))
    try:
        prepared = request(lease, paths, plan_id="boundary.self-test.v1")
        (paths["output"] / "host-link").symlink_to(tmp_path)
        with pytest.raises(native_execution.NativeExecutionIncompleteError, match="native_broker_error:22"):
            session.launch(prepared)
        assert not (paths["output"] / "managed-stdout.bin").exists()
    finally:
        session.close()
        for fd in fds.values():
            os.close(fd)


@pytest.mark.skipif("SPECFACT_NATIVE_EXECUTION_BUILD" not in os.environ, reason="maintainer native proof only")
def test_prebuilt_native_broker_waits_after_postlaunch_symlink(tmp_path: Path) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_EXECUTION_BUILD"]), tmp_path)
    session = native_execution.NativeExecutionSession(native_execution.NativeBrokerTransport(lease))
    try:
        handle = session.launch(request(lease, paths, plan_id="boundary.self-test.v1"))
        _worker_pid(paths["temporary"])
        (paths["output"] / "host-link").symlink_to(tmp_path)
        result = session.wait(handle, 5_000)
        assert result.returncode == 37
        assert result.stdout == b"specfact-native-stdout-v1\n"
    finally:
        session.close()
        for fd in fds.values():
            os.close(fd)


@pytest.mark.skipif(
    "SPECFACT_NATIVE_STALLED_STARTUP_BUILD" not in os.environ, reason="maintainer signed stall proof only"
)
@pytest.mark.parametrize("_repetition", NATIVE_REPETITIONS)
def test_prebuilt_native_broker_rejects_stalled_signed_bootstrap(tmp_path: Path, _repetition: int) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_STALLED_STARTUP_BUILD"]), tmp_path)
    session = native_execution.NativeExecutionSession(native_execution.NativeBrokerTransport(lease))
    try:
        prepared = request(lease, paths, plan_id="boundary.self-test.v1")
        started = time.monotonic()
        with pytest.raises(native_execution.NativeExecutionIncompleteError, match="native_broker_error:106"):
            session.launch(prepared)
        assert time.monotonic() - started < 6
        _assert_no_bootstrap(lease.path)
    finally:
        session.close()
        for fd in fds.values():
            os.close(fd)


@pytest.mark.skipif(
    "SPECFACT_NATIVE_STALLED_STARTUP_BUILD" not in os.environ, reason="maintainer signed stall proof only"
)
@pytest.mark.parametrize("_repetition", NATIVE_REPETITIONS)
def test_prebuilt_native_broker_observes_controller_eof_during_startup(tmp_path: Path, _repetition: int) -> None:
    lease, paths, fds = _physical_lease(Path(os.environ["SPECFACT_NATIVE_STALLED_STARTUP_BUILD"]), tmp_path)
    transport = native_execution.NativeBrokerTransport(lease)
    started = threading.Event()

    def launch() -> None:
        started.set()
        with contextlib.suppress(OSError, RuntimeError):
            transport.launch(request(lease, paths, plan_id="boundary.self-test.v1"))

    pending = threading.Thread(target=launch, daemon=True)
    try:
        pending.start()
        assert started.wait(1)
        time.sleep(0.1)
        assert pending.is_alive() and transport._process.poll() is None  # pylint: disable=protected-access
        issued = time.monotonic()
        transport._channel.shutdown(socket.SHUT_RDWR)  # pylint: disable=protected-access
        transport._process.wait(timeout=2)  # pylint: disable=protected-access
        assert time.monotonic() - issued < 2
        pending.join(timeout=2)
        assert not pending.is_alive()
        _assert_no_bootstrap(lease.path)
    finally:
        transport.close()
        for fd in fds.values():
            os.close(fd)
