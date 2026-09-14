"""Launch target imports with no access to the sealed parent's writable results."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT = Path("/opt/specfact/project-runtime")


def interpreter_command(arguments: list[str]) -> list[str]:
    """Enter the target native loader domain while keeping the signed Python binary."""
    python = "/opt/specfact/python/bin/python"
    loader = PROJECT / "native/ld-linux-x86-64.so.2"
    if loader.is_file():
        return [str(loader), "--library-path", str(loader.parent), python, *arguments]
    return [python, *arguments]


def target_command(module: str, arguments: list[str]) -> list[str]:
    """Separate PID/mount/network domains before any customer Python executes."""
    return [
        "/opt/specfact/bin/bwrap-static",
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/opt/specfact/output",
        "--tmpfs",
        "/opt/specfact/config",
        "--tmpfs",
        "/opt/specfact/control",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        "/opt/specfact/project-runtime/worker-config",
        "/etc",
        "--bind",
        "/opt/specfact/tmp",
        "/opt/specfact/tmp",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--clearenv",
        "--setenv",
        "HOME",
        "/opt/specfact/tmp/home",
        "--setenv",
        "TMPDIR",
        "/opt/specfact/tmp",
        "--setenv",
        "PATH",
        "/opt/specfact/project-runtime/bin:/opt/specfact/python/bin:/opt/specfact/analyzers/bin",
        "--chdir",
        "/opt/specfact/snapshot",
        *interpreter_command(
            ["-I", "-S", "/opt/specfact/builtin/specfact_code_review/run/target_bootstrap.py", module, *arguments]
        ),
    ]


def main() -> None:
    command = target_command("python-argv", sys.argv[1:])
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
