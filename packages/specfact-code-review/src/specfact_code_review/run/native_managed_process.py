"""Live subprocess compatibility over the broker's inherited worker pipes.

This adapter never creates a process or selects a host PID. Kernel confinement,
direct-child tracing and permission inheritance remain the broker's boundary.
"""

from __future__ import annotations

import codecs
import errno
import io
import locale
import os
import plistlib
import shutil
import signal
import stat
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from unittest.mock import patch

from beartype import beartype
from icontract import require


MAGIC = 0x53464D31
VERSION = 1
LAUNCH, POLL, SIGNAL, STDOUT, STDERR, WRITE_STDIN, CLOSE_STDIN, RELEASE = range(1, 9)
MAX_PAYLOAD = 4096
MAX_OUTPUT = 4 << 20
CHUNK = 4096
_REQUEST = struct.Struct("<IHHII")
_REPLY = struct.Struct("<IHHIiI")


def _forward_output(value: bytes | str, stream: Any) -> None:
    """Preserve inherited bytes; redirected text-only sinks receive replacement text."""
    if isinstance(value, bytes) and hasattr(stream, "buffer"):
        stream.buffer.write(value)
        stream.buffer.flush()
    else:
        stream.write(value if isinstance(value, str) else value.decode("utf-8", "replace"))
        stream.flush()


class ManagedProcessError(OSError):
    """Unsupported process behavior produces incomplete evidence, never fallback."""

    def __init__(self, reason: str):
        super().__init__(errno.ENOTSUP, f"project_native_managed_process_incomplete:{reason}")


@dataclass(frozen=True)
class WorkerReply:
    handle: int
    wait_status: int
    data: bytes


class WorkerTransport(Protocol):
    def exchange(self, opcode: int, handle: int = 0, payload: bytes = b"") -> WorkerReply: ...


class NativeWorkerChannel:
    """One private inherited channel, with bounded framing and serial requests."""

    def __init__(self, request_fd: int = 5, reply_fd: int = 6):
        for descriptor in (request_fd, reply_fd):
            try:
                metadata = os.fstat(descriptor)
            except OSError as exc:
                raise ManagedProcessError("broker worker channel unavailable") from exc
            if not stat.S_ISFIFO(metadata.st_mode):
                raise ManagedProcessError("broker worker channel is not a pipe")
        self.request_fd, self.reply_fd = request_fd, reply_fd
        self.lock = threading.Lock()

    def _read(self, length: int) -> bytes:
        result = bytearray()
        while len(result) < length:
            data = os.read(self.reply_fd, length - len(result))
            if not data:
                raise ManagedProcessError("broker connection closed")
            result.extend(data)
        return bytes(result)

    def exchange(self, opcode: int, handle: int = 0, payload: bytes = b"") -> WorkerReply:
        if opcode not in range(LAUNCH, RELEASE + 1) or len(payload) > MAX_PAYLOAD or not 0 <= handle <= 0xFFFFFFFF:
            raise ManagedProcessError("invalid request bounds")
        with self.lock:
            request = memoryview(_REQUEST.pack(MAGIC, VERSION, opcode, handle, len(payload)) + payload)
            while request:
                count = os.write(self.request_fd, request)
                if count <= 0:
                    raise ManagedProcessError("broker request failed")
                request = request[count:]
            magic, version, status, returned, wait_status, length = _REPLY.unpack(self._read(_REPLY.size))
            if magic != MAGIC or version != VERSION or (opcode != LAUNCH and returned != handle):
                raise ManagedProcessError("invalid broker reply")
            if status:
                raise ManagedProcessError(f"broker rejected operation {opcode}: errno={length}")
            if length > CHUNK:
                raise ManagedProcessError("broker reply exceeds bound")
            return WorkerReply(returned, wait_status, self._read(length))


