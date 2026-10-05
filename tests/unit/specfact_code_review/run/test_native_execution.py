from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specfact_code_review.run import native_execution


NATIVE_SOURCE = Path("packages/specfact-code-review/native/macos-arm64")
NATIVE_REPETITIONS = range(int(os.environ.get("SPECFACT_NATIVE_EXECUTION_REPETITIONS", "1")))


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.closed = False

    def launch(self, request: native_execution.NativeExecutionRequest) -> int:
        self.calls.append(("launch", request.plan_id))
        return 41

    def wait(self, handle: int, timeout_ms: int) -> native_execution.NativeExecutionResult:
        self.calls.append(("wait", handle, timeout_ms))
        return native_execution.NativeExecutionResult(handle, 0, b"ok", b"")

    def cancel(self, handle: int) -> None:
        self.calls.append(("cancel", handle))

    def close(self) -> None:
        self.calls.append(("close",))
        self.closed = True


@pytest.fixture
def admitted_paths(tmp_path: Path) -> Iterator[tuple[SimpleNamespace, dict[str, Path]]]:
    capsule = tmp_path / "capsule"
    invocation = tmp_path / "invocation"
    project = invocation / "project"
    output = invocation / "output"
    temporary = invocation / "tmp"
    for path in (capsule, invocation, project, output, temporary):
        path.mkdir()
        path.chmod(0o700)
    project.chmod(0o500)
    broker = capsule / "bin" / "specfact-native-broker"
    bootstrap = capsule / "bin" / "specfact-native-bootstrap"
    verifier = capsule / "bin" / "specfact-native-verifier"
    broker.parent.mkdir()
    broker.parent.chmod(0o700)
    broker.write_bytes(b"broker")
    bootstrap.write_bytes(b"bootstrap")
    verifier.write_bytes(b"verifier")
    broker.chmod(0o500)
    bootstrap.chmod(0o500)
    verifier.chmod(0o500)
    fds = {
        name: os.open(path, os.O_RDONLY)
        for name, path in (
            ("bin/specfact-native-broker", broker),
            ("bin/specfact-native-bootstrap", bootstrap),
            ("bin/specfact-native-verifier", verifier),
        )
    }
    lease = SimpleNamespace(
        path=capsule,
        identity="a" * 64,
        fds=fds,
        code_identities={name: (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for name, fd in fds.items()},
        evidence={
            "status": "VERIFIED_CACHE_CANDIDATE",
            "environment_id": "darwin-arm64-cp312",
            "backend": "managed-v1",
            "policy": "deny-v1",
            "native_signing_mode": "adhoc",
            "native_signing_verified": True,
        },
    )
    yield (
        lease,
        {
            "capsule": capsule,
            "invocation": invocation,
            "project": project,
            "output": output,
            "temporary": temporary,
        },
    )
    for fd in fds.values():
        os.close(fd)


def request(lease: object, paths: dict[str, Path], **changes: object) -> native_execution.NativeExecutionRequest:
    arguments: dict[str, object] = {
        "lease": lease,
        "plan_id": "analyzer.ruff.v1",
        "invocation_root": paths["invocation"],
        "project_snapshot": paths["project"],
        "output_root": paths["output"],
        "temporary_root": paths["temporary"],
        "environment": {"LANG": "C.UTF-8", "PYTHONHASHSEED": "0"},
        "descriptor_grants": {"stdin": 0, "stdout": 1, "stderr": 2},
        "timeout_ms": 30_000,
        "budget": native_execution.ResourceBudget(
            address_space_bytes=1 << 30,
            file_size_bytes=16 << 20,
            open_files=128,
            output_bytes=8 << 20,
        ),
    }
    arguments.update(changes)
    return native_execution.prepare_native_execution(**arguments)  # type: ignore[arg-type]


def test_verified_lease_and_bounded_plan_produce_canonical_immutable_request(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]],
) -> None:
    lease, paths = admitted_paths

    prepared = request(lease, paths)

    assert prepared.schema == "specfact-native-execution-v1"
    assert prepared.plan_id == "analyzer.ruff.v1"
    assert prepared.capsule_identity == "a" * 64
    assert prepared.environment == (("LANG", "C.UTF-8"), ("PYTHONHASHSEED", "0"))
    assert prepared.descriptor_grants == (("stderr", 2), ("stdin", 0), ("stdout", 1))
    assert prepared.production_eligible is False
    with pytest.raises(AttributeError):
        prepared.plan_id = "analyzer.mypy.v1"  # type: ignore[misc]


