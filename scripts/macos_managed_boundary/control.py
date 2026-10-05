"""Bounded signed native control fixtures; no customer execution or admission."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import platform
import plistlib
import secrets
import select
import socket
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from contextvars import ContextVar
from functools import partial
from pathlib import Path
from typing import Any, NamedTuple


SOURCE, REQUEST = Path(__file__).resolve().parent, struct.Struct("!BBHQII32s")
_CASE_NAMES = {
    "lifecycle": (
        "cancel cancel-held-stop timeout signal eof-pretrace eof-trace-stopped eof-running eof-wait eof-partial "
        "partial-timeout broker-kill cli-kill-wait isolation"
    ),
    "failure": (
        "unknown bootstrap-observe-caller bootstrap-authority bootstrap-register bootstrap-socket "
        "marker-broker marker-bootstrap-identity marker-trace marker-output marker-exec observe-worker observe-removal isolation-peer-authority "
        "isolation-extra-connection cleanup"
    ),
    "protocol": (
        "output-status version opcode reserved foreign-handle fixture-mode host-pid signal-selector "
        "timeout-bound unused-field fragmentation worker-limit oversize undersize authentication peer-pid "
        "peer-pidversion term-ignored runtime-trap"
    ),
}
REQUEST_FAILURE_PHASES = dict(
    enumerate(("request-authenticate", "request-launch", "request-wait", "request-signal", "request-cancel"))
)
FAILURE_PHASES = frozenset(REQUEST_FAILURE_PHASES.values()) | frozenset(_CASE_NAMES["failure"].split())
SOCKET_FAILURE_STATES = frozenset(
    (
        "socket_missing",
        "socket_mode_pending",
        "private_after_deadline",
        "directory_invalid",
        "socket_type_invalid",
        "socket_owner_invalid",
    )
)
_ACTIVE_OPERATION: ContextVar[tuple[object | None, str]] = ContextVar("control_operation", default=(None, "unknown"))


def _activate_operation(owner: Invocation | None, phase: str) -> None:
    """Bind a trusted operation before execution and keep it through validation."""
    phase = phase if phase in FAILURE_PHASES else "unknown"
    if owner is not None:
        owner.phase = phase
    _ACTIVE_OPERATION.set((owner, phase))


def _stamp_failure(error: BaseException) -> tuple[object | None, str]:
    """Snapshot once before any nested context emits diagnostics or cleans up."""
    return error.__dict__.setdefault("_control_failure_origin", _ACTIVE_OPERATION.get())


def startup_module(helper: str = "startup") -> Any:
    """Load a fixed internal sibling helper without changing import paths."""
    spec = importlib.util.spec_from_file_location(f"control_{helper}_helpers", SOURCE / f"{helper}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("control helpers unavailable")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


STARTUP = startup_module()
SOCKET = startup_module("control_socket")
STATE = startup_module("control_state")
BUILD = startup_module("control_build")
MACH = startup_module("control_mach_build")
EXEC = startup_module("control_exec")
ADMISSION = startup_module("control_admission")
EXEC_LIFECYCLE_CASES, EXEC_PROTOCOL_CASES = EXEC.LIFECYCLE_CASES, EXEC.PROTOCOL_CASES
LIFECYCLE_CASES = (*_CASE_NAMES["lifecycle"].split(), *EXEC_LIFECYCLE_CASES, *ADMISSION.LIFECYCLE_CASES)
PROTOCOL_CASES = (*_CASE_NAMES["protocol"].split(), *EXEC_PROTOCOL_CASES, *ADMISSION.PROTOCOL_CASES)


class FrameFields(NamedTuple):
    """Fixed request fields, including explicit malformed-frame test selectors."""

    handle: int = 0
    argument: int = 0
    timeout_ms: int = 0
    version: int = 1
    reserved: int = 0


class PeerIdentity(NamedTuple):
    """Caller token selection for normal and negative authentication fixtures."""

    pid: int | None = None
    stale_pidversion: bool = False


DEFAULT_FRAME, DEFAULT_PEER = FrameFields(), PeerIdentity()


def frame(capability: bytes, opcode: int, fields: FrameFields = DEFAULT_FRAME) -> bytes:
    """Encode only bounded fixture controls; no path, grants or PID fields."""
    if len(capability) != 32:
        raise ValueError("capability must be exactly 32 bytes")
    payload = REQUEST.pack(
        fields.version, opcode, fields.reserved, fields.handle, fields.argument, fields.timeout_ms, capability
    )
    return struct.pack("!I", len(payload)) + payload


def read_exact(stream: socket.socket, count: int) -> bytes:
    """EOF or incomplete bounded replies fail rather than becoming success."""
    data = bytearray()
    while len(data) < count:
        chunk = stream.recv(count - len(data))
        if not chunk:
            raise EOFError("control connection closed")
        data.extend(chunk)
    return bytes(data)


def response(stream: socket.socket) -> dict[str, Any]:
    """Bound decoding before allocation; require the agreed response version."""
    size = struct.unpack("!I", read_exact(stream, 4))[0]
    if not 1 <= size <= 2048:
        raise ValueError("oversize control reply")
    result = json.loads(read_exact(stream, size))
    if not isinstance(result, dict) or result.get("version") != 1 or not isinstance(result.get("ok"), bool):
        raise ValueError("invalid control reply")
    return result


class Client:
    """One invocation's private authenticated control connection."""

    def __init__(self, path: Path, capability: bytes, *, owner: Invocation | None = None):
        self.owner = owner
        self._activate_request(0)
        self.capability = capability
        self.history: list[dict[str, Any]] = []
        self.stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.stream.settimeout(7)
        try:
            self.stream.connect(str(path))
            require(self.request(0).get("state") == "authenticated", "authentication failed")
        except BaseException:
            self.stream.close()
            raise

    def _activate_request(self, opcode: int) -> None:
        _activate_operation(getattr(self, "owner", None), REQUEST_FAILURE_PHASES.get(opcode, "unknown"))

    def record_request(self, opcode: int, **fields: int) -> dict[str, Any]:
        """Retain a bounded attempt before any request bytes are sent."""
        self.history = [*self.history[-63:], {"opcode": opcode, "fields": fields, "started": time.monotonic()}]
        return self.history[-1]

    def request(self, opcode: int, **fields: int) -> dict[str, Any]:
        """Send one bounded frame and receive its explicit result."""
        self._activate_request(opcode)
        record = self.record_request(opcode, **fields)
        try:
            self.stream.sendall(frame(self.capability, opcode, FrameFields(**fields)))
            record["response"] = response(self.stream)
            return record["response"]
        except Exception as error:
            record["failure"] = f"{type(error).__name__}: {error}"[:1024]
            raise

    def launch(self, mode: int = 2, timeout_ms: int = 5000) -> dict[str, Any]:
        self._activate_request(1)
        started = time.monotonic()
        result = self.request(1, argument=mode, timeout_ms=timeout_ms)
        require(result.get("ok") is True and result.get("state") == "launched", f"launch rejected: {result}")
        require(isinstance(result.get("deadline_ns"), int), "native launch deadline missing")
        owner = getattr(self, "owner", None)
        if owner is not None:
            marker = owner.wait_event("bootstrap_identity", result["pid"])
            _validate_bootstrap_identity(marker, result["pid"])
            result["bootstrap_identity"] = marker
        result["launch_started"] = started  # Mach/Python elapsed clock, not the native epoch.
        return result

    def close(self) -> None:
        self.stream.close()


