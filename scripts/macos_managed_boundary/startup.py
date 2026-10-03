"""Bounded native launchd startup experiment; never a production admission API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import plistlib
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, NamedTuple


CLEANUP_SECONDS = 5.0
RACE_MODES = ("suspended", "pretrace", "trace-stopped", "traced", "exec", "confined")


class NativeBinaries(NamedTuple):
    """Fixed broker, bootstrap and independent observer paths."""

    broker: Path
    worker: Path
    observer: Path


class BootstrapInputs(NamedTuple):
    """The fixed executable paths and the single exercised policy snapshot."""

    broker: Path
    worker: Path
    profile: str


class StartupPhase(NamedTuple):
    """The target transition and the exact observed event bytes."""

    mode: str
    content: str = ""


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run fixed maintainer tools with bounded output capture."""
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=10)


def job_config(
    label: str, bootstrap: BootstrapInputs, directory: Path, abandon: bool, mode: str = "suspended"
) -> dict[str, Any]:
    """Define an invocation job without restart or installed LaunchAgent."""
    return {
        "Label": label,
        "ProgramArguments": [
            str(bootstrap.broker),
            str(bootstrap.worker),
            mode,
            bootstrap.profile,
        ],
        "RunAtLoad": True,
        "KeepAlive": False,
        "LaunchOnlyOnce": True,
        "AbandonProcessGroup": abandon,
        "ExitTimeOut": 1,
        "StandardOutPath": str(directory / "events"),
        "StandardErrorPath": str(directory / "errors"),
        "WorkingDirectory": str(directory),
        "EnvironmentVariables": {"PATH": "/usr/bin:/bin", "LANG": "C"},
    }


def validate_tracing(mode: str, identity: dict[str, Any]) -> None:
    """Kernel observation must match the promised startup transition."""
    traced = bool(identity["flags"] & 2)
    expected = mode in ("trace-stopped", "traced", "exec", "confined")
    if traced != expected:
        raise ValueError("unexpected kernel tracing state")