class _Reader(io.RawIOBase):
    name = "<managed-output>"

    def __init__(self, process: ManagedPopen, opcode: int):
        self.process, self.opcode = process, opcode
        self.used = 0
        self._pending = bytearray()

    def readable(self) -> bool:
        return True

    def available(self, size: int = CHUNK) -> tuple[bytes, bool]:
        if self._pending:
            data = bytes(self._pending[:size])
            del self._pending[:size]
            return data, self.process.returncode is not None
        if self.process.released:
            return b"", True
        return self.fetch(size)

    def fetch(self, size: int = CHUNK) -> tuple[bytes, bool]:
        reply = self.process.transport.exchange(self.opcode, self.process.handle, struct.pack("<I", min(size, CHUNK)))
        self.used += len(reply.data)
        if self.used > MAX_OUTPUT:
            self.process.kill()
            raise ManagedProcessError("output exceeds bound")
        return reply.data, reply.wait_status != -1

    def read(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        result = bytearray()
        while size < 0 or len(result) < size:
            data, ended = self.available(CHUNK if size < 0 else size - len(result))
            result.extend(data)
            if len(result) > MAX_OUTPUT:
                raise ManagedProcessError("output exceeds bound")
            if ended and not data:
                break
            if data and size >= 0:
                break
            if not data:
                time.sleep(0.005)
        return bytes(result)

    def readinto(self, buffer) -> int:
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


class _Writer(io.RawIOBase):
    name = "<managed-input>"

    def __init__(self, process: ManagedPopen):
        self.process = process

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:
        view = memoryview(data)
        used = 0
        while used < len(view):
            reply = self.process.transport.exchange(WRITE_STDIN, self.process.handle, bytes(view[used : used + CHUNK]))
            if not 0 <= reply.wait_status <= min(CHUNK, len(view) - used):
                raise ManagedProcessError("invalid input acknowledgement")
            used += reply.wait_status
            if not reply.wait_status:
                if self.process.poll() is not None:
                    raise BrokenPipeError(errno.EPIPE, "managed child stdin closed")
                time.sleep(0.005)
        return used

    def close(self) -> None:
        if not self.closed and not self.process.released:
            self.process.transport.exchange(CLOSE_STDIN, self.process.handle)
        super().close()


class ManagedPopen:
    """An owned worker with file-spooled bounded streams, never a host PID."""

    def __init__(self, transport: WorkerTransport, args: list[str], request: bytes, options: Mapping[str, Any]):
        self.encoding = options.get("encoding") or "utf-8"
        if self.encoding == "locale":
            self.encoding = locale.getencoding()
        self.errors = options.get("errors") or "strict"
        codecs.lookup(self.encoding)
        codecs.lookup_error(self.errors)
        self.transport, self.args = transport, args
        reply = transport.exchange(LAUNCH, payload=request)
        if reply.handle <= 0 or reply.wait_status != -1:
            raise ManagedProcessError("invalid launch acknowledgement")
        self.handle = reply.handle
        self.released = False
        self.returncode: int | None = None
        self.text_mode = bool(options.get("text") or options.get("universal_newlines") or options.get("encoding"))
        self._stdout, self._stderr = _Reader(self, STDOUT), _Reader(self, STDERR)
        self.stdin = self._input_stream(options)
        self.stdout = self._output_stream(self._stdout)
        self.stderr = self._output_stream(self._stderr)
        self._stdout_mode, self._stderr_mode = options.get("stdout"), options.get("stderr")
        if self._stdout_mode != subprocess.PIPE:
            self.stdout = None
        if self._stderr_mode != subprocess.PIPE:
            self.stderr = None

    def _input_stream(self, options):
        writer = _Writer(self) if options.get("stdin") == subprocess.PIPE else None
        return (
            io.TextIOWrapper(writer, encoding=self.encoding, errors=self.errors, write_through=True)
            if writer and self.text_mode
            else writer
        )

    def _output_stream(self, reader):
        return io.TextIOWrapper(reader, encoding=self.encoding, errors=self.errors) if self.text_mode else reader

    @property
    def pid(self) -> int:
        raise ManagedProcessError("host PIDs are not exposed; use poll/wait/send_signal")

    def poll(self) -> int | None:
        if self.returncode is None:
            reply = self.transport.exchange(POLL, self.handle)
            if reply.wait_status != -1:
                self.returncode = os.waitstatus_to_exitcode(reply.wait_status)
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.poll() is None:
            if deadline is not None and time.monotonic() >= deadline:
                assert timeout is not None
                raise subprocess.TimeoutExpired(self.args, timeout)
            time.sleep(0.005)
        assert self.returncode is not None
        self._finish(forward=True)
        return self.returncode

    def send_signal(self, value: int) -> None:
        if value not in {signal.SIGINT, signal.SIGTERM, signal.SIGKILL}:
            raise ManagedProcessError("signal is not admitted")
        if self.returncode is not None:
            return
        self.transport.exchange(SIGNAL, self.handle, struct.pack("<I", value))

    def terminate(self) -> None:
        self.send_signal(signal.SIGTERM)

    def kill(self) -> None:
        self.send_signal(signal.SIGKILL)

    def _communicate_stdin(self, pending, sent, closed):
        if closed:
            return sent, closed
        if sent < len(pending):
            chunk = pending[sent : sent + CHUNK]
            reply = self.transport.exchange(WRITE_STDIN, self.handle, chunk)
            if not 0 <= reply.wait_status <= len(chunk):
                raise ManagedProcessError("invalid input acknowledgement")
            return sent + reply.wait_status, False
        assert self.stdin is not None
        self.stdin.close()
        return sent, True

    def _capture_output(self, captured) -> bool:
        received = False
        for reader, buffer in zip((self._stdout, self._stderr), captured, strict=True):
            data, _terminal = reader.available()
            received |= bool(data)
            buffer.extend(data)
        if sum(map(len, captured)) > MAX_OUTPUT:
            self.kill()
            raise ManagedProcessError("output exceeds bound")
        return received

    def _communicate_input(self, value) -> bytes:
        if value is None:
            return b""
        if self.stdin is None:
            raise ValueError("managed stdin must be PIPE for input")
        return value.encode(self.encoding, self.errors) if self.text_mode else bytes(value)

    def _communicated_result(self, captured):
        values = [
            bytes(buffer).decode(self.encoding, self.errors) if self.text_mode else bytes(buffer) for buffer in captured
        ]
        for value, mode, stream in zip(
            values, (self._stdout_mode, self._stderr_mode), (sys.stdout, sys.stderr), strict=True
        ):
            if mode is None and value:
                _forward_output(value, stream)
        return tuple(values)

    def communicate(self, input=None, timeout: float | None = None):
        deadline = None if timeout is None else time.monotonic() + timeout
        pending = self._communicate_input(input)
        sent = 0
        closed = self.stdin is None or self.stdin.closed
        captured = [bytearray(), bytearray()]
        while True:
            sent, closed = self._communicate_stdin(pending, sent, closed)
            ended = self.poll() is not None
            received = self._capture_output(captured)
            if ended and not received:
                break
            if deadline is not None and time.monotonic() >= deadline:
                assert timeout is not None
                raise subprocess.TimeoutExpired(self.args, timeout, bytes(captured[0]), bytes(captured[1]))
            if not received:
                time.sleep(0.005)
        self._finish(forward=False)
        return self._communicated_result(captured)

    @staticmethod
    def _retire_stream(reader, mode, stream, forward) -> None:
        pending = bytearray()
        while True:
            data, ended = reader.fetch()
            pending.extend(data)
            if ended and not data:
                break
        if mode == subprocess.PIPE:
            reader._pending.extend(pending)
        elif forward and mode is None and pending:
            _forward_output(bytes(pending), stream)

    def _finish(self, *, forward: bool) -> None:
        if self.released:
            return
        if self.returncode is None:
            raise ManagedProcessError("cannot retire a running process")
        if self.stdin is not None and not self.stdin.closed:
            self.stdin.close()
        try:
            for reader, mode, stream in zip(
                (self._stdout, self._stderr),
                (self._stdout_mode, self._stderr_mode),
                (sys.stdout, sys.stderr),
                strict=True,
            ):
                self._retire_stream(reader, mode, stream, forward)
        finally:
            self.transport.exchange(RELEASE, self.handle)
            self.released = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_exc):
        if self.stdin is not None:
            self.stdin.close()
        if exc_type is not None and self.poll() is None:
            self.kill()
        self.wait(timeout=5 if exc_type is not None else None)
        for stream in (self.stdout, self.stderr):
            if stream is not None:
                stream.close()


