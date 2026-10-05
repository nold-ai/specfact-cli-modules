"""Maintainer-only bounded CPython fixture; host Python only orchestrates.

Run as a module from the worktree. Runtime bytes and raw diagnostics are retained
in a fresh private /private/tmp directory, never in signed module paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import tempfile
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from scripts import native_runtime_inventory as macho
from scripts.macos_managed_boundary import control


SOURCE = Path(__file__).resolve().parent
SYSTEM_ROOTS = (
    "/System/Library",
    "/usr/lib",
    "/System/Cryptexes/OS/System/Library",
    "/System/Cryptexes/OS/usr/lib",
    "/System/Volumes/Preboot/Cryptexes/OS/System/Library",
    "/System/Volumes/Preboot/Cryptexes/OS/usr/lib",
)
PROFILE_VERSION = "specfact-cpython-candidate-profile-v1"
MAX_FILES = 10000
MAX_BYTES = 128 * 1024 * 1024
ENTRY = """import sys, time, os
print("python-entry-ns=" + str(time.clock_gettime_ns(time.CLOCK_MONOTONIC)), flush=True)
assert sys.implementation.name == "cpython"
assert sys.version_info[:2] == EXPECTED_VERSION
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert not any("site-packages" in path for path in sys.path)
"""
CASES = {
    "clean": 'assert sum(range(10)) == 45\nprint("python-clean-ok", flush=True)\n',
    "defective": 'def double(value):\n    return value + 1\nif double(3) != 6:\n    print("python-defect-detected", flush=True)\n    sys.exit(7)\n',
    "denials": """import errno, socket

def denied(action):
    try:
        action()
    except OSError as error:
        assert error.errno in (errno.EPERM, errno.EACCES)
    else:
        raise AssertionError("kernel denial missing")

denied(os.fork)
denied(lambda: os.posix_spawn("/usr/bin/true", ["true"], {}))
denied(lambda: open("/etc/hosts", "rb"))
denied(lambda: open(__file__, "wb"))
sock = None
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except OSError as error:
    assert error.errno in (errno.EPERM, errno.EACCES)
else:
    denied(lambda: sock.connect(("127.0.0.1", 9)))
finally:
    if sock is not None:
        sock.close()