def same_birth_identity(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    """A reused PID is never the original fixture and cannot be signalled."""
    fields = ("pid", "start_sec", "start_usec")
    if any(field not in item for item in (expected, observed) for field in fields):
        raise ValueError("incomplete fixture birth identity")
    return all(expected[field] == observed[field] for field in fields)


def observe(observer: Path, pid: int) -> dict[str, Any] | None:
    """Use a separate native libproc process; errors cannot become absence."""
    result = command([str(observer), str(pid)], check=False)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise RuntimeError(f"independent observer failed: {result.returncode}")
    return json.loads(result.stdout)


def alive(observer: Path, identity: dict[str, Any]) -> bool:
    """Poll for observation only, never for worker containment."""
    current = observe(observer, identity["pid"])
    return current is not None and same_birth_identity(identity, current)


def signal_fixture(observer: Path, identity: dict[str, Any]) -> tuple[float, float] | None:
    """Signal a real audit token atomically bound by the kernel to its pid version."""
    token = identity.get("audit_token")
    if not isinstance(token, list) or len(token) != 8 or token[5] != identity.get("pid"):
        raise ValueError("missing or inconsistent fixture audit token")
    result = command([str(observer), "--signal", *map(str, token)], check=False)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise RuntimeError("kernel audit-token fixture signaling failed")
    issued = json.loads(result.stdout)
    return issued["before_ns"] / 1_000_000_000, issued["after_ns"] / 1_000_000_000


def verify_signal_binding(observer: Path, identity: dict[str, Any]) -> None:
    """A stale pid version must reject signaling while the original fixture survives."""
    token = list(identity["audit_token"])
    token[7] = (token[7] + 1) % (2**32)
    result = command([str(observer), "--signal", *map(str, token)], check=False)
    if result.returncode != 1 or not alive(observer, identity):
        raise RuntimeError("kernel did not reject stale fixture audit token")


def validate_fallback(content: str, started: float) -> None:
    """Never attribute a possible fixture alarm death to the execution boundary."""
    deadlines = [
        int(line.partition("=")[2]) / 1_000_000_000
        for line in content.splitlines()
        if line.startswith("fallback-deadline=")
    ]
    if deadlines and min(deadlines) - started <= CLEANUP_SECONDS:
        raise RuntimeError("fixture fallback overlaps the measured cleanup window")


def event_ready(mode: str, content: str) -> bool:
    """A complete broker record is distinct from worker-first output."""
    if mode == "runtime-trap":
        return "worker-signal=" in content or "worker-exit=" in content
    if mode == "identity":
        return any(line.startswith('{"broker":') and line.endswith("}") for line in content.splitlines())
    markers = {
        "normal": "worker-exit=37",
        "probe-control": "worker-exit=37",
        "raw-vfork-control": "worker-signal=12",
        "suspended": "\n",
        "trace-stopped": "trace-confirmed:trace-stopped",
    }
    return markers.get(mode, f"ready:{mode}") in content


def fixture_failed(mode: str, content: str) -> bool:
    """Unexpected signal/exit never establishes successful confinement."""
    if mode in ("raw-vfork-control", "runtime-trap"):
        return False
    return "worker-signal=" in content or ("worker-exit=" in content and "worker-exit=37" not in content)


def wait_events(path: Path, mode: str) -> str:
    """Bound startup waiting; a failed launch is never cleanup evidence."""
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if path.is_file():
            content = path.read_text()
            if fixture_failed(mode, content):
                raise RuntimeError(f"fixture failed: {content[-1000:]}")
            if event_ready(mode, content):
                return content
        time.sleep(0.02)
    raise RuntimeError("fixture startup did not complete")


def create_job(bootstrap: BootstrapInputs, directory: Path, abandon: bool, mode: str) -> tuple[str, Path]:
    """Create private invocation inputs, without installing a LaunchAgent."""
    directory.mkdir(mode=0o700)
    (directory / "allowed").write_text("A")
    (directory / "forbidden").write_text("F")
    label = f"io.specfact.proof.{uuid.uuid4().hex}"
    domain = f"gui/{os.getuid()}"
    service = f"{domain}/{label}"
    plist = directory / "job.plist"
    plist.write_bytes(plistlib.dumps(job_config(label, bootstrap, directory, abandon, mode)))
    plist.chmod(0o600)
    return service, plist


def completed_control(mode: str, content: str) -> dict[str, Any] | None:
    """A failed positive control or unavailable syscall is not sandbox proof."""
    if mode == "raw-vfork-control":
        return {
            "mode": mode,
            "kernel_unsupported_sigsys": "worker-signal=12" in content,
            "sandbox_denial_proven": False,
        }
    if mode == "runtime-trap":
        return {"mode": mode, "passed": "worker-signal=5" in content and "runtime-trap-was-suppressed" not in content}
    markers = {"normal": "managed-fixture-output", "probe-control": "positive-probes-ok"}
    if mode in markers:
        return {"mode": mode, "passed": markers[mode] in content and "worker-exit=37" in content}
    return None


def capture_identity(observer: Path, event: dict[str, Any], identities: list[dict[str, Any]]) -> None:
    """Retain each fixture identity for cleanup even if later startup fails."""
    for role in ("broker", "worker"):
        identity = observe(observer, event[role])
        if identity is None:
            raise RuntimeError(f"{role} disappeared before independent identity capture")
        identities.append(identity)


def phase_identity(observer: Path, identities: list[dict[str, Any]], content: str, mode: str) -> dict[str, Any]:
    """Independently verify birth, parent, tracing and the expected group transition."""
    broker_id, worker_id = identities
    current = observe(observer, worker_id["pid"])
    if current is None or not same_birth_identity(worker_id, current):
        raise RuntimeError("fixture changed identity before target transition")
    validate_tracing(mode, current)
    if mode == "confined" and "confinement-probes-ok" not in content:
        raise RuntimeError("confinement probes did not pass")
    if current["ppid"] != broker_id["pid"]:
        raise RuntimeError("fixture was not a direct broker child")
    expected_group = current["pid"] if mode in ("traced", "exec", "confined") else broker_id["pgid"]
    if current["pgid"] != expected_group:
        raise RuntimeError("unexpected fixture process group")
    if mode == "suspended" and current["status"] != 4:
        raise RuntimeError("pre-trace fixture is not suspended")
    return current


def job_absent(service: str) -> bool:
    """Distinguish service absence from a failed launchd inspection."""
    result = command(["/bin/launchctl", "print", service], check=False)
    if result.returncode == 0:
        return False
    if result.returncode == 113 and "Could not find service" in result.stderr:
        return True
    raise RuntimeError("unable to independently inspect job removal")


def wait_job_absent(service: str, deadline: float) -> bool:
    """Observe automatic job removal within the remaining cleanup deadline."""
    while time.monotonic() < deadline:
        if job_absent(service):
            return time.monotonic() <= deadline
        time.sleep(0.02)
    return False


def observe_cleanup(
    observer: Path, identities: list[dict[str, Any]], service: str, abandon: bool, phase: StartupPhase
) -> dict[str, Any]:
    """No harness-assisted cleanup is permitted inside the measured death window."""
    mode, content = phase
    broker_id, worker_id = identities
    issued = signal_fixture(observer, broker_id)
    if issued is None:
        raise RuntimeError("broker exited before injected death")
    before, after = issued
    validate_fallback(content, after)
    started = after if abandon else before
    deadline = started + CLEANUP_SECONDS
    job_removed = wait_job_absent(service, deadline)
    while time.monotonic() < deadline:
        if not alive(observer, worker_id) and not abandon:
            break
        time.sleep(0.02)
    survived = alive(observer, worker_id)
    observed_seconds = time.monotonic() - started
    return {
        "job_removed_after_broker_exit": job_removed,
        "mode": mode,
        "abandon_process_group": abandon,
        "survived": survived,
        "passed": job_removed and (survived if abandon else not survived and observed_seconds <= CLEANUP_SECONDS),
        "observation_seconds": round(observed_seconds, 4),
        "worker_identity": worker_id,
    }


def remove_job(observer: Path, identities: list[dict[str, Any]], service: str) -> None:
    """Remove once; observe asynchronous teardown within the original bound."""
    deadline = time.monotonic() + CLEANUP_SECONDS
    try:
        for identity in reversed(identities):
            signal_fixture(observer, identity)
    finally:
        command(["/bin/launchctl", "bootout", service], check=False)
        if not wait_job_absent(service, deadline):
            raise RuntimeError("invocation job removal could not be verified")


def trial(binaries: NativeBinaries, directory: Path, abandon: bool, mode: str, profile: str) -> dict[str, Any]:
    """Prove one fixed startup stage with independently captured worker identity."""
    broker, worker, observer = binaries
    service, plist = create_job(BootstrapInputs(broker, worker, profile), directory, abandon, mode)
    identities: list[dict[str, Any]] = []
    try:
        command(["/bin/launchctl", "bootstrap", service.rsplit("/", 1)[0], str(plist)])
        control_mode = mode in ("normal", "probe-control", "raw-vfork-control", "runtime-trap")
        content = wait_events(directory / "events", mode if control_mode else "identity")
        control = completed_control(mode, content)
        if control is not None:
            return control
        event = json.loads(next(line for line in content.splitlines() if line.startswith("{")))
        capture_identity(observer, event, identities)
        content = wait_events(directory / "events", mode)
        identities[1] = phase_identity(observer, identities, content, mode)
        verify_signal_binding(observer, identities[0])
        verify_signal_binding(observer, identities[1])
        return observe_cleanup(observer, identities, service, abandon, StartupPhase(mode, content))
    finally:
        remove_job(observer, identities, service)


def _compile_fixture(source: Path, target: Path) -> None:
    """Compile only an ARM64 private source snapshot with strict diagnostics."""
    command(
        [
            "/usr/bin/xcrun",
            "clang",
            "-arch",
            "arm64",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
            "-o",
            str(target),
        ]
    )


def _sign_fixture(target: Path) -> str:
    """Require the initial ad-hoc/hardened signing configuration."""
    command(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)])
    command(["/usr/bin/codesign", "--verify", "--strict", str(target)])
    details = command(["/usr/bin/codesign", "--display", "--verbose=4", str(target)]).stderr
    if "flags=0x10002(adhoc,runtime)" not in details or "Signature=adhoc" not in details:
        raise RuntimeError("unexpected initial-distribution signing configuration")
    return details


