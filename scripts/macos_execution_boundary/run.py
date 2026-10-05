"""Observe a bounded native XPC candidate; any survivor rejects admission."""

from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
import platform
import signal
import subprocess
import time
from contextlib import suppress
from pathlib import Path
from typing import Any


SOURCE = Path(__file__).resolve().parent
MODES = ("normal", "child", "fork-detach", "double-fork", "spawn-detach", "vfork-detach")
ACTIONS = ("cancel", "timeout", "client-death", "service-death")


def case_passed(case: dict[str, Any]) -> bool:
    """Reject startup failure, live descendants and observer rescue."""
    return case.get("ready") is True and case.get("survivors") == [] and case.get("emergency_cleanup") is False


def build_module() -> Any:
    """Load the sibling builder without modifying the import search path."""
    spec = importlib.util.spec_from_file_location("boundary_build", SOURCE / "build.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_path(pid: int) -> str:
    """Read kernel executable identity independently of fixture reporting."""
    library = ctypes.CDLL("/usr/lib/libproc.dylib")
    buffer = ctypes.create_string_buffer(4096)
    count = library.proc_pidpath(pid, buffer, len(buffer))
    return os.fsdecode(buffer.value) if count > 0 else ""


def identity(observer: Path, pid: int) -> dict[str, Any] | None:
    """Read PID birth identity through a native libproc observer."""
    result = subprocess.run([str(observer), str(pid)], capture_output=True, text=True, timeout=2, check=False)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise RuntimeError(f"observer failed for PID {pid}: exit {result.returncode}")
    value = json.loads(result.stdout)
    try:
        value["sid"] = os.getsid(pid)
    except ProcessLookupError:
        return None
    return value


def same_process(observer: Path, recorded: dict[str, Any]) -> bool:
    """Avoid treating reused PIDs or reaped processes as fixture survivors."""
    current = identity(observer, recorded["pid"])
    return current is not None and all(current[key] == recorded[key] for key in ("pid", "start_sec", "start_usec"))


def events(log: Path) -> list[dict[str, Any]]:
    """Read complete JSON events; partial lines are not readiness evidence."""
    rows = []
    for line in log.read_text(errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def discover(observer: Path, app: Path, log: Path, known: dict[int, dict[str, Any]]) -> None:
    """Corroborate reported fixture PIDs with independent executable/birth identity."""
    for row in events(log):
        for key in ("pid", "root_pid", "service_pid", "worker_pid"):
            pid = row.get(key)
            if not isinstance(pid, int) or pid <= 1 or pid in known:
                continue
            executable = process_path(pid)
            if not executable.startswith(str(app) + "/"):
                continue
            observed = identity(observer, pid)
            if observed:
                known[pid] = {**observed, "executable": executable}


def census(observer: Path, app: Path, known: dict[int, dict[str, Any]]) -> None:
    """Find unreported bounded fixture descendants through the host process table."""
    result = subprocess.run(["/bin/ps", "-axo", "pid="], capture_output=True, text=True, timeout=3, check=True)
    for value in result.stdout.split():
        pid = int(value)
        executable = process_path(pid)
        if pid in known or not executable.startswith(str(app) + "/"):
            continue
        observed = identity(observer, pid)
        if observed:
            known[pid] = {**observed, "executable": executable}


def fixtures_ready(rows: list[dict[str, Any]], known: dict[int, dict[str, Any]], mode: str) -> bool:
    """Require independently observed ready root and final child, without fixture errors."""
    if any(row.get("event") == "error" for row in rows):
        return False
    ready = {
        row.get("role"): row
        for row in rows
        if row.get("event") == "ready" and row.get("errno") == 0 and row.get("pid") in known
    }
    if "root" not in ready or (mode != "normal" and "child" not in ready):
        return False
    if mode not in ("normal", "child"):
        child = ready["child"]
        observed = known[child["pid"]]
        return child.get("sid") == observed.get("sid") and child.get("sid") != ready["root"].get("sid")
    return True


def completion_ok(rows: list[dict[str, Any]], action: str, returncode: int | None) -> bool:
    """Require successful native completion except for deliberately killed peers."""
    if action in ("client-death", "service-death"):
        return returncode is not None
    reason = {"hold": "exit", "cancel": "cancel", "timeout": "timeout"}[action]
    return returncode == 0 and any(
        row.get("event") == "receipt"
        and row.get("reason") == reason
        and row.get("ok") is True
        and row.get("root_reaped") is True
        for row in rows
    )


def signal_exact(observer: Path, row: dict[str, Any]) -> None:
    """Signal only a still-matching benign test process, never a broad PID group."""
    if same_process(observer, row) and process_path(row["pid"]) == row["executable"]:
        with suppress(ProcessLookupError):
            os.kill(row["pid"], signal.SIGKILL)


def wait_for_readiness(
    app: Path,
    observer: Path,
    log: Path,
    known: dict[int, dict[str, Any]],
    client: subprocess.Popen,
    row: dict[str, Any],
) -> None:
    """Poll fixture readiness and corroborate live identities for up to five seconds."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        discover(observer, app, log, known)
        if fixtures_ready(events(log), known, row["mode"]):
            row["ready"] = all(
                same_process(observer, item) for item in known.values() if item["executable"].endswith("/fixture")
            )
            if row["ready"]:
                break
        if client.poll() is not None:
            break
        time.sleep(0.02)


def inject_fault(
    observer: Path, known: dict[int, dict[str, Any]], client: subprocess.Popen, row: dict[str, Any]
) -> None:
    """Inject the selected peer death only after readiness is established."""
    if row["ready"] and row["action"] == "client-death":
        client.kill()
    if row["ready"] and row["action"] == "service-death":
        service = [item for item in known.values() if item["executable"].endswith("/Runner")]
        if len(service) != 1:
            row["ready"] = False
        else:
            signal_exact(observer, service[0])


def observe_completion(
    app: Path,
    observer: Path,
    log: Path,
    known: dict[int, dict[str, Any]],
    client: subprocess.Popen,
    row: dict[str, Any],
    start: float,
) -> None:
    """Record independent worker survival and client completion after the observation window."""
    while time.monotonic() - start < 5:
        discover(observer, app, log, known)
        time.sleep(0.05)
    census(observer, app, known)
    workers = [item for item in known.values() if item["executable"].endswith("/fixture")]
    row["survivors"] = [item["pid"] for item in workers if same_process(observer, item)]
    row["observation_seconds"] = time.monotonic() - start
    row["processes"] = list(known.values())
    row["events"] = events(log)
    row["client_returncode"] = client.poll()
    row["completion_ok"] = completion_ok(row["events"], row["action"], row["client_returncode"])


def cleanup_case(
    observer: Path, known: dict[int, dict[str, Any]], client: subprocess.Popen, row: dict[str, Any]
) -> None:
    """Rescue remaining processes while retaining observer failures and client rescue evidence."""
    row["emergency_cleanup"] = bool(row["survivors"]) or client.poll() is None or "observer_error" in row
    for item in known.values():
        try:
            signal_exact(observer, item)
        except RuntimeError as error:
            row["observer_error"] = str(error)
            row["emergency_cleanup"] = True
    if client.poll() is None:
        client.kill()
    client.wait(timeout=3)
    time.sleep(0.1)
    try:
        row["cleanup_remaining"] = [pid for pid, item in known.items() if same_process(observer, item)]
    except RuntimeError as error:
        row["observer_error"] = str(error)
        row["cleanup_remaining"] = list(known)


def run_case(app: Path, observer: Path, destination: Path, mode: str, action: str) -> dict[str, Any]:
    """Inject a lifecycle fault and measure five-second cleanup independently."""
    destination.mkdir()
    log = destination / "events.jsonl"
    known: dict[int, dict[str, Any]] = {}
    row: dict[str, Any] = {"mode": mode, "action": action, "ready": False, "survivors": [], "emergency_cleanup": False}
    client_action = action if action in ("cancel", "timeout") else "hold"
    with log.open("w") as output:
        client = subprocess.Popen(
            [str(app / "Contents/MacOS/BoundaryClient"), str(destination), mode, client_action],
            stdout=output,
            stderr=output,
            env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "TMPDIR": str(destination)},
        )
        try:
            wait_for_readiness(app, observer, log, known, client, row)
            start = time.monotonic()
            inject_fault(observer, known, client, row)
            observe_completion(app, observer, log, known, client, row, start)
        except (RuntimeError, OSError, subprocess.SubprocessError) as error:
            row["observer_error"] = str(error)
            row["ready"] = False
        finally:
            cleanup_case(observer, known, client, row)
    row["passed"] = case_passed(row) and not row["cleanup_remaining"] and row.get("completion_ok") is True
    return row


def parse_arguments() -> argparse.Namespace:
    """Parse the existing command-line interface for the native experiment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repetitions", type=int, choices=range(1, 101), default=1)
    parser.add_argument("--unsandboxed-control", action="store_true")
    parser.add_argument("--diagnose", action="store_true", help="Run each case once even after rejection; never admit")
    return parser.parse_args()


def write_report(root: Path, report: dict[str, Any]) -> None:
    """Persist the current experiment evidence using the existing JSON format."""
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def initial_report(args: argparse.Namespace, root: Path, builder: Any) -> dict[str, Any]:
    """Record build identities and explicitly retain experimental-only eligibility."""
    return {
        "schema_version": 1,
        "experimental": True,
        "production_eligible": False,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "signing": "ad-hoc",
        "repetitions_requested": args.repetitions,
        "sandbox": not args.unsandboxed_control,
        "identities": builder.identities(root),
        "cases": [],
        "status": "INCOMPLETE",
    }


def run_matrix(app: Path, root: Path, args: argparse.Namespace, report: dict[str, Any]) -> bool:
    """Record each lifecycle case and return whether the matrix encountered a failure."""
    matrix = [("normal", "hold"), ("child", "cancel")] + [(mode, action) for mode in MODES[2:] for action in ACTIONS]
    failed = False
    for iteration in range(1 if args.diagnose else args.repetitions):
        for mode, action in matrix:
            row = run_case(app, root / "observe", root / f"case-{iteration}-{mode}-{action}", mode, action)
            report["cases"].append(row)
            failed = failed or not row["passed"]
            report["status"] = "CANDIDATE_REJECTED" if failed else "INCOMPLETE"
            write_report(root, report)
            print(
                json.dumps({"mode": mode, "action": action, "passed": row["passed"], "survivors": row["survivors"]}),
                flush=True,
            )
            if not row["passed"] and not args.diagnose:
                return True
    return failed


def main() -> int:
    """Build and exercise a candidate, stopping at the first failed gate."""
    args = parse_arguments()
    root = args.output.resolve()
    builder = build_module()
    app = builder.build(root, not args.unsandboxed_control)
    report = initial_report(args, root, builder)
    if run_matrix(app, root, args, report):
        return 1
    report["status"] = "MECHANISM_REVIEW_REQUIRED" if args.repetitions == 100 and not args.diagnose else "INCOMPLETE"
    write_report(root, report)
    return 0 if args.repetitions == 100 and not args.diagnose else 2


if __name__ == "__main__":
    raise SystemExit(main())
