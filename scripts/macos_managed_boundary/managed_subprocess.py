"""Narrow managed run compatibility; never create a host subprocess.

The transport resolves exact requests to prebound native broker plans. Shells,
ambient executables, arbitrary environment and descriptor inheritance fail closed.
This is not a security boundary: direct syscalls remain kernel-confined.
"""

from __future__ import annotations

import errno
import subprocess
from collections.abc import Callable, Mapping, Sequence
from typing import Any


MAX_OUTPUT = 4 * 1024 * 1024


class UnadaptedProcessError(OSError):
    """Actionable incomplete evidence for unsupported process semantics."""

    def __init__(self, reason: str):
        super().__init__(errno.ENOTSUP, f"managed subprocess incomplete: {reason}; no host fallback")


class ManagedRun:
    """Translate a bounded run call to a verified owned-worker response."""

    def __init__(
        self,
        executables: Mapping[str, str],
        transport: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        cwd: str,
        environment: Mapping[str, str] | None = None,
    ):
        self.executables = dict(executables)
        self.transport = transport
        self.cwd = cwd
        self.environment = dict(environment or {})

    def run(self, args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if (
            isinstance(args, str)
            or not args
            or len(args) > 128
            or any(not isinstance(arg, str) or "\0" in arg or len(arg) > 65536 for arg in args)
        ):
            raise UnadaptedProcessError("invalid argv")
        if args[0] not in self.executables:
            raise UnadaptedProcessError("unbound executable")
        allowed = {"capture_output", "text", "check", "timeout", "cwd", "env", "encoding", "errors"}
        if (
            set(kwargs) - allowed
            or kwargs.get("text", True) is not True
            or kwargs.get("capture_output", True) is not True
        ):
            raise UnadaptedProcessError("unsupported shell, stream, descriptor or preexec options")
        if kwargs.get("cwd", self.cwd) != self.cwd:
            raise UnadaptedProcessError("unbound cwd")
        if kwargs.get("env", self.environment) != self.environment:
            raise UnadaptedProcessError("unbound environment")
        if kwargs.get("encoding", "utf-8") != "utf-8" or kwargs.get("errors", "strict") != "strict":
            raise UnadaptedProcessError("unsupported output decoding")
        timeout = kwargs.get("timeout", 5)
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 240:
            raise UnadaptedProcessError("invalid timeout")
        request = {"tool": self.executables[args[0]], "argv": list(args), "cwd": self.cwd}
        response = self.transport(request)
        if response.get("broker_verified") is not True or type(response.get("returncode")) is not int:
            raise UnadaptedProcessError("unverified broker result")
        if any(
            not isinstance(response.get(field), str) or len(response[field].encode()) > MAX_OUTPUT
            for field in ("stdout", "stderr")
        ):
            raise UnadaptedProcessError("invalid or oversized broker output")
        result = subprocess.CompletedProcess(list(args), response["returncode"], response["stdout"], response["stderr"])
        if kwargs.get("check", False) and result.returncode:
            raise subprocess.CalledProcessError(result.returncode, list(args), result.stdout, result.stderr)
        return result

    @staticmethod
    def popen(*_args: Any, **_kwargs: Any) -> None:
        raise UnadaptedProcessError("Popen streaming/async adapter not admitted")