@pytest.mark.parametrize(
    "plan",
    ["acquisition.pip-wheels.v1", "project.pip-install.v1", "project.python-build.v1", "acquisition.uv-project.v1"],
)
def test_project_driven_pip_domains_have_fixed_broker_plans(admitted_paths, plan: str) -> None:
    lease, paths = admitted_paths
    assert request(lease, paths, plan_id=plan).plan_id == plan


def test_unknown_plan_is_actionable_incomplete_without_executable_override(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]],
) -> None:
    lease, paths = admitted_paths

    with pytest.raises(native_execution.NativeExecutionIncompleteError, match="unsupported_native_plan") as caught:
        request(lease, paths, plan_id="/usr/bin/python3")

    assert caught.value.evidence["status"] == "INCOMPLETE"
    assert caught.value.evidence["reason"] == "unsupported_native_plan:/usr/bin/python3"
    assert caught.value.evidence["production_eligible"] is False


def test_plan_table_matches_current_analyzer_and_manager_profile() -> None:
    assert native_execution.SUPPORTED_PLAN_IDS == (
        "boundary.self-test.v1",
        "analyzer.ruff.v1",
        "analyzer.radon.v1",
        "analyzer.semgrep-clean.v1",
        "analyzer.ai-bloat-ast.v1",
        "analyzer.ast-clean-code.v1",
        "analyzer.basedpyright.v1",
        "analyzer.pylint.v1",
        "analyzer.contracts.v1",
        "analyzer.semgrep-bugs.v1",
        "analyzer.targeted-pytest-coverage.v1",
        "tool.ruff.v1",
        "tool.radon.v1",
        "tool.semgrep.v1",
        "tool.basedpyright.v1",
        "tool.pylint.v1",
        "tool.crosshair.v1",
        "tool.pytest.v1",
        "project.pip.v1",
        "project.hatch.v1",
        "project.uv.v1",
        "project.poetry.v1",
        "acquisition.pip-wheels.v1",
        "project.pip-install.v1",
        "project.python-build.v1",
        "project.wheel-inspect.v1",
        "acquisition.uv-project.v1",
    )


def test_native_policy_has_only_measured_sysctl_fingerprint_selectors() -> None:
    profile = (NATIVE_SOURCE / "profile.sb").read_text(encoding="utf-8")
    assert "(allow sysctl-read)" not in profile
    assert profile.count("(sysctl-name ") == 11
    assert '(allow file-read* (subpath (param "OUTPUT")))' in profile
    assert '(allow file-read* (subpath (param "TEMPORARY")))' in profile
    assert '(allow file-read* file-write* (literal "/dev/null"))' in profile
    assert '(subpath "/dev")' not in profile
    for name in (
        "kern.ostype",
        "kern.osrelease",
        "kern.version",
        "kern.hostname",
        "hw.machine",
        "hw.pagesize",
        "hw.pagesize_compat",
        "hw.ncpu",
        "hw.activecpu",
        "hw.logicalcpu",
        "hw.physicalcpu",
    ):
        assert f'(sysctl-name "{name}")' in profile