denied(lambda: os.execve("/usr/bin/true", ["true"], {}))
print("python-kernel-denials-ok", flush=True)
""",
    "trap": 'import signal\nos.kill(os.getpid(), signal.SIGTRAP)\nprint("trap-suppressed", flush=True)\n',
    "reexec": 'print("python-second-exec", flush=True)\nos.execve(sys.executable, [sys.executable, "-I", "-S", "-B", __file__], {})\n',
    "loop": 'print("python-loop-ready", flush=True)\nwhile True:\n    pass\n',
}


def version_key(version: str) -> str:
    """Support only the explicitly scoped CPython ABI candidates."""
    if version not in ("3.11", "3.12", "3.13"):
        raise ValueError("unsupported CPython candidate ABI")
    return version.replace(".", "")


def inventory(root: Path, *, max_files: int = MAX_FILES, max_bytes: int = MAX_BYTES) -> dict[str, dict[str, Any]]:
    """Capture exact no-link files and directory modes with bounded enumeration."""
    result: dict[str, dict[str, Any]] = {}
    pending = [root]
    total = 0
    while pending:
        path = pending.pop()
        info = path.lstat()
        name = "." if path == root else path.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError("non-regular candidate entry")
        if len(result) >= max_files:
            raise ValueError("candidate entry budget exceeded")
        record: dict[str, Any] = {"mode": stat.S_IMODE(info.st_mode)}
        if stat.S_ISDIR(info.st_mode):
            record["kind"] = "directory"
            with os.scandir(path) as entries:
                for entry in entries:
                    if len(pending) + len(result) >= max_files:
                        raise ValueError("candidate entry budget exceeded")
                    pending.append(Path(entry.path))
        else:
            total += info.st_size
            if total > max_bytes:
                raise ValueError("candidate byte budget exceeded")
            data = path.read_bytes()
            after = path.lstat()
            if (info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError("candidate changed while hashing")
            record.update(kind="file", size=len(data), sha256=hashlib.sha256(data).hexdigest())
        result[name] = record
    return dict(sorted(result.items()))


def verify_inventory(root: Path, expected: dict[str, dict[str, Any]]) -> None:
    """Reject added, changed, missing, linked or mode-substituted fixture bytes."""
    if inventory(root) != expected:
        raise ValueError("prepared candidate inventory changed")


def _read_input(path: Path, root: Path) -> bytes:
    """Candidate sources are data only, confined to the declared input root."""
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root) or not path.is_file():
        raise ValueError("candidate source escapes input root")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError("candidate source byte budget exceeded")
    data = path.read_bytes()
    if len(data) != size:
        raise ValueError("candidate source changed")
    return data


def _stdlib(runtime: Path, destination: Path, version: str, inputs: dict[str, str]) -> None:
    stdlib = runtime / "lib" / f"python{version}"
    if not stdlib.is_dir() or stdlib.is_symlink():
        raise ValueError("candidate stdlib missing or linked")
    total = count = 0
    with zipfile.ZipFile(destination / "lib" / f"python{version_key(version)}.zip", "x", zipfile.ZIP_STORED) as archive:
        # Walk without following directory links; reject them rather than silently omit.
        for directory, directories, names in os.walk(stdlib, followlinks=False):
            directories[:] = sorted(
                name
                for name in directories
                if name not in ("site-packages", "__pycache__", "test", "tests", "lib-dynload")
            )
            for name in directories:
                if (Path(directory) / name).is_symlink():
                    raise ValueError("linked stdlib directory")
            for name in sorted(names):
                if not name.endswith(".py"):
                    continue
                path = Path(directory) / name
                data = _read_input(path, runtime)
                total += len(data)
                count += 1
                if total > MAX_BYTES or count > MAX_FILES:
                    raise ValueError("stdlib input budget exceeded")
                relative = path.relative_to(stdlib).as_posix()
                inputs[f"stdlib/{relative}"] = hashlib.sha256(data).hexdigest()
                entry = zipfile.ZipInfo(relative, (2026, 1, 1, 0, 0, 0))
                entry.external_attr = 0o444 << 16
                archive.writestr(entry, data)
    # CPython getpath requires this prefix landmark even when using a stdlib ZIP.
    landmark = _read_input(stdlib / "os.py", runtime)
    (destination / "lib" / f"python{version}" / "os.py").write_bytes(landmark)


def prepare(root: Path, runtime: Path, version: str) -> dict[str, Any]:
    """Copy a candidate without executing it; no host or environment fallback."""
    version_key(version)
    runtime = runtime.resolve(strict=True)
    if runtime == Path(os.sys.executable).resolve().parent.parent:
        raise ValueError("development host runtime cannot be a prepared candidate")
    target = root / "payload"
    target.mkdir(mode=0o700)
    (target / "bin").mkdir()
    (target / "lib" / f"python{version}" / "lib-dynload").mkdir(parents=True)
    (target / "fixtures").mkdir()
    executable = runtime / "bin" / f"python{version}"
    data = _read_input(executable, runtime)
    prepared = target / "bin" / f"python{version}"
    prepared.write_bytes(data)
    prepared.chmod(0o755)
    inputs = {"executable": hashlib.sha256(data).hexdigest()}
    _stdlib(runtime, target, version, inputs)
    # This minimal fixture admits no third-party or extension dylibs. Candidate
    # built-ins must supply socket/time/os; missing capabilities fail native trials.
    for case, body in CASES.items():
        source = ENTRY.replace("EXPECTED_VERSION", repr(tuple(map(int, version.split("."))))) + body
        (target / "fixtures" / f"{case}.py").write_text(source)
    inspected = macho.inventory(target)
    for image in inspected["images"]:
        if image["architectures"] != ["arm64"]:
            raise ValueError("candidate requires exact ARM64")
        for rpath in image.get("rpaths", []):
            if not rpath.startswith("@executable_path/"):
                raise ValueError("ambient candidate rpath")
            resolved = (prepared.parent / rpath.removeprefix("@executable_path/")).resolve()
            if not resolved.is_relative_to(target) or not resolved.is_dir():
                raise ValueError("candidate rpath escapes prepared payload")
        if any(not macho.is_system(Path(load)) for load in (item["name"] for item in image["dependencies"])):
            raise ValueError("non-system dylib outside minimal candidate closure")
    return {"payload": target, "target": prepared, "version": version, "input_hashes": inputs, "macho": inspected}


def _literal(path: str | Path) -> str:
    """Quote a build-owned literal with no client-selected interpolation."""
    value = str(path)
    if any(ord(char) < 32 for char in value):
        raise ValueError("control character in policy path")
    return json.dumps(value, ensure_ascii=True)


def profile(payload: Path) -> str:
    """Grant only measured immutable code files and exact metadata ancestors."""
    files = [payload / name for name, item in inventory(payload).items() if item["kind"] == "file"]
    metadata = {Path("/")}
    for path in (*files, *(Path(root) for root in SYSTEM_ROOTS)):
        metadata.update(path.parents)
    metadata.update(path for path in payload.rglob("*") if path.is_dir())
    metadata.add(payload)
    literals = " ".join(f"(literal {_literal(path)})" for path in sorted(files))
    ancestors = " ".join(f"(literal {_literal(path)})" for path in sorted(metadata))
    system = " ".join(f"(subpath {_literal(path)})" for path in SYSTEM_ROOTS)
    executable = next((payload / "bin").iterdir())
    return (
        "(version 1)(deny default)(deny mach-task-exception-port-set)(allow signal (target self))"
        '(allow file-read* (literal "/"))'
        f"(allow file-read* {literals})"
        f"(allow file-map-executable (literal {_literal(executable)}) {system})"
        f"(allow file-read* {system})(allow file-read-metadata {ancestors})"
        f"(allow process-exec (literal {_literal(executable)}))"
    )


def _seal(payload: Path) -> dict[str, dict[str, Any]]:
    for path in payload.rglob("*"):
        path.chmod(0o555 if path.is_dir() or path.parent.name == "bin" else 0o444)
    payload.chmod(0o555)
    return inventory(payload)


def build(root: Path, candidate: dict[str, Any], *, loop: bool = False) -> tuple[Path, Path, dict[str, Any]]:
    """Reuse exact build-owned image signing and the unchanged traced broker."""
    buildroot = root / ("loop-build" if loop else "build")
    buildroot.mkdir(mode=0o700)
    tools = control.BUILD.BuildTools(
        control.STARTUP.command, control.verify_native_clock, control.require, control.MACH.prepare
    )
    args, inputs = control.BUILD._inputs(buildroot, SOURCE, tools)
    target = candidate["target"]
    if not loop:
        details, entitlements = control.BUILD._sign(target, tools)
        candidate["signing"] = {"name": "python", "signing": details, "entitlements": entitlements}
        candidate["inventory"] = _seal(candidate["payload"])
        candidate["macho"] = macho.inventory(candidate["payload"])
    verify_inventory(candidate["payload"], candidate["inventory"])
    target_hash = control.BUILD._cdhash(candidate["signing"], tools)
    policy = profile(candidate["payload"])
    header = f"#define PYTHON_PROFILE {json.dumps(policy)}\n"
    for case in CASES:
        selected = "loop" if loop and case == "clean" else case
        header += f"#define PYTHON_{case.upper()} {_literal(candidate['payload'] / 'fixtures' / f'{selected}.py')}\n"
    captured = buildroot / "python_candidate_policy.h"
    captured.write_text(header)
    captured.chmod(0o444)
    inputs.append({"name": captured.name, "sha256": hashlib.sha256(captured.read_bytes()).hexdigest()})
    target_macro = "-DFIXED_TARGET=" + _literal(target)
    worker = buildroot / "control-worker"
    worker_item = control.BUILD._compile(SOURCE / "python_candidate.c", worker, tools, [f"-I{buildroot}", target_macro])
    worker_hash = control.BUILD._cdhash(worker_item, tools)
    observer = buildroot / "control-observer"
    observer_item = control.BUILD._compile(SOURCE / "startup_observe.c", observer, tools, [])
    args += [
        "-DFIXED_WORKER=" + _literal(worker),
        "-DWORKER_REQUIREMENT=" + json.dumps(f'cdhash H"{worker_hash}"'),
        target_macro,
        "-DTARGET_REQUIREMENT=" + json.dumps(f'cdhash H"{target_hash}"'),
        "-framework",
        "Security",
        "-framework",
        "CoreFoundation",
    ]
    broker = buildroot / "control-broker"
    broker_item = control.BUILD._compile(SOURCE / "control_broker.c", broker, tools, args)
    return (
        broker,
        observer,
        {
            "worker": worker_item,
            "observer": observer_item,
            "broker": broker_item,
            "inputs": inputs,
            "policy_sha256": hashlib.sha256(policy.encode()).hexdigest(),
            "target_cdhash": target_hash,
        },
    )


def verify_status(status: dict[str, Any], marker: dict[str, Any] | None, pid: int, case: str) -> None:
    """Require real post-admission Python entry, actual exits and denial markers."""
    if (
        not marker
        or marker.get("exec") != pid
        or marker.get("held") is not False
        or type(marker.get("verified_ns")) is not int
        or status.get("traced") is not True
    ):
        raise ValueError("CPython image admission missing")
    output = status.get("output", "")
    entries = [line.split("=", 1)[1] for line in output.splitlines() if line.startswith("python-entry-ns=")]
    if len(entries) != 1 or not entries[0].isdigit() or int(entries[0]) < marker["verified_ns"]:
        raise ValueError("CPython entry precedes verified replacement")
    expected = {
        "clean": (0, 0, "python-clean-ok"),
        "defective": (7, 0, "python-defect-detected"),
        "denials": (0, 0, "python-kernel-denials-ok"),
        "trap": (-1, 5, "python-entry-ns="),
        "loop": (-1, 9, "python-loop-ready"),
        "reexec": (-1, 5, "python-second-exec"),
    }[case]
    if (status.get("exit"), status.get("signal")) != expected[:2] or expected[2] not in output:
        raise ValueError("CPython fixture status mismatch")
    if "trap-suppressed" in output or (case == "loop" and status.get("reason") != "timeout"):
        raise ValueError("CPython deadline or genuine signal lost")


def trial(broker: Path, observer: Path, root: Path, case: str, mode: int) -> dict[str, Any]:
    with control.Invocation(broker, observer, root) as invocation:
        invocation.case = f"python-{case}"
        client = invocation.connect()
        launched = client.launch(mode, timeout_ms=1000 if case == "loop" else 5000)
        status = client.request(2, handle=launched["handle"])
        marker = control._event_from_file(invocation.directory / "events", "exec", launched["pid"])
        # Persist actual status privately before verification can raise.
        raw = {"case": case, "status": status, "image_stop": marker, "pid": launched["pid"]}
        (root / f"trial-{case}.json").write_text(json.dumps(raw, indent=2) + "\n")
        verify_status(status, marker, launched["pid"], case)
        return {**raw, "passed": True}


def safe_summary(trials: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(item.get("passed") is True for item in trials)
    return {
        "candidate_passed": bool(trials) and passed == len(trials),
        "cases": len(trials),
        "passed": passed,
        "production_approved": False,
        "signed_boundary_verified": False,
        "signing_mode": "ad-hoc",
    }


def run(root: Path, runtime: Path, version: str) -> dict[str, Any]:
    """Compile and exercise only the bounded candidate subset, with raw evidence."""
    candidate = prepare(root, runtime, version)
    broker, observer, artifacts = build(root, candidate)
    trials = []
    for case, mode in (("clean", 6), ("defective", 7), ("denials", 10), ("trap", 12), ("reexec", 8)):
        verify_inventory(candidate["payload"], candidate["inventory"])
        trials.append(trial(broker, observer, root, case, mode))
        verify_inventory(candidate["payload"], candidate["inventory"])
    loop_broker, loop_observer, loop_artifacts = build(root, candidate, loop=True)
    trials.append(trial(loop_broker, loop_observer, root, "loop", 6))
    verify_inventory(candidate["payload"], candidate["inventory"])
    receipt = {
        **safe_summary(trials),
        "version": version,
        "profile_version": PROFILE_VERSION,
        "trials": trials,
        "candidate": candidate,
        "artifacts": artifacts,
        "loop_artifacts": loop_artifacts,
        "os_build": control.STARTUP.command(["/usr/sbin/sysctl", "-n", "kern.osversion"]).stdout.strip(),
    }
    (root / "receipt.json").write_text(json.dumps(receipt, default=str, indent=2) + "\n")
    return safe_summary(trials)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-input", required=True, type=Path)
    parser.add_argument("--version", required=True, choices=("3.11", "3.12", "3.13"))
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        parser.error("native macOS ARM64 is required")
    root = Path(tempfile.mkdtemp(prefix="sf-python-candidate-", dir="/private/tmp"))
    root.chmod(0o700)
    summary = safe_summary([])
    try:
        with (root / "diagnostics.log").open("w") as stream, redirect_stdout(stream):
            summary = run(root, args.runtime_input, args.version)
    except Exception as error:
        (root / "failure.txt").write_text(f"{type(error).__name__}: {error}\n")
    (root / "safe-summary.json").write_text(json.dumps(summary) + "\n")
    print(json.dumps(summary))
    return 0 if summary["candidate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
