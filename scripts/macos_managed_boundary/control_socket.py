"""Read-only bounded socket readiness for the native control fixture."""

from __future__ import annotations

import os
import socket
import stat
import time
from pathlib import Path


def _failure(message: str, state: str) -> RuntimeError:
    error = RuntimeError(message)
    error.__dict__["_native_socket_state"] = "private_after_deadline" if state == "private" else state
    return error


def _socket_state(path: Path, uid: int) -> str:
    """Observe a category; binding, owner and mode share one readiness budget."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "socket_missing"
    if not stat.S_ISSOCK(info.st_mode):
        raise _failure("private socket type/owner failed", "socket_type_invalid")
    if info.st_uid != uid:
        return "socket_owner_invalid"  # Never ready; launchd may still be assigning ownership.
    return "private" if stat.S_IMODE(info.st_mode) == 0o600 else "socket_mode_pending"


def wait_socket_ready(path: Path) -> None:
    """Observe binding/private mode within one budget; never retry bootstrap."""
    deadline = time.monotonic() + 3
    uid = os.getuid()
    state = "unobserved"
    while time.monotonic() < deadline:
        state = _private_socket_state(path, uid)
        if state == "private":
            break
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(0.005, remaining))
    else:
        raise _failure("socket readiness deadline exceeded", state)
    if time.monotonic() >= deadline:
        raise _failure("socket readiness deadline exceeded", state)


def _private_socket_state(path: Path, uid: int) -> str:
    directory = path.parent.lstat()
    if not (stat.S_ISDIR(directory.st_mode) and directory.st_uid == uid and stat.S_IMODE(directory.st_mode) == 0o700):
        raise _failure("private directory type/mode/owner failed", "directory_invalid")
    return _socket_state(path, uid)


def connect_private_socket(path: Path) -> socket.socket:
    """Wait for one listener within the original seven-second connect budget."""
    deadline = time.monotonic() + 7
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("private socket connection budget exceeded")
        state = _private_socket_state(path, os.getuid())
        if state != "private":
            raise _failure("private socket changed before connection", state)
        stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("private socket connection budget exceeded")
            stream.settimeout(remaining)
            stream.connect(str(path))
            if time.monotonic() >= deadline:
                raise TimeoutError("private socket connection budget exceeded")
            return stream
        except ConnectionRefusedError:
            stream.close()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            time.sleep(min(0.005, remaining))
        except BaseException:
            stream.close()
            raise
