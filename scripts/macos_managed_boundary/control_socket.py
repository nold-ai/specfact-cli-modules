"""Read-only bounded socket readiness for the native control fixture."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path


def _failure(message: str, state: str) -> RuntimeError:
    error = RuntimeError(message)
    error.__dict__["_native_socket_state"] = "private_after_deadline" if state == "private" else state
    return error


def _socket_state(path: Path, uid: int) -> str:
    """Observe only a category; absence and pending mode share the same budget."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "socket_missing"
    if not stat.S_ISSOCK(info.st_mode):
        raise _failure("private socket type/owner failed", "socket_type_invalid")
    if info.st_uid != uid:
        raise _failure("private socket type/owner failed", "socket_owner_invalid")
    return "private" if stat.S_IMODE(info.st_mode) == 0o600 else "socket_mode_pending"


def wait_socket_ready(path: Path) -> None:
    """Observe binding/private mode within one budget; never retry bootstrap."""
    deadline = time.monotonic() + 3
    uid = os.getuid()
    state = "unobserved"
    while time.monotonic() < deadline:
        directory = path.parent.lstat()
        if not (
            stat.S_ISDIR(directory.st_mode) and directory.st_uid == uid and stat.S_IMODE(directory.st_mode) == 0o700
        ):
            raise _failure("private directory type/mode/owner failed", "directory_invalid")
        state = _socket_state(path, uid)
        if state == "private":
            break
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(0.005, remaining))
    else:
        raise _failure("socket readiness deadline exceeded", state)
    if time.monotonic() >= deadline:
        raise _failure("socket readiness deadline exceeded", state)