def require(condition: bool, message: str) -> None:
    """Assertions used as proof gates also work under python -O."""
    if not condition:
        raise RuntimeError(message)


def _validate_bootstrap_identity(marker: object, pid: int) -> None:
    """Require exact suspended-process verification before worker execution."""
    require(isinstance(marker, dict), "bootstrap identity marker missing")
    require(marker.get("bootstrap_identity") == pid, "foreign bootstrap identity marker")
    require(marker.get("suspended") is True, "bootstrap was not suspended during identity verification")
    require(marker.get("output_empty") is True, "bootstrap produced output before identity verification")


def job_config(label: str, broker: Path, directory: Path) -> dict[str, Any]:
    """One ephemeral socket-activated job; no installation or restart."""
    if len(os.fsencode(directory / "control.sock")) >= 104:
        raise ValueError("Darwin Unix socket path exceeds public sockaddr_un limit")
    return {
        "Label": label,
        "ProgramArguments": [str(broker), str(directory / "authority")],
        "RunAtLoad": False,
        "KeepAlive": False,
        "LaunchOnlyOnce": True,
        "AbandonProcessGroup": False,
        "ExitTimeOut": 1,
        "Sockets": {
            "control": {
                "SockPathName": str(directory / "control.sock"),
                "SockPathMode": 0o600,
                "SockPathOwner": os.getuid(),
            }
        },
        "StandardOutPath": str(directory / "events"),
        "StandardErrorPath": str(directory / "errors"),
        "WorkingDirectory": str(directory),
        "EnvironmentVariables": {"PATH": "/usr/bin:/bin", "LANG": "C"},
    }