def test_native_build_outputs_are_ignored_and_wait_does_not_accept_stops() -> None:
    assert (NATIVE_SOURCE / ".gitignore").read_text(encoding="utf-8") == "/build/\n"
    broker = (NATIVE_SOURCE / "broker.c").read_text(encoding="utf-8")
    assert "WNOHANG | WUNTRACED" not in broker
    assert "WIFEXITED(*status) || WIFSIGNALED(*status)" in broker
    assert "stop_worker(worker)" in broker
    assert "raise(SIGSTOP)" in broker
    protocol = (NATIVE_SOURCE / "native_protocol.h").read_text(encoding="utf-8")
    assert "#define SPECFACT_MAX_PLAN 30u" in protocol
    assert "#define SPECFACT_PYTHON_CHILD_PLAN 27u" in protocol
    assert "#define SPECFACT_GIT_CHILD_PLAN 30u" in protocol
    assert "request->plan != SPECFACT_GIT_CHILD_PLAN" in broker
    assert "O_EXCL | O_NOFOLLOW" in broker


def test_broker_marker_wait_has_a_deadline_and_observes_controller_eof() -> None:
    broker = (NATIVE_SOURCE / "broker.c").read_text(encoding="utf-8")
    launch = broker[broker.index("static int launch_worker(") : broker.index("static int wait_bounded(")]
    assert "startup_deadline" in launch
    assert "marker_pipe[0]" in launch
    assert "controller_closed(control)" in launch
    assert "poll(" in launch
    assert "exact_io(marker_pipe[0]" not in launch


def test_broker_lifecycle_dispatch_does_not_scan_worker_writable_trees() -> None:
    broker = (NATIVE_SOURCE / "broker.c").read_text(encoding="utf-8")
    dispatch = broker[broker.index("int main(") :]
    assert dispatch.index("request.opcode == SPECFACT_LAUNCH") < dispatch.index("valid_launch_request(&request)")
    assert dispatch.index("valid_launch_request(&request)") < dispatch.index("request.opcode == SPECFACT_WAIT")
    assert "valid_control_request(&request)" in dispatch
    assert "valid_request(&request)" not in dispatch


def test_bootstrap_uses_fixed_worker_modules_and_all_roots() -> None:
    bootstrap = (NATIVE_SOURCE / "bootstrap.c").read_text(encoding="utf-8")
    assert '"specfact_code_review.run.native_worker"' in bootstrap
    assert '"specfact_code_review.run.native_tool_worker"' in bootstrap
    assert '"specfact_code_review.run.native_project_manager"' in bootstrap
    assert '"--plan-number"' not in bootstrap
    assert '"PYTHONDONTWRITEBYTECODE=1"' in bootstrap
    assert "flags & ~FD_CLOEXEC" in bootstrap
    for field in ("request.project", "request.output", "request.temporary"):
        assert field in bootstrap
    assert '"INVOCATION", request.invocation' in bootstrap


def test_bootstrap_binds_capsule_and_invocation_ancestors_without_bytecode_writes() -> None:
    bootstrap = (NATIVE_SOURCE / "bootstrap.c").read_text(encoding="utf-8")

    assert "append_ancestors(capsule" in bootstrap
    assert "append_ancestors(request.invocation" in bootstrap
    assert "target_length = strlen(target_path)" not in bootstrap
    assert bootstrap.count('"-I", "-B", "-m"') == 7


def test_bootstrap_enters_verified_project_before_worker_replacement() -> None:
    bootstrap = (NATIVE_SOURCE / "bootstrap.c").read_text(encoding="utf-8")

    assert "if (chdir(request.project)) return 73;" in bootstrap
    assert bootstrap.index("if (chdir(request.project)) return 73;") < bootstrap.index("execve(target_path")


def test_production_plans_never_select_fixture_only_exception_holds() -> None:
    control = (NATIVE_SOURCE / "control_mach.inc").read_text(encoding="utf-8")

    assert "MIG_NO_REPLY" not in control
    assert "held_threads" not in control
    assert "item->mode == 4" not in control
    assert "item->mode == 11" not in control
    assert "item->mode == 13" not in control


