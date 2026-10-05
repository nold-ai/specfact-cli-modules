"""Fail-closed admission and lifecycle API for the native macOS broker.

This module does not select host executables. It turns a verified native capsule
lease and a closed plan identifier into an immutable request suitable for the
prebuilt broker protocol. Production eligibility remains false until the signed
artifact and complete boundary matrix are admitted.
"""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import stat
import struct
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol


SCHEMA = "specfact-native-execution-v1"
BROKER_MEMBER = "bin/specfact-native-broker"
BOOTSTRAP_MEMBER = "bin/specfact-native-bootstrap"
VERIFIER_MEMBER = "bin/specfact-native-verifier"
_PLAN_SEQUENCE = (
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
_PLAN_IDS = frozenset(_PLAN_SEQUENCE)
SUPPORTED_PLAN_IDS = _PLAN_SEQUENCE
_PLAN_NUMBERS = {name: index for index, name in enumerate(_PLAN_SEQUENCE, 1)}
_PLAN_NUMBERS["acquisition.uv-project.v1"] = 28  # 27 is a private managed Python child.
_REQUEST = struct.Struct("<IHHIIIIQQQ1024s1024s1024s1024s")
_REPLY = struct.Struct("<IHHIiI")
_ENVIRONMENT_KEYS = frozenset(
    {
        "LANG",
        "LC_ALL",
        "TZ",
        "SOURCE_DATE_EPOCH",
        "PYTHONHASHSEED",
        "PYTHONUTF8",
        "NO_COLOR",
    }
)
_DESCRIPTORS = frozenset({"stdin", "stdout", "stderr"})
_DIGEST = re.compile(r"[0-9a-f]{64}")


class NativeExecutionIncompleteError(RuntimeError):
    """A missing managed capability that must never fall back to the host."""

    def __init__(self, reason: str, *, capsule_identity: str = "") -> None:
        super().__init__(reason)
        self.evidence: Mapping[str, object] = MappingProxyType(
            {
                "status": "INCOMPLETE",
                "capability": SCHEMA,
                "capsule_identity": capsule_identity,
                "reason": reason,
                "production_eligible": False,
                "native_execution_performed": False,
            }
        )


@dataclass(frozen=True)
class ResourceBudget:
    address_space_bytes: int
    file_size_bytes: int
    open_files: int
    output_bytes: int


@dataclass(frozen=True)
class NativeExecutionRequest:
    schema: str
    plan_id: str
    capsule_identity: str
    capsule_root: Path
    invocation_root: Path
    project_snapshot: Path
    output_root: Path
    temporary_root: Path
    environment: tuple[tuple[str, str], ...]
    descriptor_grants: tuple[tuple[str, int], ...]
    timeout_ms: int
    budget: ResourceBudget
    production_eligible: bool = False


@dataclass(frozen=True)
class NativeExecutionResult:
    handle: int
    returncode: int
    stdout: bytes
    stderr: bytes


class NativeExecutionTransport(Protocol):
    """Private broker channel; implementations assign opaque handles."""

    def launch(self, request: NativeExecutionRequest) -> int: ...

    def wait(self, handle: int, timeout_ms: int) -> NativeExecutionResult: ...

    def cancel(self, handle: int) -> None: ...

    def close(self) -> None: ...


def _absolute(path: Path, label: str) -> Path:
    if not path.is_absolute() or path != Path(os.path.abspath(path)):
        raise ValueError(f"{label} must be an absolute canonical path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            raise ValueError(f"{label} must already exist") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{label} contains a symlink")
    if not path.is_dir():
        raise ValueError(f"{label} must be a directory")
    return path


def _owned_directory(path: Path, label: str, *, mode: int | None = None) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{label} must be an owner-owned directory")
    permissions = stat.S_IMODE(metadata.st_mode)
    if mode is not None and permissions != mode:
        raise ValueError(f"{label} must have mode {mode:04o}")
    if permissions & 0o022:
        raise ValueError(f"{label} must not be group/other writable")


def _tree_is_immutable(root: Path, label: str, *, root_may_be_private: bool = False) -> None:
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        metadata = current_path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise ValueError(f"{label} contains a symlink or foreign owner")
        permissions = stat.S_IMODE(metadata.st_mode)
        if root_may_be_private:
            if permissions != 0o700:
                raise ValueError(f"{label} directories must be owner-only")
        elif permissions & 0o222:
            raise ValueError(f"{label} must be immutable")
        for name in [*directories, *files]:
            child = current_path / name
            child_metadata = child.lstat()
            if stat.S_ISLNK(child_metadata.st_mode) or child_metadata.st_uid != os.getuid():
                raise ValueError(f"{label} contains a symlink or foreign owner")
            if name in files and stat.S_IMODE(child_metadata.st_mode) & 0o222:
                raise ValueError(f"{label} must be immutable")


def _below(child: Path, parent: Path, label: str) -> None:
    try:
        relative = child.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"{label} must remain below invocation root") from exc
    if not relative.parts:
        raise ValueError(f"{label} must be a dedicated directory below invocation root")