def _event_from_file(path: Path, field: str, pid: int | None) -> dict[str, Any] | None:
    """Match a complete native marker; malformed JSON lines remain ignorable."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if field in item and (pid is None or item[field] == pid):
            return item
    return None


class Invocation:
    """Own private fixture inputs and post-measurement token-safe cleanup."""

    phase: str

    def __init__(self, broker: Path, observer: Path, root: Path, *, peer: PeerIdentity = DEFAULT_PEER):
        self.observer, self.broker = observer, broker
        self.case = "protocol"
        self.directory = root / uuid.uuid4().hex[:12]
        self.identities: list[dict[str, Any]] = []
        self.client: Client | None = None
        self.service = f"gui/{os.getuid()}/io.specfact.control.{uuid.uuid4().hex}"
        self.registered = False
        _activate_operation(self, "bootstrap-authority")
        try:
            self.directory.mkdir(mode=0o700)
            self.capability = secrets.token_bytes(32)
            _activate_operation(self, "bootstrap-observe-caller")
            caller = STARTUP.observe(observer, peer.pid or os.getpid())
            require(caller is not None, "caller token unavailable")
            _activate_operation(self, "bootstrap-authority")
            authority = self.directory / "authority"
            token = list(caller["audit_token"])
            if peer.stale_pidversion:
                token[7] = (token[7] + 1) % 2**32  # authentication-only negative control
            authority.write_bytes(self.capability + struct.pack("=8I", *token))
            authority.chmod(0o600)
            plist = self.directory / "job.plist"
            plist.write_bytes(plistlib.dumps(job_config(self.service.rsplit("/", 1)[1], broker, self.directory)))
            plist.chmod(0o600)
            # Registration can succeed even when launchctl subsequently times out.
            self.registered = True
            self.registration_started = time.monotonic()
            _activate_operation(self, "bootstrap-register")
            STARTUP.command(["/bin/launchctl", "bootstrap", self.service.rsplit("/", 1)[0], str(plist)])
            _activate_operation(self, "bootstrap-socket")
            SOCKET.wait_socket_ready(self.directory / "control.sock")
        except BaseException as error:
            self._finish_failed_invocation(error)
            raise

    def connect(self) -> Client:
        _activate_operation(self, "request-authenticate")
        self.client = Client(self.directory / "control.sock", self.capability, owner=self)
        self.capture_broker()
        return self.client

    def capture_broker(self) -> None:
        event = self.wait_event("broker")
        identity = STARTUP.observe(self.observer, event["broker"])
        require(identity is not None, "broker token unavailable")
        self.identities.append(identity)

    def wait_event(self, field: str, pid: int | None = None) -> dict[str, Any]:
        """Read-only observation of fixture markers; never cleanup enforcement."""
        _activate_operation(
            self,
            {
                "broker": "marker-broker",
                "bootstrap_identity": "marker-bootstrap-identity",
                "trace": "marker-trace",
                "output": "marker-output",
                "exec": "marker-exec",
            }.get(field, "unknown"),
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            item = _event_from_file(self.directory / "events", field, pid)
            if item is not None:
                return item
            time.sleep(0.005)
        raise RuntimeError(f"missing native {field} marker; errors={self.errors()}")

    def errors(self) -> str:
        path = self.directory / "errors"
        return path.read_text()[-1000:] if path.exists() else ""

    def capture_worker(self, launched: dict[str, Any], mode: int = 2) -> dict[str, Any]:
        """Validate the original kernel identity before injecting lifecycle faults."""
        pid = launched["pid"]
        bootstrap = launched.get("bootstrap_identity") or self.wait_event("bootstrap_identity", pid)
        _validate_bootstrap_identity(bootstrap, pid)
        if mode in (10, 11):
            marker = self.wait_event("exec", pid)
            require(marker.get("held") is (mode == 11), "unexpected replacement hold")
        elif mode in (4, 13):
            self.wait_event("trace", pid)
        elif mode != 3:
            self.wait_event("output", pid)
        _activate_operation(self, "observe-worker")
        identity = STARTUP.observe(self.observer, pid)
        if mode == 10:
            deadline = time.monotonic() + 3
            while identity is not None and identity["pgid"] != pid and time.monotonic() < deadline:
                time.sleep(0.005)
                identity = STARTUP.observe(self.observer, pid)
        if identity is None:
            raise RuntimeError("worker vanished before capture")
        self.identities.append(identity)
        require(identity["ppid"] == self.identities[0]["pid"], "worker not direct broker child")
        require(bool(identity["flags"] & 2) == (mode != 3), "unexpected tracing flag")
        if mode in (3, 4, 11, 13):
            require(identity["pgid"] == self.identities[0]["pgid"], "trusted startup left launchd group")
        elif mode in (2, 10):
            require(identity["pgid"] == pid, "traced hold fixture did not leave group")
        return identity

    def cleanup(self) -> None:
        """Post-measurement cleanup cannot turn a failed survivor check green."""
        _activate_operation(self, "cleanup")
        if self.client is not None:
            self.client.close()
        if self.registered:
            STARTUP.remove_job(self.observer, self.identities, self.service)
            self.registered = False

    def __enter__(self) -> Invocation:
        return self

    def retain_failure(self, error: BaseException) -> Path:
        """Snapshot before cleanup; capability/authority bytes are never exported."""
        owner, phase = _stamp_failure(error)
        phase = phase if phase in FAILURE_PHASES else "unknown"
        origin = owner is self
        record = {
            "case": self.case,
            "failure_phase": phase,
            "failure_origin": origin,
            "failure": f"{type(error).__name__}: {error}"[:1024],
            "service": self.service,
            "events": _bounded_text(self.directory / "events"),
            "errors": _bounded_text(self.directory / "errors"),
            "identities": self.identities,
            "observed": [_failure_identity(self.observer, item) for item in self.identities],
            "requests": self.client.history if self.client is not None else [],
            "broker_sha256": hashlib.sha256(self.broker.read_bytes()).hexdigest() if self.broker.exists() else None,
        }
        path = _write_diagnostic(record)
        marker = {"failed_case": self.case, "failure_phase": phase, "failure_origin": origin, "diagnostic": str(path)}
        state = STATE.last_worker_state(record["events"], record["requests"], phase) if origin else {}
        if state:
            marker["last_worker_state"] = state
        socket_state = error.__dict__.get("_native_socket_state")
        if (
            origin
            and phase == "bootstrap-socket"
            and type(socket_state) is str  # pylint: disable=unidiomatic-typecheck  # Reject string subclasses.
            and socket_state in SOCKET_FAILURE_STATES
        ):
            marker["bootstrap_socket_state"] = socket_state
        _emit_json(marker)
        return path

    def _finish_failed_invocation(self, error: BaseException, *, cleanup_attempted: bool = False) -> None:
        """Report secondary failures without replacing the original proof failure."""
        _stamp_failure(error)
        try:
            self.retain_failure(error)
        except BaseException as diagnostic_error:
            error.add_note(f"Failure diagnostic unavailable: {type(diagnostic_error).__name__}")
            raise error from None
        finally:
            if not cleanup_attempted:
                try:
                    self.cleanup()
                except BaseException as cleanup_error:
                    error.add_note(f"Fixture cleanup failed: {type(cleanup_error).__name__}")
                    raise error from None

    def __exit__(self, _kind: Any, error: BaseException | None, _traceback: Any) -> None:
        if error is None:
            try:
                self.cleanup()
            except BaseException as cleanup_error:
                self._finish_failed_invocation(cleanup_error, cleanup_attempted=True)
                raise
        else:
            self._finish_failed_invocation(error)


def _bounded_text(path: Path) -> str:
    """Capture bounded native event tails without reading authority files."""
    if not path.exists():
        return ""
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 8192))
        return stream.read(8192).decode("utf-8", errors="replace")


def _failure_identity(observer: Path, identity: dict[str, Any]) -> dict[str, Any] | None:
    """Retain observation errors distinctly from actual process absence."""
    try:
        return STARTUP.observe(observer, identity["pid"])
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as error:
        return {"observation_error": f"{type(error).__name__}: {error}"[:1024]}


def _write_diagnostic(record: dict[str, Any]) -> Path:
    """Use a private persistent receipt, bounded to 256 KiB, outside build tempfiles."""
    payload = json.dumps(record, indent=2)
    require(len(payload.encode()) <= 262144, "failure evidence exceeds bounded receipt limit")
    directory = "/private/tmp" if Path("/private/tmp").is_dir() else tempfile.gettempdir()
    fd, name = tempfile.mkstemp(prefix="specfact-control-failure-", suffix=".json", dir=directory)
    with os.fdopen(fd, "w") as stream:
        stream.write(payload + "\n")
    return Path(name)


def cleanup_deadline(launched: dict[str, Any]) -> int:
    """Retain the launch timer; stop 250 ms before it can compete with cleanup."""
    deadline = launched["deadline_ns"] - 250_000_000
    remaining = deadline - time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    require(remaining >= 1_500_000_000, "competing worker timeout leaves inadequate cleanup proof horizon")
    return deadline


def _within_window(elapsed_deadline: float, native_deadline_ns: int | None) -> bool:
    """Check each clock in its own epoch, with strict native deadline exclusion."""
    if time.monotonic() >= elapsed_deadline:
        return False
    return native_deadline_ns is None or time.clock_gettime_ns(time.CLOCK_MONOTONIC) < native_deadline_ns


def _observe_job_removed(service: str, elapsed_deadline: float, native_deadline_ns: int | None) -> bool:
    """Bound automatic job-removal observation by both clocks, never enforce cleanup."""
    while _within_window(elapsed_deadline, native_deadline_ns):
        if STARTUP.job_absent(service):
            return _within_window(elapsed_deadline, native_deadline_ns)
        time.sleep(0.005)
    return False


def observe_absence(
    invocation: Invocation,
    identity: dict[str, Any],
    started: float,
    *,
    job: bool,
    native_deadline_ns: int | None = None,
) -> dict[str, Any]:
    """Independent removal proof, excluding native timer death and any rescue signal."""
    _activate_operation(invocation, "observe-removal")
    elapsed_deadline = started + 5
    while _within_window(elapsed_deadline, native_deadline_ns):
        if not STARTUP.alive(invocation.observer, identity):
            break
        time.sleep(0.005)
    absent = not STARTUP.alive(invocation.observer, identity)
    removed = _observe_job_removed(invocation.service, elapsed_deadline, native_deadline_ns) if job else True
    elapsed = time.monotonic() - started
    require(
        absent and removed and _within_window(elapsed_deadline, native_deadline_ns),
        f"lifecycle survivor/job failure after {elapsed:.4f}s",
    )
    return {
        "passed": True,
        "worker_identity": identity,
        "observation_seconds": round(elapsed, 6),
        "job_removed": removed if job else None,
        "native_proof_deadline_ns": native_deadline_ns,
    }


def _prepare_wait(client: Client, handle: int, case: str) -> None:
    """Submit the full pending wait or a deliberately incomplete frame."""
    if case not in ("eof-wait", "eof-partial", "partial-timeout"):
        return
    _activate_operation(getattr(client, "owner", None), "request-wait")
    if case == "eof-wait":
        client.record_request(2, handle=handle)
    packet = frame(client.capability, 2, FrameFields(handle=handle))
    client.stream.sendall(packet if case == "eof-wait" else packet[:13])
    if case == "eof-wait":
        require(not select.select([client.stream], [], [], 0.03)[0], "wait did not defer")


def _finish_worker(client: Client, handle: int, case: str) -> dict[str, Any]:
    """Validate signal/cancel/timeout status independently of survivor observation."""
    if case in ("cancel", "cancel-held-stop", "exec-cancel", "exec-cancel-held"):
        require(client.request(4, handle=handle)["ok"], "cancel rejected")
    elif case == "signal":
        require(client.request(3, handle=handle, argument=9)["ok"], "signal rejected")
    status = client.request(2, handle=handle)
    require(
        status["state"] == "exited"
        and status["signal"] == 9
        and status["reason"] == ("cancel" if "cancel" in case else case),
        f"unexpected status {status}",
    )
    if case == "exec-cancel":
        require("target-denials-ok" in status["output"], "replacement confinement probes missing")
    elif case == "exec-cancel-held":
        require("target-initializer-ns=" not in status["output"], "held replacement initialized")
    elif case != "cancel-held-stop":
        require("control-denials-ok" in status["output"], "native deny-default probes missing")
    return status


def _trigger_lifecycle(
    invocation: Invocation, client: Client, handle: int, case: str
) -> tuple[float, dict[str, Any] | None]:
    """Keep fault issuance and its measurement start together."""
    started = time.monotonic()
    if case.startswith("eof-") or case in ("exec-eof", "exec-eof-held"):
        client.close()
        return started, None
    if case in ("broker-kill", "exec-broker-kill", "exec-broker-kill-held"):
        issued = STARTUP.signal_fixture(invocation.observer, invocation.identities[0])
        require(issued is not None, "broker exited before injection")
        return issued[0], None
    if case == "partial-timeout":
        return started, None  # Native assembly deadline; the socket remains open.
    return started, _finish_worker(client, handle, case)


def lifecycle_trial(broker: Path, observer: Path, root: Path, case: str) -> dict[str, Any]:
    """Use kernel identity proof plus returned status for each added lifecycle."""
    if case == "exec-identity-swap":
        return identity_swap_trial(broker, observer, root)
    if case == "cli-kill-wait":
        return cli_death_trial(broker, observer, root)
    if case == "isolation":
        return isolation_trial(broker, observer, root)
    mode = {"eof-pretrace": 3, "eof-trace-stopped": 4, "cancel-held-stop": 4}.get(case, 2)
    if case in EXEC_LIFECYCLE_CASES:
        mode = 11 if case.endswith("-held") else 10
    timeout = 500 if case == "timeout" else 5000
    with Invocation(broker, observer, root) as invocation:
        invocation.case = case
        client = invocation.connect()
        launched = client.launch(mode, timeout)
        identity = invocation.capture_worker(launched, mode)
        _prepare_wait(client, launched["handle"], case)
        job = case.startswith(("eof-", "exec-eof", "exec-broker-kill")) or case in ("partial-timeout", "broker-kill")
        deadline = cleanup_deadline(launched) if job else None
        started, status = _trigger_lifecycle(invocation, client, launched["handle"], case)
        result = observe_absence(invocation, identity, started, job=job, native_deadline_ns=deadline)
        marker = (
            _event_from_file(invocation.directory / "events", "exec", launched["pid"])
            if case in EXEC_LIFECYCLE_CASES
            else None
        )
        if case in EXEC_LIFECYCLE_CASES:
            EXEC.verify_lifecycle_marker(marker, identity, case, require)
        return {
            "case": case,
            **result,
            "status": status,
            "image_stop": marker,
            "bootstrap_identity": launched["bootstrap_identity"],
        }


def isolation_trial(broker: Path, observer: Path, root: Path) -> dict[str, Any]:
    """Simultaneous jobs cannot exchange authority or affect each other's workers."""
    with Invocation(broker, observer, root) as first, Invocation(broker, observer, root) as second:
        first.case, second.case = "isolation-left", "isolation-right"
        left, right = first.connect(), second.connect()
        a, b = left.launch(), right.launch()
        one, two = first.capture_worker(a), second.capture_worker(b)
        require(right.request(4, handle=a["handle"]).get("error") == "handle", "foreign handle accepted")
        _activate_operation(second, "isolation-peer-authority")
        right.stream.sendall(frame(left.capability, 4, FrameFields(handle=b["handle"])))
        require(response(right.stream).get("error") == "capability", "foreign capability accepted")
        _activate_operation(first, "isolation-extra-connection")
        extra = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        extra.settimeout(2)
        try:
            extra.connect(str(first.directory / "control.sock"))
            require(extra.recv(1) == b"", "second connection replaced owner")
        finally:
            extra.close()
        _activate_operation(first, "observe-removal")
        started = time.monotonic()
        deadline = cleanup_deadline(a)
        left.close()
        result = observe_absence(first, one, started, job=True, native_deadline_ns=deadline)
        _activate_operation(second, "observe-worker")
        require(STARTUP.alive(observer, two), "other invocation killed by peer EOF")
        require(right.request(4, handle=b["handle"])["ok"], "isolated cancellation failed")
        status = right.request(2, handle=b["handle"])
        require(status["signal"] == 9 and status["reason"] == "cancel", "isolated status failed")
        observe_absence(second, two, time.monotonic(), job=False)
        return {"case": "isolation", **result, "isolated_worker_identity": two}


