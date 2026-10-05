"""Native ARM64 resource maintainer proof; never production admission."""

from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any


SOURCE = Path(__file__).resolve().parent
CASES = (
    "nofile-control",
    "nofile",
    "fsize-control",
    "fsize",
    "as-control",
    "as",
    "data-control",
    "data",
    "cpu-control",
    "cpu-default",
    "cpu-ignore",
    "cpu-block",
    "wall-ignore",
    "wall-block",
)
ADMITTED_CASES = ("nofile", "fsize", "as", "wall-ignore", "wall-block")
COMMANDS: list[dict[str, Any]] = []


def require(condition: bool, message: str) -> None:
    """Fail closed instead of silently accepting partial evidence."""
    if not condition:
        raise RuntimeError(message)


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Bound commands and retain actual tool output in the private receipt."""
    result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    COMMANDS.append({"argv": args, "exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    if check:
        result.check_returncode()
    return result


def verify_limit(record: dict[str, Any]) -> None:
    """Successful readback alone is not enforcement or adversarial proof."""
    require(record["set_errno"] == 0 and record["raise_errno"] == errno.EPERM, f"bad limit setup/raise: {record}")
    require(record["soft"] == record["hard"] == record["value"], f"changed hard ceiling: {record}")


def verify_evidence(case: str, records: list[dict[str, Any]]) -> None:
    """Require exact pre/post native readback for every mandatory configured limit."""
    expected = {"CORE": 0}
    if not case.endswith("-control"):
        resource = case.split("-", 1)[0].upper()
        if resource in ("CPU", "WALL"):
            expected["CPU"] = 1
        elif resource == "AS":
            baselines = [item for item in records if item.get("type") == "baseline"]
            require(len(baselines) == 1 and baselines[0]["virtual_bytes"] > 0, "missing native VM baseline")
            expected["AS"] = baselines[0]["virtual_bytes"] + 32 * 1024 * 1024
        else:
            expected[resource] = {"NOFILE": 32, "FSIZE": 4096, "DATA": 16 * 1024 * 1024}[resource]
    limits = [item for item in records if item.get("type") == "limit"]
    require(len(limits) == 2 * len(expected), "missing/extra native limit records")
    for resource, value in expected.items():
        matching = [item for item in limits if item.get("resource") == resource]
        require(
            len(matching) == 2 and {item.get("phase") for item in matching} == {"pre", "post"},
            "missing pre/post native limit evidence",
        )
        require(all(item.get("value") == value for item in matching), "configured resource ceiling changed")
        if resource in ("AS", "DATA") and all(item.get("set_errno") for item in matching):
            continue  # Explicit unavailable memory mechanism; never an enforced claim.
        for item in matching:
            verify_limit(item)


def cleanup_passed(*, survivor: bool, seconds: float, rescued: bool) -> bool:
    """Post-measurement rescue can never upgrade a failed survivor check."""
    return not survivor and 0 <= seconds <= 5 and not rescued


def verify_death_window(records: list[dict[str, Any]]) -> None:
    """Reject cooperative completion that could rescue an owner-death measurement."""
    ready = [item for item in records if item.get("type") == "cpu-ready"]
    require(
        len(ready) == 1 and ready[0].get("self_completion") is False, "competing/missing fixture completion exclusion"
    )


def verify_cpu(case: str, records: list[dict[str, Any]], status: dict[str, Any]) -> dict[str, Any]:
    """Use native process CPU accounting; wall time cannot prove a CPU ceiling."""
    require(isinstance(status.get("cpu_seconds"), (int, float)), "missing wait4 CPU accounting")
    if case == "cpu-default":
        require(status["signal"] == 24 and status["exit"] == -1, f"default SIGXCPU control failed: {status}")
        return {"enforced": False, "classification": "observed-only", "default_signal_effective": True}
    samples = [item for item in records if item.get("type") == "cpu"]
    require(len(samples) == 1 and samples[0]["seconds"] >= 3, "finite CPU stress did not reach 3 CPU seconds")
    require(status["signal"] == 0 and status["exit"] == 37 and status["cpu_seconds"] >= 3, "missing CPU overrun")
    if case == "cpu-block":
        require(samples[0]["sigxcpu_pending"] is True, "blocked SIGXCPU was not pending")
    return (
        {
            "enforced": False,
            "classification": "observed-only",
            "observation": "RLIMIT_CPU=1 CPU second survives ignored/blocked SIGXCPU; no kernel hard CPU kill proven",
        }
        if case != "cpu-control"
        else {"enforced": False, "classification": "observed-only", "positive_control": True}
    )


def receipt(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Admit measured configured ceilings; CPU/RSS observations are not hard budgets."""
    successes = Counter(item.get("case") for item in trials if item.get("passed") is True)
    complete = set(CASES).issubset(successes) and all(
        item.get("passed") is True and not item.get("command_timeout") for item in trials
    )
    lifecycle = complete and all(successes[case] >= 100 for case in ("death-ignore", "death-block"))
    enforced = {
        case: any(
            item.get("case") == case and item.get("passed") is True and item.get("enforced") is True for item in trials
        )
        for case in ADMITTED_CASES
    }
    observations = [item["observation"] for item in trials if "observation" in item]
    budgets = {
        "wall_deadline_ms": 1500,
        "independent_survivor_window_ms": 5000,
        "nofile_descriptors": 32,
        "fsize_bytes_per_file": 4096,
        "address_space_increment_bytes": 32 * 1024 * 1024,
        "workers_per_fixed_resource_job": 1,
    }
    for item in trials:
        if item.get("case") == "as" and item.get("enforced") is True:
            for record in item.get("records", []):
                if record.get("type") == "limit" and record.get("resource") == "AS":
                    budgets["address_space_ceiling_bytes"] = record["value"]
    return {
        "schema_version": "specfact-native-resource-proof-v1",
        "probe_suite_passed": complete,
        "resource_lifecycle_subset_passed": lifecycle,
        "resource_gate_passed": lifecycle and all(enforced.values()),
        "resource_gate_scope": "measured resource fixtures with captured startup BSD tracing; parent integration not admitted",
        "enforced_resource_cases": enforced,
        "configured_budgets": budgets,
        "kernel_hard_cpu_enforced": False,
        "physical_ram_ceiling_proven": False,
        "non_admitted_hard_limits": {
            "CPU": "observed-only",
            "RSS": "observed-only",
            "DATA": "not enforced by these mapping probes",
            "output": "parent-owned; parser size guard is not an enforced byte ceiling",
            "CORE": "zero configured and immutable; core-dump behavior not probed",
        },
        "production_approved": False,
        "counts": dict(successes),
        "observations": observations,
        "blockers": [f"missing enforced resource proof: {case}" for case, passed in enforced.items() if not passed]
        + ([] if lifecycle else ["resource lifecycle subset incomplete"]),
    }


