"""Bounded trusted-host supervision for supplementary diagnostics only."""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any


def _linux_descendants(parent: int) -> tuple[dict[int, str], bool]:
    """Observe only descendants of the still-owned unreaped child on Linux."""
    import sys

    if sys.platform != "linux":
        return {}, False
    table = {}
    deadline = time.monotonic() + 2
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        if len(table) >= 16384 or time.monotonic() >= deadline:
            raise ValueError("process_observation_incomplete")
        try:
            with (entry / "stat").open("rb") as stream:
                fields = stream.read(4096).rsplit(b")", 1)[1].split()
            table[int(entry.name)] = (int(fields[1]), fields[19].decode())
        except FileNotFoundError:
            continue
    owned = {parent}
    while True:
        additional = {pid for pid, (ppid, _) in table.items() if ppid in owned} - owned
        if not additional:
            break
        owned.update(additional)
    descendants = {pid: table[pid][1] for pid in owned - {parent} if pid in table}
    capsule = False
    for pid in descendants:
        try:
            with (Path("/proc") / str(pid) / "cmdline").open("rb") as stream:
                argv = stream.read(4096).split(b"\0")
            capsule = capsule or (b"--die-with-parent" in argv and b"--new-session" in argv)
        except FileNotFoundError:
            pass
    return descendants, capsule


def _descendants_gone(descendants: dict[int, str]) -> bool:
    for pid, start in descendants.items():
        try:
            with (Path("/proc") / str(pid) / "stat").open("rb") as stream:
                fields = stream.read(4096).rsplit(b")", 1)[1].split()
            if fields[19].decode() == start and fields[0] != b"Z":
                return False
        except FileNotFoundError:
            pass
        except (OSError, ValueError, IndexError):
            return False
    return True


def _wait_owned(child: subprocess.Popen[bytes], timeout: float) -> int:
    deadline = time.monotonic() + timeout
    while True:
        state = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG)
        if state is not None and state.si_pid == child.pid:
            return state.si_status if state.si_code == os.CLD_EXITED else -state.si_status
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(child.args, timeout)
        time.sleep(min(0.02, max(0, deadline - time.monotonic())))


def _signal_owned(pid: int, sig: int, deadline: float) -> None:
    import sys
    import tempfile

    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except PermissionError:
        if sys.platform != "darwin":
            raise
        # Darwin denies signals to groups containing only unreaped zombies.
        with tempfile.TemporaryFile() as output:
            result = subprocess.run(
                ["/bin/ps", "-g", str(pid), "-o", "stat="],
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=max(0.001, min(2, deadline - time.monotonic())),
                check=False,
            )
            output.seek(0)
            states = output.read(4097)
        if (
            result.returncode != 0
            or len(states) > 4096
            or not states.split()
            or not all(state.startswith(b"Z") for state in states.split())
        ):
            raise


def _terminate_owned(child: subprocess.Popen[bytes], descendants: dict[int, str]) -> str:
    """Keep the owned PID unreaped until group signaling; share one ten-second cap."""
    if child.pid == os.getpgrp():
        return "incomplete"
    deadline = time.monotonic() + 10
    _signal_owned(child.pid, signal.SIGTERM, deadline)
    with contextlib.suppress(subprocess.TimeoutExpired):
        _wait_owned(child, min(5, max(0.001, deadline - time.monotonic())))
    _signal_owned(child.pid, signal.SIGKILL, deadline)
    try:
        child.wait(timeout=max(0.001, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        return "incomplete"
    while not _descendants_gone(descendants):
        if time.monotonic() >= deadline:
            return "incomplete"
        time.sleep(0.02)
    return "complete"


def supervise(command: list[str], directory: Path, binding: dict[str, str], *, timeout: float = 600) -> int:
    from specfact_code_review.run import supplemental_diagnostics as diagnostic

    binding = diagnostic.validate_binding(binding)
    if not 0 < timeout <= 600:
        raise ValueError("supervisor_deadline")
    started = time.monotonic()
    terminal: dict[str, Any] = {
        "schema": "supplemental-host-terminal-v1",
        "purpose": "SUPPLEMENTARY_DIAGNOSTIC_ONLY",
        "binding": binding,
        "category": "supervisor_error",
        "child_returncode": None,
        "elapsed_ms": 0,
        "cleanup": "pending",
        "capsule_process_observed": "UNAVAILABLE",
    }
    child = None
    descendants: dict[int, str] = {}
    code = 1
    inventory_complete = True
    try:
        child = subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL)
        try:
            code = _wait_owned(child, timeout)
            terminal.update(category="signal_termination" if code < 0 else "child_exit", child_returncode=code)
        except subprocess.TimeoutExpired:
            code = 124
            terminal["category"] = "wrapper_expired"
            terminal["elapsed_ms"] = int((time.monotonic() - started) * 1000)
            diagnostic.atomic_record(directory, "terminal.json", terminal, diagnostic.TERMINAL_LIMIT)
            try:
                descendants, terminal["capsule_process_observed"] = _linux_descendants(child.pid)
            except (OSError, ValueError, IndexError):
                inventory_complete = False
        terminal["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        diagnostic.atomic_record(directory, "terminal.json", terminal, diagnostic.TERMINAL_LIMIT)
    finally:
        terminal["cleanup"] = "complete" if child is None else _terminate_owned(child, descendants)
        if not inventory_complete:
            terminal["cleanup"] = "incomplete"
        terminal["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        diagnostic.atomic_record(directory, "terminal.json", terminal, diagnostic.TERMINAL_LIMIT)
    return code if code >= 0 and terminal["cleanup"] == "complete" else 1


def main() -> int:
    from specfact_cli.registry import CommandRegistry

    CommandRegistry.get_module_typer("code")
    from specfact_code_review.run import supplemental_diagnostics as diagnostic

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    binding = diagnostic.read_record(args.directory, "binding.json", diagnostic.TERMINAL_LIMIT)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("supervisor_command_missing")
    try:
        return supervise(command, args.directory, binding, timeout=args.timeout)
    finally:
        summary = diagnostic.collect_host_summary(args.directory, binding)
        diagnostic.atomic_record(args.directory, "diagnostic-summary.json", summary, diagnostic.MAX_BYTES)


if __name__ == "__main__":
    raise SystemExit(main())