def child_line(process: subprocess.Popen[str]) -> dict[str, Any]:
    """Bound external CLI synchronization without blocking indefinitely."""
    if process.stdout is None:
        raise RuntimeError("missing fixture stdout")
    data = bytearray()
    deadline = time.monotonic() + 5
    while len(data) <= 2048:
        remaining = deadline - time.monotonic()
        require(
            remaining > 0 and bool(select.select([process.stdout], [], [], max(0, remaining))[0]),
            "fixture CLI handshake timeout",
        )
        byte = os.read(process.stdout.fileno(), 1)
        require(bool(byte), "fixture CLI closed early")
        if byte == b"\n":
            return json.loads(data)
        data.extend(byte)
    raise RuntimeError("oversize fixture CLI handshake")


def _emit_json(value: dict[str, Any]) -> None:
    """Keep JSON protocol records on stdout, flushed before the next handshake."""
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()


def fixture_client() -> int:
    """Separate benign CLI process, killed by token during a native pending wait."""
    _emit_json({"client": os.getpid()})
    config = json.loads(input())
    client = Client(Path(config["socket"]), bytes.fromhex(config["capability"]))
    try:
        launched = client.launch()
        _emit_json(launched)
        client.stream.sendall(frame(client.capability, 2, FrameFields(handle=launched["handle"])))
        _emit_json({"waiting": True})
        response(client.stream)
        return 2
    finally:
        client.close()


