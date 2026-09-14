"""Launch target imports with no access to the sealed parent's writable results."""

from __future__ import annotations

import os
import sys


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
        "--setenv",
        "LD_LIBRARY_PATH",
        "/opt/specfact/project-runtime/native",
        "--chdir",
        "/opt/specfact/snapshot",
        "/opt/specfact/python/bin/python",
        "-I",
        "-S",
        "/opt/specfact/builtin/specfact_code_review/run/target_bootstrap.py",
        module,
        *arguments,
    ]


def main() -> None:
    command = target_command("python-argv", sys.argv[1:])
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