def _warning_argument_width(arguments, index) -> int:
    if index + 1 >= len(arguments):
        raise ManagedProcessError("Python warning filter is missing")
    return 2


def python_launch_isolated(arguments: Sequence[str]) -> bool:
    """Interpret supported startup flags before the execution selector."""
    isolated, index = False, 0
    while index < len(arguments):
        value = arguments[index]
        if value in {"-E", "-S"}:
            raise ManagedProcessError("Python startup isolation cannot be bypassed")
        if value in {"-I", "-B", "-u"}:
            isolated |= value == "-I"
            index += 1
        elif value == "-W":
            index += _warning_argument_width(arguments, index)
        elif value.startswith("-W"):
            index += 1
        else:
            break
    return isolated


class ManagedSubprocess:
    """Map reviewed executable identities and cwd grants to owned child requests."""

    def __init__(self, transport: WorkerTransport, *, roots: Mapping[str, Path], executables: Mapping[str, str]):
        self.transport, self.roots, self.executables = transport, dict(roots), dict(executables)

    def _cwd(self, raw) -> str:
        selected = Path.cwd() if raw is None else Path(raw)
        if not selected.is_absolute():
            selected = Path.cwd() / selected
        if selected.resolve() != selected or not selected.is_dir():
            raise ManagedProcessError("working directory is not canonical")
        for label, root in self.roots.items():
            if selected.is_relative_to(root):
                return label + ("/" + selected.relative_to(root).as_posix() if selected != root else "")
        raise ManagedProcessError("working directory exceeds inherited grants")

    def _private_python_alias(self, selected: Path) -> bool:
        return (
            selected.is_absolute()
            and selected.parent.name == "bin"
            and any(selected.parent.parent.is_relative_to(root) for root in self.roots.values())
        )

    def _python_alias_settings(self, prefix: Path) -> None:
        if prefix.resolve() != prefix or not any(prefix.is_relative_to(root) for root in self.roots.values()):
            raise ManagedProcessError("executable identity is not admitted")
        config = prefix / "pyvenv.cfg"
        if config.is_symlink() or not config.is_file() or config.stat().st_size > 16384:
            raise ManagedProcessError("executable identity is not admitted")
        settings = {
            name.strip().lower(): value.strip().lower()
            for line in config.read_text().splitlines()
            if "=" in line
            for name, value in [line.split("=", 1)]
        }
        if settings.get("include-system-site-packages") != "false":
            raise ManagedProcessError("executable identity is not admitted")

    def _fixed_python_images(self) -> set[Path]:
        return {
            Path(name).resolve()
            for name, kind in self.executables.items()
            if kind == "python"
            and Path(name).is_absolute()
            and Path(name).is_file()
            and not any(Path(name).is_relative_to(root) for root in self.roots.values())
        }

    def _python_prefix(self, executable: str) -> str:
        """Admit a private alias, never execute its path or a customer binary."""
        active = os.environ.get("VIRTUAL_ENV") if executable in {"python", "python3"} else None
        selected = Path(active) / "bin" / executable if active else Path(executable)
        if not active and not self._private_python_alias(selected) and self.executables.get(executable) == "python":
            return ""
        if not selected.is_absolute() or selected.parent.name != "bin":
            raise ManagedProcessError("executable identity is not admitted")
        prefix = selected.parent.parent
        self._python_alias_settings(prefix)
        # Alias metadata never authorizes a different executable image.
        if selected.resolve() not in self._fixed_python_images():
            raise ManagedProcessError("executable identity is not admitted")
        return str(prefix)

    def _build_paths(self, environment: Mapping[str, Any]) -> list[str]:
        value = environment.get("PYTHONPATH")
        if value is None:
            return []
        if not isinstance(value, str):
            raise ManagedProcessError("Python path must be a bounded private directory list")
        paths = value.split(os.pathsep)
        if len(paths) > 128 or any(
            not path
            or not Path(path).is_absolute()
            or Path(path).resolve() != Path(path)
            or not Path(path).is_dir()
            or not any(Path(path).is_relative_to(root) for root in self.roots.values())
            for path in paths
        ):
            raise ManagedProcessError("Python path exceeds inherited grants")
        return paths

    def _uv_prefix_environment(self, environment) -> None:
        prefix = environment.get("VIRTUAL_ENV")
        if prefix:
            if not isinstance(prefix, str):
                raise ManagedProcessError("uv environment exceeds inherited grants")
            selected = Path(prefix)
            if (
                not selected.is_absolute()
                or selected.resolve() != selected
                or not selected.is_dir()
                or not any(selected.is_relative_to(root) for root in self.roots.values())
            ):
                raise ManagedProcessError("uv environment exceeds inherited grants")
            if environment.get("PATH") == os.pathsep.join([str(selected / "bin"), os.environ.get("PATH", "")]):
                environment.pop("PATH")

    @staticmethod
    def _strip_uv_credentials(environment) -> None:
        for name in tuple(environment):
            if (
                name == "PYTHONPATH"
                or name.startswith("SPECFACT_")
                or any(marker in name.upper() for marker in ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "PROXY"))
            ):
                environment.pop(name)

    def _uv_fixed_environment(self) -> dict[str, str]:
        wheelhouse = self.roots["project"] / "wheelhouse"
        if wheelhouse.resolve() != wheelhouse or not wheelhouse.is_dir():
            raise ManagedProcessError("uv offline wheelhouse exceeds inherited grants")
        # These values do not grant execution or network access. The native
        # bootstrap independently fixes the same offline and bridge settings.
        return {
            "UV_OFFLINE": "1",
            "UV_NO_INDEX": "1",
            "UV_FIND_LINKS": str(wheelhouse),
            "UV_CACHE_DIR": str(self.roots["temporary"] / "uv-cache"),
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_KEYRING_PROVIDER": "disabled",
            "UV_LINK_MODE": "copy",
        }

    @staticmethod
    def _validate_uv_overrides(executable, image, environment, fixed) -> None:
        if "UV_PYTHON" in environment and environment.pop("UV_PYTHON") != str(
            image.parent.parent / "python/bin/python3"
        ):
            raise ManagedProcessError("uv interpreter identity is not admitted")
        if "HATCH_UV" in environment and environment["HATCH_UV"] != executable:
            raise ManagedProcessError("uv executable environment override is not admitted")
        if any(
            name.startswith("UV_") and name not in fixed and (name != "UV_NO_PROGRESS" or value != "1")
            for name, value in environment.items()
        ):
            raise ManagedProcessError("uv environment option is not admitted")

    def _uv_environment(self, executable: str, environment: dict[str, Any]) -> None:
        image = self._tool_image("uv")
        if Path(executable) != image:
            raise ManagedProcessError("uv executable identity is not admitted")
        self._uv_prefix_environment(environment)
        fixed = self._uv_fixed_environment()
        for name, value in fixed.items():
            if name in environment and environment[name] != value:
                raise ManagedProcessError(f"uv offline environment override is not admitted:{name}")
        self._strip_uv_credentials(environment)
        self._validate_uv_overrides(executable, image, environment, fixed)
        environment.update(fixed)

    @staticmethod
    def _uv_interpreter_selector(args, index):
        value = args[index]
        if value in {"--python", "-p"}:
            if index + 1 >= len(args):
                raise ManagedProcessError("uv install interpreter selector is missing")
            return args[index + 1], index + 2
        if value.startswith("--python="):
            return value.removeprefix("--python="), index + 1
        if value.startswith("-p"):
            return value.removeprefix("-p"), index + 1
        return None, index + 1

    def _uv_install_arguments(self, args: list[str], environment: Mapping[str, Any]) -> list[str]:
        """Keep UV's install target private despite bootstrap's fixed image selector."""
        if args[1:3] not in (["pip", "install"], ["pip", "sync"]) or not environment.get("VIRTUAL_ENV"):
            return args
        prefix = environment["VIRTUAL_ENV"]
        alias = str(Path(prefix) / "bin/python")
        if self._python_prefix(alias) != prefix:
            raise ManagedProcessError("uv install environment identity is not admitted")
        explicit, index = False, 3
        while index < len(args) and args[index] != "--":
            target, index = self._uv_interpreter_selector(args, index)
            if target is None:
                continue
            if target != alias:
                raise ManagedProcessError("uv install interpreter override is not admitted")
            explicit = True
        return args if explicit else [*args[:3], "--python", alias, *args[3:]]

    def _git_image(self) -> Path:
        return self._tool_image("git")

    def _validate_tool_image(self, image: Path, kind: str, label: str) -> None:
        if (
            image.resolve() != image
            or image.is_symlink()
            or not image.is_file()
            or image.stat().st_mode & 0o222
            or not image.stat().st_mode & 0o111
            or image.name != kind
            or image.parent.name != "tools"
            or any(image.is_relative_to(root) for root in self.roots.values())
        ):
            raise ManagedProcessError(f"{label} executable identity is not admitted")

    def _tool_image(self, kind: str) -> Path:
        label = "Git" if kind == "git" else "uv"
        if kind not in {"git", "uv"}:
            raise ManagedProcessError("tool executable identity is not admitted")
        images = [Path(name) for name, value in self.executables.items() if value == kind and Path(name).is_absolute()]
        if len(images) != 1:
            raise ManagedProcessError(f"{label} executable identity is not admitted")
        image = images[0]
        self._validate_tool_image(image, kind, label)
        return image

    def _git_repository_selector(self, arguments, index, selected):
        value = arguments[index]
        if value.startswith("--git-dir="):
            path = Path(value.split("=", 1)[1])
            index += 1
        elif index + 1 < len(arguments):
            path = Path(arguments[index + 1])
            index += 2
        else:
            raise ManagedProcessError("Git private repository selector is missing")
        path = path if path.is_absolute() else selected / path
        if (
            path.resolve() != path
            or not path.is_dir()
            or not any(path.is_relative_to(root) for root in self.roots.values())
        ):
            raise ManagedProcessError("Git repository selector exceeds inherited grants")
        if value == "-C":
            selected = path
        return index, selected

    def _git_selector_prefix(self, arguments, selected):
        index = 0
        while index < len(arguments):
            value = arguments[index]
            if value == "--no-pager":
                index += 1
                continue
            if value == "-c" and arguments[index + 1 : index + 2] == ["log.showSignature=false"]:
                index += 2
                continue
            if value in {"--git-dir", "-C"} or value.startswith("--git-dir="):
                index, selected = self._git_repository_selector(arguments, index, selected)
                continue
            break
        return arguments[index:]

    @staticmethod
    def _git_read_query(query) -> None:
        commands = {
            "--version",
            "version",
            "describe",
            "rev-parse",
            "rev-list",
            "log",
            "status",
            "symbolic-ref",
            "ls-files",
            "cat-file",
            "show-ref",
            "for-each-ref",
            "diff",
            "diff-index",
            "diff-files",
        }
        if (
            not query
            or query[0] not in commands
            or any(value.split("=", 1)[0] in {"--broken", "--show-signature"} for value in query)
        ):
            raise ManagedProcessError("Git command is not a built-in SCM query")
        if query[0] == "symbolic-ref" and (
            "--delete" in query or "-d" in query or sum(not value.startswith("-") for value in query[1:]) != 1
        ):
            raise ManagedProcessError("Git symbolic-ref must be a read query")

    def _git_query(self, arguments: Sequence[str], cwd) -> None:
        label, _separator, relative = self._cwd(cwd).partition("/")
        query = self._git_selector_prefix(arguments, self.roots[label] / relative)
        self._git_read_query(query)

    def _git_environment(self, environment: dict[str, Any]) -> None:
        if any(name.startswith("GIT_") for name in environment):
            raise ManagedProcessError("Git environment configuration is not admitted")
        for name in tuple(environment):
            if (
                name in {"PYTHONPATH", "LC_ALL", "XDG_CONFIG_HOME"}
                or name.startswith(("SPECFACT_", "UV_"))
                or any(marker in name.upper() for marker in ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "PROXY"))
            ):
                environment.pop(name)

    @staticmethod
    def _validate_stream_options(options) -> None:
        for name in ("stdin", "stdout", "stderr"):
            admitted = {None, subprocess.PIPE, subprocess.DEVNULL}
            if name == "stderr":
                admitted.add(subprocess.STDOUT)
            if options.get(name) not in admitted:
                raise ManagedProcessError("descriptor inheritance is unsupported")

    @staticmethod
    def _launch_arguments(args, options) -> list[str]:
        allowed = {
            "stdin",
            "stdout",
            "stderr",
            "cwd",
            "env",
            "text",
            "universal_newlines",
            "encoding",
            "errors",
            "bufsize",
            "shell",
            "close_fds",
        }
        if isinstance(args, (str, bytes)) or len(args) > 128:
            raise ManagedProcessError("arguments must be a bounded string sequence")
        try:
            args = [os.fsdecode(value) for value in args]
        except TypeError as exc:
            raise ManagedProcessError("arguments must be a bounded string sequence") from exc
        if any("\0" in value for value in args):
            raise ManagedProcessError("arguments must be a bounded string sequence")
        if set(options) - allowed or options.get("shell") or options.get("close_fds", True) is not True:
            raise ManagedProcessError("shell, descriptors or startup options are unsupported")
        return args

    def _program_selection(self, args, options) -> tuple[str, str, bool]:
        program = self.executables.get(args[0]) if self.executables.get(args[0]) in {"uv", "git"} else "python"
        if program == "git":
            self._git_image()
            self._git_query(args[1:], options.get("cwd"))
        python_prefix = self._python_prefix(args[0]) if program == "python" else ""
        isolated = python_launch_isolated(args[1:]) if program == "python" else False
        return program, python_prefix, isolated

    def _reserved_environment(self, environment, python_prefix) -> None:
        if python_prefix and environment.get("PATH") == os.pathsep.join(
            [str(Path(python_prefix) / "bin"), os.environ.get("PATH", "")]
        ):
            # This is manager bookkeeping, not an executable search grant.
            environment.pop("PATH")
        reserved = {
            name
            for name in environment
            if (name.startswith(("DYLD_", "LD_", "PYTHON")) and name not in {"PYTHONUTF8", "PYTHONPATH"})
            or name in {"PATH", "HOME", "TMPDIR"}
        }
        if any(environment[name] != os.environ.get(name) for name in reserved):
            raise ManagedProcessError("environment override is not admitted")
        for name in reserved:
            environment.pop(name)

    @staticmethod
    def _invalid_environment_item(name, value, build_paths) -> bool:
        return (
            not isinstance(name, str)
            or not isinstance(value, str)
            or "\0" in name + value
            or (
                name.startswith(("DYLD_", "LD_", "PYTHON"))
                and not ((name == "PYTHONUTF8" and value == "1") or (name == "PYTHONPATH" and build_paths))
            )
            or name in {"PATH", "HOME", "TMPDIR"}
        )

    def _launch_environment(self, args, options, selection):
        program, python_prefix, isolated = selection
        inherited_environment = options.get("env")
        environment = dict(os.environ if inherited_environment is None else inherited_environment)
        if program == "uv":
            self._uv_environment(args[0], environment)
            args = self._uv_install_arguments(args, environment)
        elif program == "git":
            self._git_environment(environment)
        if isolated:
            environment.pop("PYTHONPATH", None)
        build_paths = self._build_paths(environment)
        self._reserved_environment(environment, python_prefix)
        if len(environment) > 128 or any(
            self._invalid_environment_item(name, value, build_paths) for name, value in environment.items()
        ):
            raise ManagedProcessError("environment override is not admitted")
        return args, environment, build_paths

    def _launch_python_paths(self, selection, build_paths) -> list[str]:
        program, python_prefix, isolated = selection
        python_paths = [
            str(Path(path).resolve())
            for path in sys.path
            if path
            and Path(path).exists()
            and any(Path(path).resolve().is_relative_to(root) for root in self.roots.values())
        ]
        if isolated or program in {"uv", "git"}:
            python_paths = []
        if python_prefix:
            site = Path(python_prefix) / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
            if site.is_symlink() or site.resolve() != site:
                raise ManagedProcessError("virtual environment site is not canonical")
            python_paths = [str(site)] if site.is_dir() else []
        return list(dict.fromkeys([*build_paths, *python_paths]))

    @beartype
    @require(lambda args: bool(args))
    def popen(self, args: Sequence[str | bytes | os.PathLike[str]], **options: Any) -> ManagedPopen:
        args = self._launch_arguments(args, options)
        selection = self._program_selection(args, options)
        self._validate_stream_options(options)
        program, python_prefix, _isolated = selection
        args, environment, build_paths = self._launch_environment(args, options, selection)
        python_paths = self._launch_python_paths(selection, build_paths)
        request = plistlib.dumps(
            {
                "program": program,
                "argv": list(args[1:]),
                "cwd": self._cwd(options.get("cwd")),
                "environment": environment,
                "stdin_pipe": options.get("stdin") == subprocess.PIPE,
                "merge_stderr": options.get("stderr") == subprocess.STDOUT,
                "python_paths": python_paths,
                "python_prefix": python_prefix,
                "python_alias": (Path(args[0]).name if args[0] not in {"python", "python3"} else args[0])
                if python_prefix
                else "",
            },
            fmt=plistlib.FMT_BINARY,
            sort_keys=True,
        )
        if len(request) > MAX_PAYLOAD:
            raise ManagedProcessError("request exceeds bound")
        return ManagedPopen(self.transport, list(args), request, options)

    def run(
        self,
        args: Sequence[str],
        *,
        input=None,
        capture_output: bool = False,
        timeout: float | None = None,
        check: bool = False,
        **options: Any,
    ):
        if capture_output:
            if "stdout" in options or "stderr" in options:
                raise ValueError("capture_output cannot be combined with stdout/stderr")
            options.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if input is not None:
            if "stdin" in options:
                raise ValueError("input cannot be combined with stdin")
            options["stdin"] = subprocess.PIPE
        with self.popen(args, **options) as process:
            try:
                stdout, stderr = process.communicate(input, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                raise
            assert process.returncode is not None
            result = subprocess.CompletedProcess(
                args,
                process.returncode,
                stdout if process.stdout is not None else None,
                stderr if process.stderr is not None else None,
            )
            if check and result.returncode:
                raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
            return result


@contextmanager
def installed_subprocess(capsule: Path, project: Path, output: Path, temporary: Path):
    """Compatibility only; kernel fork denial remains independently enforced."""
    adapter = ManagedSubprocess(
        NativeWorkerChannel(),
        roots={"project": project, "output": output, "temporary": temporary},
        executables={
            sys.executable: "python",
            str(capsule / "python/bin/python3"): "python",
            "python": "python",
            "python3": "python",
            str(capsule / "tools/uv"): "uv",
            str(capsule / "tools/git"): "git",
            "git": "git",
        },
    )

    class Popen:
        """Retain Popen's runtime generic API while routing creation to the broker."""

        def __new__(cls, args, **options):
            return adapter.popen(args, **options)

        @classmethod
        def __class_getitem__(cls, _item):
            return cls

    original_which = shutil.which

    def which(command, mode=os.F_OK | os.X_OK, path=None):
        if command in {"git", "uv"}:
            try:
                return str(adapter._tool_image(command))
            except ManagedProcessError:
                return None
        if Path(os.fsdecode(command)).name in {"git", "uv"}:
            return None
        return original_which(command, mode=mode, path=path)

    with (
        patch.object(subprocess, "Popen", Popen),
        patch.object(subprocess, "run", adapter.run),
        patch.object(shutil, "which", which),
    ):
        yield adapter