def _measure_cli_wait(
    process: subprocess.Popen[str], invocation: Invocation, client_identity: dict[str, Any]
) -> dict[str, Any]:
    """Connect the captured caller, kill it during wait, then only observe workers."""
    if process.stdin is None:
        raise RuntimeError("CLI stdin unavailable")
    process.stdin.write(
        json.dumps({"socket": str(invocation.directory / "control.sock"), "capability": invocation.capability.hex()})
        + "\n"
    )
    process.stdin.flush()
    launched = child_line(process)
    require(child_line(process).get("waiting") is True, "CLI did not enter wait")
    invocation.capture_broker()
    identity = invocation.capture_worker(launched)
    deadline = cleanup_deadline(launched)
    issued = STARTUP.signal_fixture(invocation.observer, client_identity)
    require(issued is not None, "CLI exited before injection")
    result = observe_absence(invocation, identity, issued[0], job=True, native_deadline_ns=deadline)
    require(process.wait(timeout=5) == -9, "CLI death not injected SIGKILL")
    return {"case": "cli-kill-wait", **result, "cli_identity": client_identity}


def _stop_cli(process: subprocess.Popen[str], observer: Path, identity: dict[str, Any] | None) -> None:
    """Reap before leaving Popen's context, even after a failed handshake."""
    if process.poll() is not None:
        return
    if identity is None:
        process.kill()  # Still-unreaped Popen child ownership, never a discovered PID.
    else:
        STARTUP.signal_fixture(observer, identity)
    process.wait(timeout=5)