def test_broker_uses_assembled_fixed_tool_paths() -> None:
    broker = (NATIVE_SOURCE / "broker.c").read_text(encoding="utf-8")
    assert 'posix_spawn_file_actions_addopen(&actions, 0, "/dev/null"' in broker
    assert broker.index("posix_spawn_file_actions_adddup2(&actions, sources[0], 1)") < broker.index(
        "posix_spawn_file_actions_adddup2(&actions, sources[2], 3)"
    )
    assert '"%s/tools/ruff"' in broker
    assert '"%s/tools/semgrep-core"' in broker
    assert '"%s/tools/node"' in broker
    assert '"%s/payload/' not in broker


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"environment": {"DYLD_INSERT_LIBRARIES": "/tmp/payload"}}, "environment key"),
        ({"environment": {"LANG": "x\x00y"}}, "environment value"),
        ({"descriptor_grants": {"control": 9}}, "descriptor grant"),
        ({"timeout_ms": 0}, "timeout"),
        ({"budget": native_execution.ResourceBudget(1, 1, 1, 1)}, "resource budget"),
    ],
)
def test_unbounded_environment_descriptors_and_resources_fail_closed(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]], change: dict[str, object], message: str
) -> None:
    lease, paths = admitted_paths

    with pytest.raises(ValueError, match=message):
        request(lease, paths, **change)


def test_path_escape_and_symlink_grants_fail_closed(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]], tmp_path: Path
) -> None:
    lease, paths = admitted_paths
    outside = tmp_path / "outside"
    outside.mkdir()
    outside.chmod(0o700)
    link = paths["invocation"] / "linked-output"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="below invocation root"):
        request(lease, paths, output_root=outside)
    with pytest.raises(ValueError, match="symlink"):
        request(lease, paths, output_root=link)


def test_unverified_or_closed_lease_fails_before_transport(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]],
) -> None:
    lease, paths = admitted_paths
    lease.evidence["native_signing_verified"] = False
    with pytest.raises(ValueError, match="verified native signing"):
        request(lease, paths)
    lease.evidence["native_signing_verified"] = True
    lease.fds.clear()
    with pytest.raises(ValueError, match="live broker/bootstrap descriptors"):
        request(lease, paths)


def test_session_exposes_only_launch_wait_cancel_and_closes_transport(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]],
) -> None:
    lease, paths = admitted_paths
    transport = FakeTransport()
    prepared = request(lease, paths)

    with native_execution.NativeExecutionSession(transport) as session:
        handle = session.launch(prepared)
        result = session.wait(handle, 500)
        handle = session.launch(prepared)
        session.cancel(handle)

    assert result == native_execution.NativeExecutionResult(41, 0, b"ok", b"")
    assert transport.calls == [
        ("launch", "analyzer.ruff.v1"),
        ("wait", 41, 500),
        ("launch", "analyzer.ruff.v1"),
        ("cancel", 41),
        ("close",),
    ]
    with pytest.raises(RuntimeError, match="closed"):
        session.launch(prepared)


def test_session_rejects_foreign_handles_and_duplicate_wait(
    admitted_paths: tuple[SimpleNamespace, dict[str, Path]],
) -> None:
    lease, paths = admitted_paths
    transport = FakeTransport()
    prepared = request(lease, paths)
    session = native_execution.NativeExecutionSession(transport)

    handle = session.launch(prepared)
    with pytest.raises(ValueError, match="owned active handle"):
        session.wait(99, 500)
    session.wait(handle, 500)
    with pytest.raises(ValueError, match="owned active handle"):
        session.cancel(handle)
    session.close()


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


def _worker_pid(temporary: Path) -> int:
    marker = temporary / "native-self-test.pid"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if marker.is_file():
            return int(marker.read_text(encoding="utf-8"))
        time.sleep(0.01)
    raise AssertionError("worker PID marker was not written")


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
