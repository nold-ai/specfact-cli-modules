"""Run fixed native Semgrep fixtures through a traced deny-default bootstrap."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import platform
import plistlib
import re
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CapturedSourceLoader(importlib.machinery.SourceFileLoader):
    """Use normal import semantics while binding execution to captured source."""

    def __init__(self, name: str, path: Path, snapshot: bytes) -> None:
        super().__init__(name, str(path))
        self.snapshot = snapshot

    def get_code(self, fullname: str) -> Any:
        """Reject a mismatched import and compile the already captured bytes."""
        if fullname != self.name:
            raise ImportError("captured helper identity mismatch")
        return compile(self.snapshot, self.path, "exec")


def load_script(path: Path, name: str) -> Any:
    """Load a captured repository helper without ambient or bytecode discovery."""
    snapshot = path.read_bytes()
    loader = CapturedSourceLoader(name, path, snapshot)
    spec = importlib.util.spec_from_file_location(name, path, loader=loader)
    assert spec
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.loaded_source_sha256 = hashlib.sha256(snapshot).hexdigest()
    return module


HERE = Path(__file__).resolve().parent
STARTUP = load_script(HERE / "startup.py", "analyzer_startup")
PARITY = load_script(HERE.parent / "native_semgrep_parity.py", "analyzer_parity")

SEALED_CASES = ("clean_code_clean", "clean_code_defective", "bugs_clean", "bugs_defective")
LIBRARY_PINS = {
    "libdwarf.2.dylib": "9afa73bb9a22272a6d586e84204c2434523f5789dfd1894156696c3e02056cd6",
    "libev.4.dylib": "862bcbbb7c273170fe4864990efbb074f429eca11794b701a2f1b9a8a5d960d7",
    "libgmp.10.dylib": "bc6145edbeca608b4fecd4440dbbd7b27cacd55cbfd2b552b8bc333febe43b35",
    "libpcre2-8.0.dylib": "b473d326a1dc8863e527c5fbeb155b8ea1183d0eb92d9d68fbc45568cb14fc81",
    "libtree-sitter.0.22.dylib": "500b3b33d4fcc81d54ff722516056d01a90c6b499509c355c27c4d858f744db5",
    "libtree-sitter.dylib": "500b3b33d4fcc81d54ff722516056d01a90c6b499509c355c27c4d858f744db5",
    "libzstd.1.dylib": "40cde10ac8415f73144109a6e4f80a403ca0a3259e5fd227158277bab146e6d8",
}


def scan_passed(payload: dict[str, Any], exit_code: int, expected: str | None) -> bool:
    """Never turn missing required evidence or a failed launch into clean analysis."""
    if (
        exit_code != 0
        or payload.get("version") != PARITY.VERSION
        or payload.get("errors") != []
        or payload.get("paths", {}).get("scanned") != ["fixture.py"]
    ):
        return False
    results = payload.get("results")
    if not isinstance(results, list):
        return False
    if expected is None:
        return results == []
    return (
        len(results) == 1
        and results[0].get("check_id") == expected
        and results[0].get("path") == "fixture.py"
        and results[0].get("start", {}).get("line") == 2
    )


def case_passed(content: str, payload: dict[str, Any], exit_code: int, expected: str | None) -> bool:
    """Require actual confinement controls in addition to completed analysis."""
    return {"sealed-boundary-established", "sealed-profile-probes-ok"}.issubset(content.splitlines()) and scan_passed(
        payload, exit_code, expected
    )


def verify_libraries(core: Path) -> dict[str, dict[str, str]]:
    """Reject substituted or extra dylibs before granting exact pinned files."""
    directory = core.parent / "libs"
    if directory.is_symlink() or {path.name for path in directory.iterdir()} != set(LIBRARY_PINS):
        raise ValueError("unexpected native library inventory")
    inventory = {}
    for name, digest in LIBRARY_PINS.items():
        path = PARITY.verify_file(directory / name, digest, limit=PARITY.FILE_LIMIT)
        STARTUP.command(["/usr/bin/codesign", "--verify", "--strict", str(path)])
        inventory[name] = {"path": str(path), "sha256": digest}
    return inventory


def build_wrapper(directory: Path, core: Path) -> tuple[Path, str]:
    """Compile a fixed verified core identity into the local maintainer fixture."""
    target = directory / "sealed-worker"
    snapshot = (HERE / "analyzer_worker.c").read_bytes()
    compiled_source = directory / "source-sealed-worker.c"
    compiled_source.write_bytes(snapshot)
    compiled_source.chmod(0o444)
    forbidden = directory / "host-input"
    forbidden.write_text("private host fixture")
    STARTUP.command(["/usr/bin/codesign", "--verify", "--strict", str(core)])
    STARTUP.command(
        [
            "/usr/bin/xcrun",
            "clang",
            "-arch",
            "arm64",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-DSF_CORE_PATH={json.dumps(str(core))}",
            f"-DSF_LIB_DIR={json.dumps(str(core.parent / 'libs'))}",
            f"-DSF_DENIED_PATH={json.dumps(str(forbidden))}",
            str(compiled_source),
            "-o",
            str(target),
        ]
    )
    STARTUP.command(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)])
    STARTUP.command(["/usr/bin/codesign", "--verify", "--strict", str(target)])
    return target, hashlib.sha256(snapshot).hexdigest()


def capture_scan_identity(content: str, observer: Path, identities: list[dict[str, Any]]) -> None:
    """Capture only independently observed fixed fixture processes still alive."""
    if identities or not STARTUP.event_ready("identity", content):
        return
    event = json.loads(next(line for line in content.splitlines() if line.startswith('{"broker":')))
    for name in ("broker", "worker"):
        identity = STARTUP.observe(observer, event[name])
        if identity is not None:
            identities.append(identity)


def completed_scan(content: str) -> int | None:
    """Retain the real executable status; crashed scans are incomplete."""
    matches = re.findall(r"worker-exit=(\d+)", content)
    if matches:
        return int(matches[-1])
    signals = re.findall(r"worker-signal=(\d+)", content)
    return -int(signals[-1]) if signals else None


def _stderr_tail(path: Path) -> str:
    """Keep absent launchd stderr optional without hiding other read failures."""
    try:
        return path.read_text()[-4000:]
    except FileNotFoundError:
        return ""


def wait_scan(events: Path, observer: Path, identities: list[dict[str, Any]], service: str) -> tuple[str, int]:
    """Bound actual analyzer execution and retain independent fixture identity."""
    deadline = time.monotonic() + 30
    content = ""
    while time.monotonic() < deadline:
        content = events.read_text() if events.exists() else ""
        status = completed_scan(content)
        if status is not None:
            return content, status
        capture_scan_identity(content, observer, identities)
        time.sleep(0.02)
    errors = _stderr_tail(events.with_name("errors"))
    raise RuntimeError(f"sealed analyzer timeout: {service}: {content[-4000:]}: {errors[-4000:]}")


def run_case(binaries: Any, directory: Path, case: dict, assets: dict, profile: str) -> dict:
    """Execute only embedded benign sources and approved local rule bytes."""
    broker, worker, observer = binaries
    service, plist = STARTUP.create_job(STARTUP.BootstrapInputs(broker, worker, profile), directory, False, "normal")
    (directory / "fixture.py").write_text(case["source"])
    (directory / "rules.yaml").write_bytes(assets[case["pack"]].read_bytes())
    (directory / "ca.pem").write_bytes(assets["ca_bundle"].read_bytes())
    (directory / "home").mkdir(mode=0o700)
    (directory / "tmp").mkdir(mode=0o700)
    job = plistlib.loads(plist.read_bytes())
    job["ProgramArguments"][3] = profile
    plist.write_bytes(plistlib.dumps(job))
    identities = []
    try:
        STARTUP.command(["/bin/launchctl", "bootstrap", service.rsplit("/", 1)[0], str(plist)])
        content, exit_code = wait_scan(directory / "events", observer, identities, service)
        payloads = [json.loads(line) for line in content.splitlines() if line.startswith('{"version":')]
        payload = payloads[-1] if payloads else {}
        return {
            "passed": case_passed(content, payload, exit_code, case["expected_rule"]),
            "bootstrap_output": content[-4000:],
            "tool_exit": exit_code,
            "fixture_path": str(directory),
            "tool_payload": payload,
            "stderr": _stderr_tail(directory / "errors"),
        }
    finally:
        STARTUP.remove_job(observer, identities, service)


def analyzer_receipt(cases: dict, payload: dict, profile: bytes) -> dict:
    """Keep exact exercised inputs and physical-host evidence distinct from admission."""
    return {
        "schema_version": "specfact-sealed-analyzer-experiment-v1",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "architecture": platform.machine(),
        "os": platform.platform(),
        "os_build": STARTUP.command(["/usr/sbin/sysctl", "-n", "kern.osversion"]).stdout.strip(),
        "semgrep_version": PARITY.VERSION,
        "source_sha256": payload["source_sha256"],
        "passed": set(cases) == set(SEALED_CASES) and all(case["passed"] for case in cases.values()),
        "production_approved": False,
        "complete_boundary_verified": False,
        "cases": cases,
        "assets": payload["assets"],
        "native_libraries": payload["libraries"],
        "bootstrap_sha256": payload["bootstrap_sha256"],
        "profile_sha256": hashlib.sha256(profile).hexdigest(),
        "signed_fixtures": payload["signed_fixtures"],
    }


def execute_sealed_cases(directory: Path, assets: dict, profile: bytes) -> tuple[dict, dict]:
    """Build the fixed bootstrap and execute every required sealed fixture."""
    broker, _fixture, observer, signed = STARTUP.build(directory)
    worker, wrapper_source = build_wrapper(directory, assets["core"])
    cases = {
        name: run_case(
            STARTUP.NativeBinaries(broker, worker, observer),
            directory / name,
            PARITY.CASES[name],
            assets,
            profile.decode("utf-8"),
        )
        for name in SEALED_CASES
    }
    source_digests = {
        f"startup_{item['name'] if item['name'] != 'observer' else 'observe'}.c": item["source_sha256"]
        for item in signed
    }
    return cases, {
        "bootstrap_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
        "signed_fixtures": signed,
        "source_sha256": {
            **source_digests,
            "analyzer_worker.c": wrapper_source,
            "startup.py": STARTUP.loaded_source_sha256,
            "native_semgrep_parity.py": PARITY.loaded_source_sha256,
        },
    }


def main() -> int:
    """Report this analyzer subset only; no runtime publication or admission."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("native Darwin ARM64 required")
    profile = (HERE / "analyzer.sb").read_bytes()
    assets, _rule_bytes = PARITY.validate_assets()
    libraries = verify_libraries(assets["core"])
    inventory = {name: {"path": str(path), "sha256": PARITY.ASSET_PINS[name][1]} for name, path in assets.items()}
    with tempfile.TemporaryDirectory(prefix="specfact sealed 雪 analyzer ") as temporary:
        directory = Path(temporary).resolve()
        directory.chmod(0o700)
        cases, binaries = execute_sealed_cases(directory, assets, profile)
        payload = {
            "assets": inventory,
            "libraries": libraries,
            **binaries,
        }
        report = analyzer_receipt(cases, payload, profile)
        output = HERE.parents[1] / ".specfact/native-compat/sealed-semgrep.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        sys.stdout.write(
            json.dumps(
                {
                    "passed": report["passed"],
                    "production_approved": False,
                    "cases": {name: case["passed"] for name, case in cases.items()},
                }
            )
            + "\n"
        )
        return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