def cli_death_trial(broker: Path, observer: Path, root: Path) -> dict[str, Any]:
    """Actual CLI SIGKILL closes the pending wait socket; supervisor only observes."""
    with subprocess.Popen(
        [sys.executable, str(SOURCE / "control.py"), "--fixture-client"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        identity = None
        try:
            child = child_line(process)
            identity = STARTUP.observe(observer, child["client"])
            require(identity is not None, "CLI identity unavailable")
            with Invocation(broker, observer, root, peer=PeerIdentity(child["client"])) as invocation:
                invocation.case = "cli-kill-wait"
                return _measure_cli_wait(process, invocation, identity)
        finally:
            _stop_cli(process, observer, identity)


def runtime_trap_trial(broker: Path, observer: Path, root: Path) -> dict[str, Any]:
    """A kernel-traced runtime trap must remain an actual terminating signal."""
    with Invocation(broker, observer, root) as invocation:
        client = invocation.connect()
        launched = client.launch(5)
        status = client.request(2, handle=launched["handle"])
        require(status["signal"] == 5 and status["exit"] == -1, f"runtime trap suppressed: {status}")
        require("control-denials-ok" in status["output"], "confinement probes missing")
        require("runtime-trap-was-suppressed" not in status["output"], "worker resumed after runtime trap")
        return {"case": "runtime-trap", "passed": True, "status": status}


verify_exec_status = partial(EXEC.verify_status, require=require)


exec_trials = partial(EXEC.trials, tools=EXEC.ExecTools(Invocation, require, _event_from_file))

exception_port_trial = partial(
    ADMISSION.exception_port_trial,
    tools=ADMISSION.AdmissionTools(Invocation, require, observe_absence, cleanup_deadline, STARTUP.command, BUILD),
)

identity_swap_trial = partial(
    ADMISSION.identity_swap_trial,
    tools=ADMISSION.AdmissionTools(Invocation, require, observe_absence, cleanup_deadline, STARTUP.command, BUILD),
)

bootstrap_identity_trial = partial(
    ADMISSION.bootstrap_identity_trial,
    tools=ADMISSION.AdmissionTools(Invocation, require, observe_absence, cleanup_deadline, STARTUP.command, BUILD),
)


def _output_protocol_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """Prove native output, rejection, fragmentation and retained handle limits."""
    trials: list[dict[str, Any]] = []
    with Invocation(broker, observer, root) as invocation:
        client = invocation.connect()
        launched = client.launch(1)
        completed = client.request(2, handle=launched["handle"])
        require(
            completed["exit"] == 37
            and completed["signal"] == 0
            and completed["traced"]
            and "control-fixture-output" in completed["output"]
            and "control-denials-ok" in completed["output"],
            f"positive fixture failed: {completed}",
        )
        trials.append({"case": "output-status", "passed": True, "status": completed})
        for name, opcode, fields, error in (
            ("version", 1, {"version": 2}, "version"),
            ("opcode", 255, {}, "opcode"),
            ("reserved", 1, {"reserved": 1}, "reserved"),
            ("foreign-handle", 2, {"handle": 123}, "handle"),
            ("fixture-mode", 1, {"argument": 99, "timeout_ms": 50}, "arguments"),
            ("host-pid", 3, {"handle": os.getpid(), "argument": 9}, "handle"),
            ("signal-selector", 3, {"handle": launched["handle"], "argument": 19}, "arguments"),
            ("timeout-bound", 1, {"argument": 2, "timeout_ms": 5001}, "arguments"),
            ("unused-field", 2, {"handle": launched["handle"], "timeout_ms": 1}, "arguments"),
        ):
            result = client.request(opcode, **fields)
            require(result.get("ok") is False and result.get("error") == error, f"{name} was not rejected: {result}")
            trials.append({"case": name, "passed": True, "response": result})
        _activate_operation(getattr(client, "owner", None), "request-wait")
        packet = frame(client.capability, 2, FrameFields(handle=launched["handle"]))
        for fragment in (packet[:1], packet[1:4], packet[4:15], packet[15:]):
            client.stream.sendall(fragment)
        require(response(client.stream)["exit"] == 37, "fragmented frame failed")
        trials.append({"case": "fragmentation", "passed": True})
        for _ in range(7):
            worker = client.launch(1)
            require(client.request(2, handle=worker["handle"])["exit"] == 37, "bounded launch failed")
        require(client.request(1, argument=1, timeout_ms=1000).get("error") == "worker-limit", "worker limit missing")
        trials.append({"case": "worker-limit", "passed": True})
    return trials


def _frame_size_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """Oversized and undersized frames must terminate the owning broker."""
    trials: list[dict[str, Any]] = []
    for name, header in (("oversize", 2**32 - 1), ("undersize", 51)):
        with Invocation(broker, observer, root) as invocation:
            client = invocation.connect()
            launched = client.launch()
            identity = invocation.capture_worker(launched)
            started = time.monotonic()
            client.stream.sendall(struct.pack("!I", header))
            result = observe_absence(invocation, identity, started, job=True)
            trials.append({"case": name, **result})
    return trials


def _authentication_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """Reject unauthenticated launch and an incorrect private capability."""
    trials: list[dict[str, Any]] = []
    with Invocation(broker, observer, root) as invocation:
        _activate_operation(invocation, "request-authenticate")
        stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stream.settimeout(2)
        try:
            stream.connect(str(invocation.directory / "control.sock"))
            _activate_operation(invocation, "request-launch")
            stream.sendall(frame(invocation.capability, 1, FrameFields(argument=2, timeout_ms=1000)))
            require(response(stream).get("error") == "authentication", "unauthenticated launch accepted")
            _activate_operation(invocation, "request-authenticate")
            stream.sendall(frame(b"z" * 32, 0))
            require(response(stream).get("error") == "capability", "bad capability accepted")
            invocation.capture_broker()
        finally:
            stream.close()
        require(STARTUP.wait_job_absent(invocation.service, time.monotonic() + 5), "unauthenticated EOF job survived")
        trials.append({"case": "authentication", "passed": True})
    return trials


def _peer_pid_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """A real foreign process cannot replace the captured caller."""
    trials: list[dict[str, Any]] = []
    with Invocation(broker, observer, root) as invocation:
        # A different ordinary process gets the real capability but fails kernel peer PID/token.
        config = {"socket": str(invocation.directory / "control.sock"), "capability": invocation.capability.hex()}
        result = subprocess.run(
            [sys.executable, str(SOURCE / "control.py"), "--fixture-client"],
            input=json.dumps(config) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        require(result.returncode != 0 and "EOFError" in result.stderr, "foreign kernel peer accepted")
        client = invocation.connect()
        require(client.launch(1)["ok"], "foreign peer displaced the owner")
        trials.append({"case": "peer-pid", "passed": True})
    return trials


def _peer_version_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """Reject a stale version derived from a real caller kernel token."""
    trials: list[dict[str, Any]] = []
    with Invocation(broker, observer, root, peer=PeerIdentity(stale_pidversion=True)) as invocation:
        # Reject a negative version derived from the real kernel caller token.
        _activate_operation(invocation, "request-authenticate")
        stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stream.settimeout(2)
        try:
            stream.connect(str(invocation.directory / "control.sock"))
            require(stream.recv(1) == b"", "stale kernel peer pid version accepted")
        finally:
            stream.close()
        trials.append({"case": "peer-pidversion", "passed": True})
    return trials


def _term_ignored_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """An ignored ordinary signal must still end at the native deadline."""
    trials: list[dict[str, Any]] = []
    with Invocation(broker, observer, root) as invocation:
        client = invocation.connect()
        launched = client.launch(timeout_ms=500)
        identity = invocation.capture_worker(launched)
        require(client.request(3, handle=launched["handle"], argument=15)["ok"], "SIGTERM rejected")
        time.sleep(0.03)
        require(STARTUP.alive(observer, identity), "SIGTERM-ignore control died")
        status = client.request(2, handle=launched["handle"])
        require(status["signal"] == 9 and status["reason"] == "timeout", "ignored signal bypassed timeout")
        trials.append({"case": "term-ignored", "passed": True, "status": status})
    return trials


def protocol_trials(broker: Path, observer: Path, root: Path) -> list[dict[str, Any]]:
    """Actual negative requests must reject while fixed positive execution works."""
    trials = [
        bootstrap_identity_trial(broker, observer, root),
        runtime_trap_trial(broker, observer, root),
        *exec_trials(broker, observer, root),
        *(exception_port_trial(broker, observer, root, kind) for kind in ("task", "thread")),
    ]
    for check in (
        _output_protocol_trials,
        _frame_size_trials,
        _authentication_trials,
        _peer_pid_trials,
        _peer_version_trials,
        _term_ignored_trials,
    ):
        trials.extend(check(broker, observer, root))
    return trials


class _Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


def verify_native_clock() -> dict[str, Any]:
    """Bracket the actual public libc CLOCK_MONOTONIC call with stdlib reads."""
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    clock = library.clock_gettime
    clock.argtypes = [ctypes.c_int, ctypes.POINTER(_Timespec)]
    clock.restype = ctypes.c_int
    samples = []
    for _ in range(10):
        native = _Timespec()
        before = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        require(clock(time.CLOCK_MONOTONIC, ctypes.byref(native)) == 0, "native clock probe failed")
        after = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        sampled = native.tv_sec * 1_000_000_000 + native.tv_nsec
        require(before <= sampled <= after, "Python/native CLOCK_MONOTONIC mapping failed")
        samples.append({"before_ns": before, "native_ns": sampled, "after_ns": after})
    return {
        "native_clock": "CLOCK_MONOTONIC",
        "python_native_reader": "clock_gettime_ns(CLOCK_MONOTONIC)",
        "elapsed_clock": time.get_clock_info("monotonic").implementation,
        "samples": samples,
    }


def build(root: Path) -> tuple[Path, Path, list[dict[str, Any]]]:
    """Compile captured fixture and SDK inputs; no production admission."""
    return BUILD.build(root, SOURCE, BUILD.BuildTools(STARTUP.command, verify_native_clock, require, MACH.prepare))


def run_trials(
    broker: Path, observer: Path, root: Path, repetitions: int, *, trials: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Reject any failed native case; do not run observer-assisted rescues as proof."""
    trials = [] if trials is None else trials
    trials.extend(protocol_trials(broker, observer, root))
    for index in range(repetitions):
        for case in LIFECYCLE_CASES:
            item = lifecycle_trial(broker, observer, root, case)
            item["repetition"] = index + 1
            trials.append(item)
        if (index + 1) % 10 == 0:
            _emit_json({"completed_repetitions": index + 1, "cases": len(LIFECYCLE_CASES)})
    return trials


def _counts_complete(counts: dict[str, int], minimum: int) -> bool:
    """Every required lifecycle count must meet the specified evidence threshold."""
    return all(count >= minimum for count in counts.values())


def receipt(repetitions: int, trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Full counts still cannot approve a fixture as a signed production boundary."""
    successes = Counter(item.get("case") for item in trials if item.get("passed") is True)
    counts = {case: successes[case] for case in LIFECYCLE_CASES}
    protocol = set(PROTOCOL_CASES).issubset(successes)
    passed = protocol and bool(trials) and all(item.get("passed") is True for item in trials)
    return {
        "schema_version": "specfact-managed-control-experiment-v4",
        "completed_lifecycle_cases": counts,
        "control_subset_passed": passed and _counts_complete(counts, 1),
        "repetition_gate_passed": passed and repetitions >= 100 and _counts_complete(counts, 100),
        "production_approved": False,
        "signed_boundary_verified": False,
        "signing_mode": "ad-hoc",
        "hardened_runtime": True,
        "architecture": platform.machine(),
        "os": platform.platform(),
        "repetitions": repetitions,
        "trials": trials,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-client", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--repetitions", type=int, choices=range(1, 101), default=1)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.fixture_client:
        return fixture_client()
    if args.out is None or platform.system() != "Darwin" or platform.machine() != "arm64":
        parser.error("--out and native Darwin ARM64 required")
    report: dict[str, Any] = {
        "production_approved": False,
        "signed_boundary_verified": False,
        "control_subset_passed": False,
        "repetition_gate_passed": False,
        "trials": [],
    }
    try:
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-control-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            broker, observer, inventory = build(root)
            report["artifacts"] = inventory
            report["clock_verification"] = json.loads((root / "clock-verification.json").read_text())
            trials = run_trials(broker, observer, root, args.repetitions, trials=report["trials"])
            report.update(receipt(args.repetitions, trials))
            report["os_build"] = STARTUP.command(["/usr/sbin/sysctl", "-n", "kern.osversion"]).stdout.strip()
    except Exception as error:
        report["failure"] = f"{type(error).__name__}: {error}"
        report["trials"].append({"case": "run-failure", "passed": False, "failure": report["failure"]})
        report.update(receipt(args.repetitions, report["trials"]))
        raise
    finally:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    _emit_json({key: value for key, value in report.items() if key not in ("artifacts", "trials")})
    return 0 if report["control_subset_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