def load_startup(root: Path) -> Any:
    """Import the captured existing controller, without modifying shared sources."""
    snapshot = (SOURCE / "startup.py").read_bytes()
    target = root / "startup.py"
    target.write_bytes(snapshot)
    target.chmod(0o400)
    spec = importlib.util.spec_from_file_location("resource_captured_startup", target)
    require(spec is not None and spec.loader is not None, "captured controller missing")
    assert spec and spec.loader
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    controller.command = command
    return controller


def compile_artifact(root: Path, name: str, data: bytes, extra: list[str]) -> dict[str, Any]:
    """Compile immutable native snapshots and verify exact empty-entitlement signatures."""
    code, target = root / f"source-{name}.c", root / name
    code.write_bytes(data)
    code.chmod(0o400)
    command(
        [
            "/usr/bin/xcrun",
            "clang",
            "-arch",
            "arm64",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(code),
            "-o",
            str(target),
            *extra,
        ]
    )
    command(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)])
    command(["/usr/bin/codesign", "--verify", "--strict", str(target)])
    details = command(["/usr/bin/codesign", "--display", "--verbose=4", str(target)]).stderr
    require("flags=0x10002(adhoc,runtime)" in details and "Signature=adhoc" in details, "wrong native signing mode")
    entitlements = command(["/usr/bin/codesign", "--display", "--entitlements", ":-", str(target)]).stdout
    require(not entitlements.strip(), "nonempty native entitlements")
    architecture = command(["/usr/bin/lipo", "-archs", str(target)]).stdout.strip()
    require(architecture == "arm64", "native artifact is not exact ARM64")
    return {
        "name": name,
        "path": str(target),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "signing": details,
        "entitlements": entitlements,
    }