def _disjoint(left: Path, right: Path, label: str) -> None:
    if left == right or left in right.parents or right in left.parents:
        raise ValueError(f"{label} grants must be disjoint")


def _verified_lease(lease: object) -> tuple[Path, str]:
    evidence = getattr(lease, "evidence", None)
    identity = getattr(lease, "identity", "")
    fds = getattr(lease, "fds", None)
    identities = getattr(lease, "code_identities", None)
    path = getattr(lease, "path", None)
    if not isinstance(evidence, Mapping) or evidence.get("status") != "VERIFIED_CACHE_CANDIDATE":
        raise ValueError("native execution requires a verified capsule lease")
    if evidence.get("native_signing_mode") != "adhoc" or evidence.get("native_signing_verified") is not True:
        raise ValueError("native execution requires verified native signing evidence")
    if not isinstance(identity, str) or _DIGEST.fullmatch(identity) is None or not isinstance(path, Path):
        raise ValueError("native execution requires a bound capsule identity")
    if (
        not isinstance(fds, Mapping)
        or not isinstance(identities, Mapping)
        or not all(name in fds and name in identities for name in (BROKER_MEMBER, BOOTSTRAP_MEMBER, VERIFIER_MEMBER))
    ):
        raise ValueError("native execution requires live broker/bootstrap descriptors")
    capsule = _absolute(path, "capsule root")
    _owned_directory(capsule, "capsule root")
    _tree_is_immutable(capsule, "capsule tree", root_may_be_private=True)
    for name in (BROKER_MEMBER, BOOTSTRAP_MEMBER, VERIFIER_MEMBER):
        fd = fds[name]
        if type(fd) is not int or fd < 0:
            raise ValueError("native execution requires live broker/bootstrap descriptors")
        try:
            descriptor = os.fstat(fd)
            pathname = (capsule / name).lstat()
        except (OSError, FileNotFoundError) as exc:
            raise ValueError("native execution requires live broker/bootstrap descriptors") from exc
        observed = (descriptor.st_dev, descriptor.st_ino)
        if (
            observed != identities[name]
            or observed != (pathname.st_dev, pathname.st_ino)
            or not stat.S_ISREG(descriptor.st_mode)
            or descriptor.st_uid != os.getuid()
            or stat.S_IMODE(descriptor.st_mode) != 0o500
        ):
            raise ValueError("verified broker/bootstrap identity changed")
    return capsule, identity


