"""Read-only bounded socket readiness for the native control fixture."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path


def _socket_is_private(path: Path, uid: int) -> bool:
    """Observe the socket itself; absent paths may bind within the same budget."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != uid:
        raise RuntimeError("private socket type/owner failed")
    return stat.S_IMODE(info.st_mode) == 0o600


def wait_socket_ready(path: Path) -> None:
    """Observe binding/private mode within one budget; never retry bootstrap."""
    deadline = time.monotonic() + 3
    uid = os.getuid()
    while time.monotonic() < deadline:
        directory = path.parent.lstat()
        if not (
            stat.S_ISDIR(directory.st_mode) and directory.st_uid == uid and stat.S_IMODE(directory.st_mode) == 0o700
        ):
            raise RuntimeError("private directory type/mode/owner failed")
        if _socket_is_private(path, uid):
            break
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(0.005, remaining))
    else:
        raise RuntimeError("socket readiness deadline exceeded")
    if time.monotonic() >= deadline:
        raise RuntimeError("socket readiness deadline exceeded")