def build(root: Path) -> tuple[Any, dict[str, Path], list[dict[str, Any]]]:
    """Reuse the captured startup broker/observer; build only resource-specific native tools."""
    controller = load_startup(root)
    source = (SOURCE / "resource_limits.c").read_bytes()
    inventory = [
        compile_artifact(root, "worker", source, ["-DRESOURCE_FILE=" + json.dumps(str(root / "probe-output"))])
    ]
    inventory.append(compile_artifact(root, "metrics", source, ["-DRESOURCE_OBSERVER"]))
    inventory.append(
        compile_artifact(
            root, "supervisor", source, ["-DRESOURCE_SUPERVISOR", "-DFIXED_WORKER=" + json.dumps(str(root / "worker"))]
        )
    )
    for name, filename in (("broker", "startup_broker.c"), ("observer", "startup_observe.c")):
        inventory.append(compile_artifact(root, name, (SOURCE / filename).read_bytes(), []))
    inventory.append({"name": "controller", "sha256": hashlib.sha256((root / "startup.py").read_bytes()).hexdigest()})
    return (
        controller,
        {name: root / name for name in ("worker", "supervisor", "broker", "observer", "metrics")},
        inventory,
    )


def records_from(path: Path) -> list[dict[str, Any]]:
    """Only parse complete bounded native records; trailing partial output is not proof."""
    if not path.exists():
        return []
    data = path.read_text()
    require(len(data) <= 65536, "oversize native evidence")
    return [json.loads(line) for line in data.splitlines() if line.startswith("{") and line.endswith("}")]


def wait_record(path: Path, kind: str, deadline: float) -> list[dict[str, Any]]:
    """A startup/command timeout fails and triggers teardown only after rejection."""
    while time.monotonic() < deadline:
        records = records_from(path)
        if any(item.get("type") == kind for item in records):
            require(time.monotonic() <= deadline, "late native evidence")
            return records
        if any(item.get("type") == "status" for item in records):
            raise RuntimeError(f"worker completed before {kind}: {records}")
        time.sleep(0.01)
    raise TimeoutError(f"native {kind} evidence timeout")