def _environment(values: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    if len(values) > len(_ENVIRONMENT_KEYS):
        raise ValueError("unsupported environment key")
    for key, value in values.items():
        if key not in _ENVIRONMENT_KEYS:
            raise ValueError(f"unsupported environment key: {key}")
        if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1024 or "\0" in value:
            raise ValueError(f"invalid environment value: {key}")
        result.append((key, value))
    return tuple(sorted(result))


def _descriptors(values: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    if set(values) != _DESCRIPTORS or any(type(fd) is not int or fd < 0 or fd > 2 for fd in values.values()):
        raise ValueError("descriptor grants must be exactly stdin/stdout/stderr on descriptors 0/1/2")
    if len(set(values.values())) != 3:
        raise ValueError("descriptor grants must be distinct")
    return tuple(sorted(values.items()))


def _budget(value: ResourceBudget) -> None:
    if not (
        256 << 20 <= value.address_space_bytes <= 16 << 30
        and 1 << 20 <= value.file_size_bytes <= 1 << 30
        and 32 <= value.open_files <= 1024
        and 1024 <= value.output_bytes <= 64 << 20
    ):
        raise ValueError("resource budget is outside the admitted bounds")


def prepare_native_execution(
    *,
    lease: object,
    plan_id: str,
    invocation_root: Path,
    project_snapshot: Path,
    output_root: Path,
    temporary_root: Path,
    environment: Mapping[str, str],
    descriptor_grants: Mapping[str, int],
    timeout_ms: int,
    budget: ResourceBudget,
) -> NativeExecutionRequest:
    """Validate a closed native plan without accepting an executable or PID."""
    capsule, identity = _verified_lease(lease)
    if plan_id not in _PLAN_IDS:
        raise NativeExecutionIncompleteError(f"unsupported_native_plan:{plan_id}", capsule_identity=identity)
    invocation = _absolute(invocation_root, "invocation root")
    project = _absolute(project_snapshot, "project snapshot")
    output = _absolute(output_root, "output root")
    temporary = _absolute(temporary_root, "temporary root")
    _owned_directory(invocation, "invocation root", mode=0o700)
    _owned_directory(output, "output root", mode=0o700)
    _owned_directory(temporary, "temporary root", mode=0o700)
    _owned_directory(project, "project snapshot")
    _tree_is_immutable(project, "project snapshot")
    _below(project, invocation, "project snapshot")
    _below(output, invocation, "output root")
    _below(temporary, invocation, "temporary root")
    for granted in (project, output, temporary):
        _disjoint(granted, capsule, "capsule/invocation")
    _disjoint(project, output, "project/output")
    _disjoint(project, temporary, "project/temporary")
    _disjoint(output, temporary, "output/temporary")
    if type(timeout_ms) is not int or not 50 <= timeout_ms <= 900_000:
        raise ValueError("timeout must be between 50 and 900000 milliseconds")
    _budget(budget)
    return NativeExecutionRequest(
        schema=SCHEMA,
        plan_id=plan_id,
        capsule_identity=identity,
        capsule_root=capsule,
        invocation_root=invocation,
        project_snapshot=project,
        output_root=output,
        temporary_root=temporary,
        environment=_environment(environment),
        descriptor_grants=_descriptors(descriptor_grants),
        timeout_ms=timeout_ms,
        budget=budget,
    )


class NativeExecutionSession:
    """Track broker-assigned handles and reject foreign process selection."""

    def __init__(self, transport: NativeExecutionTransport) -> None:
        self._transport = transport
        self._active: set[int] = set()
        self._closed = False

    def _open(self) -> None:
        if self._closed:
            raise RuntimeError("native execution session is closed")

    def launch(self, request: NativeExecutionRequest) -> int:
        self._open()
        if request.schema != SCHEMA or request.plan_id not in _PLAN_IDS:
            raise ValueError("request was not admitted by this execution contract")
        handle = self._transport.launch(request)
        if type(handle) is not int or handle <= 0 or handle in self._active:
            self.close()
            raise RuntimeError("broker returned an invalid or duplicate handle")
        self._active.add(handle)
        return handle

    def _owned(self, handle: int) -> None:
        self._open()
        if type(handle) is not int or handle not in self._active:
            raise ValueError("operation requires an owned active handle")

    def wait(self, handle: int, timeout_ms: int) -> NativeExecutionResult:
        self._owned(handle)
        if type(timeout_ms) is not int or not 1 <= timeout_ms <= 900_000:
            raise ValueError("wait timeout is outside the bounded range")
        result = self._transport.wait(handle, timeout_ms)
        if result.handle != handle:
            self.close()
            raise RuntimeError("broker response handle mismatch")
        self._active.remove(handle)
        return result

    def cancel(self, handle: int) -> None:
        self._owned(handle)
        self._transport.cancel(handle)
        self._active.remove(handle)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._active.clear()
        self._transport.close()

    def __enter__(self) -> NativeExecutionSession:
        self._open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class BinaryNativeExecutionTransport:
    """Binary private-channel transport for the prebuilt invocation broker."""

    def __init__(self, lease: object) -> None:
        capsule, _identity = _verified_lease(lease)
        broker = capsule / BROKER_MEMBER
        verifier = capsule / VERIFIER_MEMBER
        component = capsule / "provenance/native-component.json"
        try:
            metadata = json.loads(component.read_text(encoding="utf-8"))
            requirement = metadata["broker_designated_requirement"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("native component lacks authenticated broker requirement") from exc
        if not isinstance(requirement, str) or not requirement or len(requirement.encode("utf-8")) > 4096:
            raise ValueError("native component broker requirement is invalid")
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        child.set_inheritable(True)
        environment = {"LANG": "C", "LC_ALL": "C", "SPECFACT_CAPSULE_ROOT": str(capsule)}
        try:
            self._process = subprocess.Popen(
                [str(broker), "--control-fd", str(child.fileno()), "--capsule-root", str(capsule)],
                close_fds=True,
                pass_fds=(child.fileno(),),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except BaseException:
            parent.close()
            child.close()
            raise
        child.close()
        try:
            while True:
                try:
                    waited, status = os.waitpid(self._process.pid, os.WUNTRACED)
                    break
                except InterruptedError:
                    continue
            if waited != self._process.pid or not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGSTOP:
                raise RuntimeError("native broker did not enter its verification stop")
            _verified_lease(lease)
            verified = subprocess.run(
                [str(verifier), str(self._process.pid), requirement],
                check=False,
                capture_output=True,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                env={"LANG": "C", "LC_ALL": "C"},
                timeout=5,
            )
            _verified_lease(lease)
            if verified.returncode:
                raise RuntimeError("native broker running-image verification failed")
            os.kill(self._process.pid, signal.SIGCONT)
        except BaseException:
            parent.close()
            self._process.kill()
            self._process.wait(timeout=5)
            raise
        self._channel = parent
        self._requests: dict[int, NativeExecutionRequest] = {}
        self._closed = False

    @staticmethod
    def _path(value: Path) -> bytes:
        encoded = os.fsencode(value)
        if len(encoded) >= 1024 or b"\0" in encoded:
            raise ValueError("native grant path exceeds protocol bounds")
        return encoded.ljust(1024, b"\0")

    def _send(self, request: NativeExecutionRequest, opcode: int, handle: int, timeout_ms: int) -> tuple[int, int]:
        if self._closed:
            raise RuntimeError("native broker transport is closed")
        payload = _REQUEST.pack(
            0x53464E31,
            1,
            opcode,
            _PLAN_NUMBERS[request.plan_id],
            handle,
            timeout_ms,
            request.budget.open_files,
            request.budget.address_space_bytes,
            request.budget.file_size_bytes,
            request.budget.output_bytes,
            self._path(request.invocation_root),
            self._path(request.project_snapshot),
            self._path(request.output_root),
            self._path(request.temporary_root),
        )
        self._channel.sendall(payload)
        response = bytearray()
        while len(response) < _REPLY.size:
            chunk = self._channel.recv(_REPLY.size - len(response))
            if not chunk:
                raise RuntimeError("native broker closed before replying")
            response.extend(chunk)
        magic, version, status, returned_handle, wait_status, detail = _REPLY.unpack(response)
        if magic != 0x53464E31 or version != 1 or (opcode != 1 and returned_handle != handle):
            self.close()
            raise RuntimeError("invalid native broker reply")
        if status:
            raise NativeExecutionIncompleteError(
                f"native_broker_error:{detail}", capsule_identity=request.capsule_identity
            )
        return returned_handle, wait_status

    def launch(self, request: NativeExecutionRequest) -> int:
        handle, _status = self._send(request, 1, 0, request.timeout_ms)
        if handle <= 0 or handle in self._requests:
            self.close()
            raise RuntimeError("native broker returned an invalid handle")
        self._requests[handle] = request
        return handle

    def wait(self, handle: int, timeout_ms: int) -> NativeExecutionResult:
        request = self._requests.get(handle)
        if request is None:
            raise ValueError("operation requires an owned broker handle")
        try:
            returned, status = self._send(request, 2, handle, timeout_ms)
        finally:
            self._requests.pop(handle, None)
        if os.WIFEXITED(status):
            returncode = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            returncode = -os.WTERMSIG(status)
        else:
            self.close()
            raise RuntimeError("native broker returned a nonterminal wait status")
        stdout = self._read_stream(request, "managed-stdout.bin")
        stderr = self._read_stream(request, "managed-stderr.bin")
        if len(stdout) + len(stderr) > request.budget.output_bytes:
            self.close()
            raise RuntimeError("native worker output exceeded its admitted budget")
        return NativeExecutionResult(returned, returncode, stdout, stderr)

    @staticmethod
    def _read_stream(request: NativeExecutionRequest, name: str) -> bytes:
        path = request.output_root / name
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_nlink != 1
                or before.st_size > request.budget.output_bytes
            ):
                raise RuntimeError("native worker output identity is invalid")
            content = os.read(descriptor, request.budget.output_bytes + 1)
            after = os.fstat(descriptor)
            if len(content) != before.st_size or (before.st_dev, before.st_ino, before.st_size) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
            ):
                raise RuntimeError("native worker output changed during verification")
            return content
        finally:
            os.close(descriptor)

    def cancel(self, handle: int) -> None:
        request = self._requests.get(handle)
        if request is None:
            raise ValueError("operation requires an owned broker handle")
        self._send(request, 3, handle, request.timeout_ms)
        del self._requests[handle]

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._requests.clear()
        self._channel.close()
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=5)


# Compatibility name for the initial integration branch; both names are the
# same real binary protocol transport, never the unit-test fake.
NativeBrokerTransport = BinaryNativeExecutionTransport