def build(directory: Path) -> tuple[Path, Path, Path, list[dict[str, Any]]]:
    """Build only fixed checked-in fixtures; customers need no compiler."""
    source = Path(__file__).resolve().parent
    inputs = {
        "broker": source / "startup_broker.c",
        "worker": source / "startup_worker.c",
        "observer": source / "startup_observe.c",
    }
    inventory = []
    for name, code in inputs.items():
        target = directory / name
        snapshot = code.read_bytes()
        compiled_source = directory / f"source-{name}.c"
        compiled_source.write_bytes(snapshot)
        compiled_source.chmod(0o444)
        _compile_fixture(compiled_source, target)
        details = _sign_fixture(target)
        inventory.append(
            {
                "source_sha256": hashlib.sha256(snapshot).hexdigest(),
                "name": name,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "signing": details,
            }
        )
    return directory / "broker", directory / "worker", directory / "observer", inventory


def completed_counts(trials: list[dict[str, Any]]) -> dict[str, int]:
    """Count actual successful positive trials for every required transition."""
    return {
        mode: sum(
            item.get("mode") == mode and item.get("passed") is True and not item.get("abandon_process_group")
            for item in trials
        )
        for mode in RACE_MODES
    }


def receipt(positive: bool, negative: bool, repetitions: int, trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Partial startup experiments cannot approve a native runtime."""
    counts = completed_counts(trials)
    return {
        "completed_races": counts,
        "schema_version": "specfact-managed-startup-experiment-v1",
        "startup_subset_passed": positive and negative and all(count >= 1 for count in counts.values()),
        "repetition_gate_passed": positive
        and negative
        and repetitions >= 100
        and all(count >= 100 for count in counts.values()),
        "production_approved": False,
        "signed_boundary_verified": False,
        "signing_mode": "ad-hoc",
        "hardened_runtime": True,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "repetitions": repetitions,
        "trials": trials,
    }


def run_trials(
    binaries: NativeBinaries, profile: str, directory: Path, repetitions: int
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Run controls and reject the first failed startup repetition group."""
    trials = [trial(binaries, directory / "normal", False, "normal", profile)]
    raw_vfork = trial(binaries, directory / "raw-vfork", False, "raw-vfork-control", profile)
    control = trial(binaries, directory / "probe-control", False, "probe-control", profile)
    if not control["passed"]:
        raise RuntimeError("unsandboxed positive probes failed")
    trials.append(trial(binaries, directory / "negative", True, "pretrace", profile))
    trials.append(trial(binaries, directory / "runtime-trap", False, "runtime-trap", profile))
    for index in range(repetitions):
        for mode in RACE_MODES:
            trials.append(trial(binaries, directory / f"{mode}-{index}", False, mode, profile))
        if not all(item["passed"] for item in trials):
            break
    return trials, control, raw_vfork


def main() -> int:
    """Run local fixtures only, with no network or publication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, choices=range(1, 101), default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        parser.error("native Darwin ARM64 required")
    with tempfile.TemporaryDirectory(prefix="specfact-startup-") as temporary:
        directory = Path(temporary).resolve()
        directory.chmod(0o700)
        broker, worker, observer, inventory = build(directory)
        profile = (Path(__file__).parent / "fixture.sb").read_bytes()
        trials, control, raw_vfork = run_trials(
            NativeBinaries(broker, worker, observer), profile.decode("utf-8"), directory, args.repetitions
        )
        positive = all(item["passed"] for item in trials if not item.get("abandon_process_group"))
        report = receipt(positive, trials[1]["passed"], args.repetitions, trials)
        report["artifacts"] = inventory
        report["profile_sha256"] = hashlib.sha256(profile).hexdigest()
        report["os_build"] = command(["/usr/sbin/sysctl", "-n", "kern.osversion"]).stdout.strip()
        report["probe_control"] = control
        report["raw_vfork_control"] = raw_vfork
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        sys.stdout.write(
            json.dumps({key: value for key, value in report.items() if key not in ("artifacts", "trials")}) + "\n"
        )
        return 0 if report["startup_subset_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