def observe_absence(
    controller: Any,
    observer: Path,
    identity: dict[str, Any],
    started: float,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Observer measures only; no signaling or timeout rescue inside the five-second window."""
    deadline = started + 5
    while clock() < deadline:
        survivor = controller.alive(observer, identity)
        elapsed = clock() - started
        if not survivor:
            require(cleanup_passed(survivor=False, seconds=elapsed, rescued=False), "late worker disappearance")
            return {"survivor": False, "observation_seconds": elapsed, "rescued": False}
        time.sleep(0.01)
    raise RuntimeError("resource worker survived five seconds")


def verify_probe(case: str, records: list[dict[str, Any]], status: dict[str, Any]) -> dict[str, Any]:
    """Paired operation results distinguish unsupported controls from enforced bounds."""
    require(not status.get("safety_timeout"), "native safety timeout is rejection, never resource proof")
    verify_evidence(case, records)
    if case.startswith("cpu-"):
        return verify_cpu(case, records, status)
    if case.startswith("wall-"):
        timers = [item for item in records if item.get("type") == "timer"]
        require(len(timers) == 1 and timers[0]["deadline_ms"] == 1500, "missing native watchdog event")
        require(
            isinstance(timers[0].get("deadline_monotonic_seconds"), (int, float))
            and timers[0]["deadline_monotonic_seconds"] > 0,
            "missing original native wall deadline",
        )
        require(status["timer_fired"] and status["signal"] == 9 and status["exit"] == -1, "watchdog kill missing")
        require(1.5 <= status["elapsed_seconds"] <= 2.5, "native watchdog missed bounded deadline")
        require(any(item.get("type") == "cpu-ready" for item in records), "signal control never started")
        return {"enforced": True, "mechanism": "native kqueue wall watchdog", "kernel_hard_cpu_enforced": False}
    require(status["exit"] == 37 and status["signal"] == 0, f"resource probe failed: {status}")
    probes = [item for item in records if item.get("type") == "probe"]
    require(len(probes) == 1 and probes[0]["positive"], "missing positive below-limit operation")
    probe = probes[0]
    if case.startswith(("as", "data")):
        require(probe.get("mach_positive") is True, "missing Mach VM positive control")
    if case.endswith("-control"):
        if case.startswith(("as", "data")):
            require(probe["mach_over_error"] == 0, "unbounded Mach VM control failed")
        require(probe["over_errno"] == 0, "unbounded positive control failed")
        return {"enforced": False, "positive_control": True}
    if case == "nofile":
        require(probe["over_errno"] == errno.EMFILE and probe["opened"] < 32, "descriptor ceiling not enforced")
        return {"enforced": True, "mechanism": "RLIMIT_NOFILE", "ceiling_descriptors": 32}
    if case == "fsize":
        require(probe["over_errno"] == errno.EFBIG and probe["file_bytes"] == 4096, "file ceiling not enforced")
        return {"enforced": True, "mechanism": "RLIMIT_FSIZE", "ceiling_bytes_per_file": 4096}
    unavailable = any(
        item.get("type") == "limit" and item["resource"] in ("AS", "DATA") and item["set_errno"] for item in records
    )
    if not unavailable and probe["over_errno"] == errno.ENOMEM and probe["mach_over_error"] in (3, 6):
        return {
            "enforced": True,
            "mechanism": f"RLIMIT_{case.upper()} anonymous mapping ceiling",
            "physical_ram_ceiling_proven": False,
        }
    require(
        probe["over_errno"] in (0, errno.ENOMEM) and probe["mach_over_error"] in (0, 3, 6),
        "memory probe failed for unexplained reason",
    )
    return {
        "enforced": False,
        "classification": "not-admitted",
        "observation": f"RLIMIT_{case.upper()} did not bound both mmap and Mach VM 64 MiB allocations; physical RAM ceiling unproven",
    }


def capture_resources(
    controller: Any,
    binaries: dict[str, Path],
    identity: dict[str, Any],
    root: Path,
    case: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Separate native libproc process verifies actual resource use during each held probe."""
    require(controller.alive(binaries["observer"], identity), "worker absent before resource measurement")
    measured = json.loads(command([str(binaries["metrics"]), str(identity["pid"])]).stdout)
    require(controller.alive(binaries["observer"], identity), "worker identity lost during resource measurement")
    if case.startswith("nofile"):
        probes = [item for item in records if item.get("type") == "probe"]
        require(
            len(probes) == 1 and measured["fd_count"] == probes[0]["opened"] + 4, "independent FD accounting mismatch"
        )
        require(
            measured["fd_count"] <= 32 if case == "nofile" else measured["fd_count"] == 68,
            "independent FD ceiling mismatch",
        )
    if case.startswith("fsize"):
        size = (root / "probe-output").stat().st_size
        require(size == (4096 if case == "fsize" else 4097), "independent file-size ceiling mismatch")
        measured["file_bytes"] = size
    if case == "as":
        limits = [item for item in records if item.get("type") == "limit" and item["resource"] == "AS"]
        if all(item["set_errno"] == 0 for item in limits):
            require(measured["virtual_bytes"] <= limits[0]["value"], "independent virtual ceiling mismatch")
    return measured


def trial(controller: Any, binaries: dict[str, Path], root: Path, case: str, index: int) -> dict[str, Any]:
    """All teardown happens after evidence validation; failure stays failed."""
    death = case.startswith("death-")
    worker_case = case
    directory = root / f"trial-{case}-{index}"
    bootstrap = controller.BootstrapInputs(
        binaries["broker" if death else "supervisor"], binaries["worker"], worker_case
    )
    service, plist = controller.create_job(bootstrap, directory, False, "confined")
    identities: list[dict[str, Any]] = []
    try:
        command(["/bin/launchctl", "bootstrap", service.rsplit("/", 1)[0], str(plist)])
        path = directory / "events"
        records = wait_record(path, "cpu-ready" if death else "ready", time.monotonic() + 5)
        event = next(item for item in records if "broker" in item)
        controller.capture_identity(binaries["observer"], event, identities)
        broker, worker = identities
        require(
            worker["flags"] & 2 != 0 and worker["ppid"] == broker["pid"], "independent tracing/parent proof missing"
        )
        if death:
            verify_death_window(records)
            issued = controller.signal_fixture(binaries["observer"], broker)
            require(issued is not None, "broker exited before death injection")
            assert issued is not None
            started = issued[0]
            result = observe_absence(controller, binaries["observer"], worker, started)
            require(controller.wait_job_absent(service, started + 5), "resource death job survived")
        else:
            measured = None
            if not case.startswith(("cpu-", "wall-")):
                records = wait_record(path, "probe", time.monotonic() + 5)
                measured = capture_resources(controller, binaries, worker, root, case, records)
            records = wait_record(path, "status", time.monotonic() + 8)
            statuses = [item for item in records if item.get("type") == "status"]
            require(len(statuses) == 1, "ambiguous native wait status")
            result = verify_probe(case, records, statuses[0])
            if measured is not None:
                result["independent_resources"] = measured
            if case.startswith("wall-"):
                timer = next(item for item in records if item.get("type") == "timer")
                result.update(
                    observe_absence(
                        controller,
                        binaries["observer"],
                        worker,
                        timer["deadline_monotonic_seconds"],
                        lambda: time.clock_gettime(time.CLOCK_MONOTONIC),
                    )
                )
            else:
                result.update(observe_absence(controller, binaries["observer"], worker, time.monotonic()))
        return {
            "case": case,
            "repetition": index,
            "passed": True,
            "identities": identities,
            "records": records,
            "events_path": str(path),
            **result,
        }
    finally:
        controller.remove_job(binaries["observer"], identities, service)


def verify_control_probe(record: dict[str, Any]) -> None:
    require(record.get("limited") == 1, "missing limited native measurement")
    require(record.get("fd_errno") == errno.EMFILE and 0 < record.get("duplicates", 0) < 128, "NOFILE not enforced")
    require(
        record.get("file_below") == 1
        and record.get("file_above") == -1
        and record.get("file_errno") == errno.EFBIG
        and record.get("file_size") == 16777216,
        "FSIZE not enforced",
    )
    require(
        record.get("mmap_errno") == errno.ENOMEM and record.get("mach_status") == 3,
        "AS not enforced through both native VM APIs",
    )
    require(record.get("small_ok") == 1 and record.get("small_mach") == 0, "VM positive controls failed")


def verify_mach_resource_receipt(report: dict[str, Any]) -> None:
    """No BSD fixture, missing resource readback, or partial races admits Mach integration."""
    require(report.get("signal_transport") == "mach-exception-v1", "actual Mach transport required")
    require(report.get("resource_records_verified") is True, "missing actual worker resource readback")
    require(report.get("protocol_passed") is True, "Mach protocol/initializer controls incomplete")
    require(report.get("worker_header_bound") is True, "resource header bytes not bound to worker build")
    counts = report.get("lifecycle_counts", {})
    require(
        set(counts) == set(report.get("required_lifecycle_cases", ())) and bool(report.get("required_lifecycle_cases")),
        "missing lifecycle cases",
    )
    require(bool(counts) and all(count >= 100 for count in counts.values()), "Mach lifecycle repetitions incomplete")
    require(report.get("all_trials_passed") is True, "failed/rescued Mach trial")
    require(report.get("production_approved") is False, "resource fixture cannot approve production")


def parse_control_resources(output: str) -> dict[str, int]:
    """Read the exact worker record; baseline, allowance and ceiling are distinct."""
    lines = [line for line in output.splitlines() if line.startswith("resource-bounds ")]
    require(len(lines) == 1, "missing/ambiguous actual worker resource record")
    record = {key: int(value) for key, value in (field.split("=", 1) for field in lines[0].split()[1:])}
    require(
        record.get("nofile") == 128 and record.get("fsize") == 16 * 1024 * 1024,
        "actual worker resource ceilings changed",
    )
    require(
        record.get("vm-delta") == 1024 * 1024 * 1024 and record.get("vm-baseline", 0) > 0,
        "actual worker VM baseline/allowance missing",
    )
    require(
        record["vm-ceiling"] == record["vm-baseline"] + record["vm-delta"] and record.get("api-denied") == 1,
        "actual worker immutable ceiling mismatch",
    )
    return record


def capture_control(root: Path) -> tuple[Any, list[dict[str, Any]]]:
    """Read-only capture of parent-owned sources; never edit its build/checker/loops."""
    captured = root / "captured"
    captured.mkdir(mode=0o700)
    inputs = []
    for path in sorted(SOURCE.iterdir()):
        if path.suffix not in (".py", ".c", ".h", ".inc"):
            continue
        data = path.read_bytes()
        target = captured / path.name
        target.write_bytes(data)
        target.chmod(0o444)
        inputs.append({"name": path.name, "sha256": hashlib.sha256(data).hexdigest(), "path": str(target)})
    spec = importlib.util.spec_from_file_location("resource_captured_mach_control", captured / "control.py")
    require(spec is not None and spec.loader is not None, "captured Mach controller unavailable")
    assert spec and spec.loader
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    control.STARTUP.command = command
    return control, inputs


def mach_concurrency_trial(control: Any, broker: Path, observer: Path, root: Path, case: str) -> dict[str, Any]:
    """Observe all eight governed workers before EOF/broker death; native timer cannot rescue."""
    with control.Invocation(broker, observer, root) as invocation:
        invocation.case = case
        client = invocation.connect()
        launches, identities, resources = [], [], []
        for _ in range(8):
            launched = client.launch(2, timeout_ms=5000)
            identity = invocation.capture_worker(launched, 2)
            status = client.request(3, handle=launched["handle"], argument=15)
            require(status.get("ok") is True, "eight-worker SIGTERM-ignore positive control failed")
            resources.append(parse_control_resources(status["output"]))
            launches.append(launched)
            identities.append(identity)
        require(
            client.request(1, argument=2, timeout_ms=5000).get("error") == "worker-limit",
            "actual broker admitted a ninth worker",
        )
        deadline = min(control.cleanup_deadline(launched) for launched in launches)
        if case == "resource-eight-broker-kill":
            issued = control.STARTUP.signal_fixture(observer, invocation.identities[0])
            require(issued is not None, "eight-worker broker exited before injection")
            assert issued is not None
            started = issued[0]
        else:
            started = time.monotonic()
            client.close()
        observations = [
            control.observe_absence(invocation, identity, started, job=True, native_deadline_ns=deadline)
            for identity in identities
        ]
        return {"case": case, "passed": True, "workers": 8, "resources": resources, "observations": observations}


def mach_resource_main(out: Path, repetitions: int) -> int:
    """Use actual captured Mach broker and unchanged parent lifecycle/protocol routines."""
    root = out.parent.resolve()
    require(
        str(root).startswith("/private/tmp/") and root.is_dir() and root.stat().st_mode & 0o077 == 0,
        "private 0700 evidence root required",
    )
    directory = root / f"m-{time.time_ns()}"
    directory.mkdir(mode=0o700)
    report: dict[str, Any] = {"production_approved": False, "mach_resource_subset_passed": False, "trials": []}
    try:
        control, inputs = capture_control(directory)
        report["captured_inputs"] = inputs
        report["harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report["os_build"] = command(["/usr/sbin/sysctl", "-n", "kern.osversion"]).stdout.strip()
        report["architecture"] = platform.machine()
        build_root = directory / "b"
        build_root.mkdir(mode=0o700)
        # Until parent capture lands, this maintainer proof binds its private copy
        # explicitly. No shared builder/checker is edited or production seal claimed.
        parent_capture = '"control_resource.h"' in (control.SOURCE / "control_build.py").read_text()
        header = next(item for item in inputs if item["name"] == "control_resource.h")
        if not parent_capture:
            (build_root / "control_resource.h").write_bytes(Path(header["path"]).read_bytes())
            (build_root / "control_resource.h").chmod(0o444)
        broker, observer, inventory = control.build(build_root)
        worker = next(item for item in inventory if item["name"] == "worker")
        if not parent_capture:
            worker["build_inputs"].append({**header, "path": str(build_root / "control_resource.h")})
        bound_header = next(item for item in worker["build_inputs"] if item["name"] == "control_resource.h")
        require(bound_header["sha256"] == header["sha256"], "worker resource header changed during build")
        report["artifacts"] = inventory
        report["parent_header_capture_present"] = parent_capture
        report["worker_header_bound"] = True
        native_broker = next(item for item in inventory if item["name"] == "broker")
        report["signal_transport"] = native_broker["signal_transport"]
        require(report["signal_transport"] == "mach-exception-v1", "BSD fallback cannot prove integration")
        positive = compile_artifact(
            build_root,
            "resource-header-positive",
            (control.SOURCE / "resource_limits.c").read_bytes(),
            ["-DRESOURCE_CONTROL_TEST", f"-I{build_root}"],
        )
        report["header_positive_artifact"] = positive
        report["header_positive"] = json.loads(
            command([positive["path"], "limited", str(build_root / "limited-file")]).stdout
        )
        verify_control_probe(report["header_positive"])
        paired = json.loads(command([positive["path"], "control", str(build_root / "control-file")]).stdout)
        require(
            paired["duplicates"] == 129
            and paired["file_above"] == 1
            and paired["file_size"] == 16777217
            and paired["mmap_errno"] == 0
            and paired["mach_status"] == 0,
            "native unbounded controls failed",
        )
        report["header_unbounded_control"] = paired
        run_root = build_root  # Parent exec controls resolve exact signed targets here.
        with control.Invocation(broker, observer, run_root) as invocation:
            client = invocation.connect()
            launched = client.launch(1)
            status = client.request(2, handle=launched["handle"])
            require(status["exit"] == 37 and status["signal"] == 0, f"resource worker did not complete: {status}")
            report["resource_record"] = parse_control_resources(status["output"])
            report["resource_status"] = status
            report["resource_records_verified"] = True
        cases = (*control.LIFECYCLE_CASES, "resource-eight-eof", "resource-eight-broker-kill")
        report["required_lifecycle_cases"] = list(cases)
        report["lifecycle_counts"] = dict.fromkeys(cases, 0)
        report["maintainer_budget_seconds"] = 1800
        budget = time.monotonic() + 1800  # Maintainer budget, never worker containment.
        for index in range(1, repetitions + 1):
            for case in cases:
                require(time.monotonic() < budget, "maintainer budget exceeded; proof rejected")
                item = (
                    mach_concurrency_trial(control, broker, observer, run_root, case)
                    if case.startswith("resource-eight-")
                    else control.lifecycle_trial(broker, observer, run_root, case)
                )
                require(item.get("passed") is True, f"Mach lifecycle failure: {case}")
                item["repetition"] = index
                report["trials"].append(item)
                report["lifecycle_counts"][case] += 1
            if index % 10 == 0:
                print(json.dumps({"mach_completed_repetitions": index, "cases": len(cases)}), flush=True)
        protocol = control.protocol_trials(broker, observer, run_root)
        report["trials"].extend(protocol)
        report["protocol_passed"] = all(item.get("passed") is True for item in protocol)
        report["all_trials_passed"] = all(item.get("passed") is True for item in report["trials"])
        if repetitions >= 100:
            verify_mach_resource_receipt(report)
            report["mach_resource_subset_passed"] = True
    except Exception as error:
        report["failure"] = f"{type(error).__name__}: {error}"
    finally:
        report["commands"] = COMMANDS
        with out.open("w") as stream:
            os.chmod(out, 0o600)
            stream.write(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in ("commands", "trials", "captured_inputs", "artifacts")
            }
        ),
        flush=True,
    )
    return 2 if "failure" in report else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mach-control", action="store_true", help="Exercise the actual Mach worker integration")
    parser.add_argument("--death-repetitions", type=int, choices=range(101), default=0)
    args = parser.parse_args()
    require(
        platform.system() == "Darwin" and platform.machine() == "arm64" and os.geteuid() != 0,
        "ordinary-user native ARM64 macOS required",
    )
    if args.mach_control:
        return mach_resource_main(args.out, args.death_repetitions)
    root = args.out.parent.resolve()
    require(
        str(root).startswith("/private/tmp/") and root.is_dir() and root.stat().st_mode & 0o077 == 0,
        "existing private 0700 /private/tmp evidence directory required",
    )
    build_root = root / f"artifacts-{time.time_ns()}"
    build_root.mkdir(mode=0o700)
    report: dict[str, Any] = {"trials": [], "production_approved": False, "resource_gate_passed": False}
    try:
        report["architecture"] = platform.machine()
        report["os_build"] = command(["/usr/sbin/sysctl", "-n", "kern.osversion"]).stdout.strip()
        report["kernel"] = command(["/usr/bin/uname", "-a"]).stdout.strip()
        report["python"] = platform.python_version()
        harness = Path(__file__).read_bytes()
        (build_root / "resource_limits.py").write_bytes(harness)
        (build_root / "resource_limits.py").chmod(0o400)
        report["harness_sha256"] = hashlib.sha256(harness).hexdigest()
        controller, binaries, report["artifacts"] = build(build_root)
        for case in CASES:
            report["trials"].append(trial(controller, binaries, build_root, case, 1))
        for index in range(1, args.death_repetitions + 1):
            for case in ("death-ignore", "death-block"):
                report["trials"].append(trial(controller, binaries, build_root, case, index))
            if index % 10 == 0:
                print(json.dumps({"completed_death_repetitions": index}), flush=True)
    except Exception as error:
        report["failure"] = f"{type(error).__name__}: {error}"
        report["trials"].append(
            {
                "case": "run-failure",
                "passed": False,
                "command_timeout": isinstance(error, (TimeoutError, subprocess.TimeoutExpired)),
            }
        )
    finally:
        report.update(receipt(report["trials"]))
        report["commands"] = COMMANDS
        with args.out.open("w") as stream:
            os.chmod(args.out, 0o600)
            stream.write(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({key: value for key, value in report.items() if key not in ("trials", "commands", "artifacts")}),
        flush=True,
    )
    return 0 if report["probe_suite_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
