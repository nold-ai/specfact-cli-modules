"""Run the pinned external corpus through the public review/runtime interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import runpy
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


EXPECTED_ANALYZERS = frozenset(
    {
        "ruff",
        "radon",
        "semgrep-clean",
        "ai-bloat-ast",
        "ast-clean-code",
        "basedpyright",
        "pylint",
        "contracts",
        "semgrep-bugs",
        "targeted-pytest-coverage",
    }
)


MANIFEST = Path(__file__).resolve().parents[1] / "tests/fixtures/portable-runtime/corpus.json"


def _require_test_execution(rows: list[dict[str, Any]]) -> None:
    execution = next((row.get("target_execution", {}) for row in rows if row["id"] == "targeted-pytest-coverage"), {})
    if not execution.get("collected") or not any(row["phase"] == "call" for row in execution.get("records", [])):
        raise ValueError("external capsule has no actual test execution")
    if not execution.get("coverage", {}).get("files"):
        raise ValueError("external capsule has no actual coverage")


def assert_completed_report(report: dict[str, Any]) -> None:
    """Allow real findings while requiring completed applicable evidence."""
    if report.get("has_unknown_required_evidence") or report.get("assurance_status") not in {"PASS", "FAIL"}:
        raise ValueError("external capsule analysis incomplete")
    rows = report.get("analyzer_evidence", [])
    if any(row.get("evidence_outcome") == "UNKNOWN" for row in rows):
        raise ValueError("external capsule member incomplete")
    _require_test_execution(rows)
    if len(rows) != len(EXPECTED_ANALYZERS) or {row["id"] for row in rows} != EXPECTED_ANALYZERS:
        raise ValueError("external capsule analyzer roster incomplete or duplicated")
    if any(row.get("evidence_outcome") not in {"PASS", "FAIL"} for row in rows):
        raise ValueError("external capsule applicable analyzer did not complete")


def execute(argv: list[str], *, cwd: Path, evidence: Path, name: str, allowed: tuple[int, ...] = (0,)) -> str:
    started = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, timeout=4500)
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / f"{name}.stdout").write_text(result.stdout)
    (evidence / f"{name}.stderr").write_text(result.stderr)
    (evidence / f"{name}.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "exit": result.returncode,
                "seconds": time.monotonic() - started,
                "python": sys.version,
                "platform": platform.platform(),
                "uid": os.getuid(),
            },
            indent=2,
        )
    )
    if result.returncode not in allowed:
        raise ValueError(f"{name} failed with exit {result.returncode}; see {evidence}")
    return result.stdout


def materialize_reconstruction(source: Path, destination: Path) -> None:
    """Create executable external fixtures without collecting them in the module suite."""
    shutil.copytree(source, destination)
    for template in destination.rglob("*.py.in"):
        template.rename(template.with_suffix(""))


def checkout(entry: dict[str, Any], root: Path, evidence: Path) -> None:
    if entry.get("fixture"):
        root.parent.mkdir(parents=True, exist_ok=True)
        materialize_reconstruction(MANIFEST.parent / entry["fixture"], root)
        identity = hashlib.sha256(json.dumps(tracked_identity(root), sort_keys=True).encode()).hexdigest()
        entry["commit"] = "reconstructed-sha256:" + identity
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "fixture-origin.json").write_text(
            json.dumps({"kind": "reconstruction", "original_customer_reproduction": False, "source_identity": identity})
        )
        return
    root.mkdir(parents=True)
    execute(["git", "init", "--quiet"], cwd=root, evidence=evidence, name="git-init")
    execute(["git", "fetch", "--depth=1", entry["url"], entry["commit"]], cwd=root, evidence=evidence, name="git-fetch")
    execute(["git", "checkout", "--detach", "--quiet", "FETCH_HEAD"], cwd=root, evidence=evidence, name="git-checkout")
    actual = execute(["git", "rev-parse", "HEAD"], cwd=root, evidence=evidence, name="git-head").strip()
    if actual != entry["commit"]:
        raise ValueError("corpus checkout identity mismatch")


def tracked_identity(root: Path) -> dict[str, str]:
    paths = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
        if (root / ".git").exists()
        else [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    )
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in paths
        if name and (root / name).is_file()
    }


def json_document(output: str) -> dict[str, Any]:
    # The core CLI may surround command output with a banner and timing footer.
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character == "{":
            try:
                value, _ = decoder.raw_decode(output[index:])
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    raise ValueError("runtime command emitted no JSON document")


def review(
    root: Path, evidence: Path, config: Path, paths: list[str], *, name: str, descriptor: str = ""
) -> dict[str, Any]:
    output = evidence / f"{name}-report.json"
    argv = [
        "specfact",
        "code",
        "review",
        "run",
        *paths,
        "--project-config",
        str(config),
        "--json",
        "--out",
        str(output),
        "--bug-hunt",
    ]
    if descriptor:
        argv += ["--project-runtime", descriptor]
    execute(argv, cwd=root, evidence=evidence, name=name, allowed=(0, 1, 2))
    report = json.loads(output.read_text())
    assert_completed_report(report)
    return report


def assert_host_execution(result: Path) -> None:
    """Reject manager startup errors and suites that never enter a test call."""
    if not result.is_file():
        raise ValueError("host has no actual test execution report")
    cases = ET.parse(result).getroot().iter("testcase")
    if not any(case.find("error") is None and case.find("skipped") is None for case in cases):
        raise ValueError("host has no actual test execution")


def host_test(entry: dict[str, Any], root: Path, evidence: Path, workspace: Path) -> None:
    """Record native-manager test execution in a separate disposable checkout."""
    host = workspace / "host-checkouts" / entry["name"]
    shutil.copytree(root, host, symlinks=True)
    environment = workspace / "host-environments" / entry["name"]
    execute([sys.executable, "-m", "venv", str(environment)], cwd=host, evidence=evidence, name="host-venv")
    python = str(environment / "bin/python")
    manager = entry["manager"]
    versions = {"pip": "pip==26.2.1", "hatch": "hatch==1.18.0", "uv": "uv==0.12.13", "poetry": "poetry==2.4.3"}
    execute([python, "-m", "pip", "install", versions[manager]], cwd=host, evidence=evidence, name="host-manager")
    if manager == "pip":
        install = [
            python,
            "-m",
            "pip",
            "install",
            ".",
            *[arg for group in entry["groups"] for arg in ("--group", group)],
        ]
        run = [python, "-m", "pytest"]
    elif manager == "uv":
        install = [
            python,
            "-m",
            "uv",
            "sync",
            "--locked",
            "--no-default-groups",
            *[arg for group in entry["groups"] for arg in ("--group", group)],
        ]
        run = [str(host / ".venv/bin/python"), "-m", "pytest"]
    elif manager == "hatch":
        export = json.loads(
            execute(
                ["env", f"HATCH_UV={environment / 'bin/uv'}", python, "-m", "hatch", "env", "show", "--json"],
                cwd=host,
                evidence=evidence,
                name="host-environments",
            )
        )
        driver = (
            MANIFEST.parents[3] / "packages/specfact-code-review/src/specfact_code_review/run/runtime_build_driver.py"
        )
        selected = runpy.run_path(str(driver))["select_hatch_environment"](
            export, entry["environment"], f"{sys.version_info.major}.{sys.version_info.minor}"
        )
        install = [python, "-m", "hatch", "env", "create", selected]
        run = [python, "-m", "hatch", "-e", selected, "run", "python", "-m", "pytest"]
    else:
        install = [python, "-m", "poetry", "install", "--no-interaction", "--only", "main," + ",".join(entry["groups"])]
        run = [python, "-m", "poetry", "run", "python", "-m", "pytest"]
    execute(install, cwd=host, evidence=evidence, name="host-install")
    execute(
        [
            *run,
            f"--junitxml={evidence / 'host-junit.xml'}",
            *[path for path in entry["paths"] if path.startswith("tests/")],
        ],
        cwd=host,
        evidence=evidence,
        name="host-tests",
        allowed=(0, 1),
    )
    assert_host_execution(evidence / "host-junit.xml")


def controlled_defect(root: Path, evidence: Path, config: Path, workspace: Path) -> None:
    """Require actual test failure and static defect detection in an identified copy."""
    copy = workspace / "controlled" / root.name
    shutil.copytree(root, copy, symlinks=True)
    (copy / "specfact_controlled.py").write_text('def controlled() -> int:\n    return "injected wrong type"\n')
    (copy / "tests/test_specfact_controlled.py").write_text(
        'def test_specfact_controlled_failure():\n    assert False, "SPECFACT_CONTROLLED_473"\n'
    )
    report = review(
        copy,
        evidence,
        config,
        ["specfact_controlled.py", "tests/test_specfact_controlled.py"],
        name="controlled-defect",
    )
    findings = report.get("findings", [])
    if not any(row.get("rule") == "TEST_OUTCOME_NOT_PASS" for row in findings):
        raise ValueError("controlled failing test was not detected")
    if not any(
        row.get("tool") == "basedpyright" and row.get("file", "").endswith("specfact_controlled.py") for row in findings
    ):
        raise ValueError("controlled type defect was not detected")


def run_entry(entry: dict[str, Any], workspace: Path) -> None:
    evidence = workspace / "evidence" / entry["name"]
    root = workspace / "checkouts" / entry["name"]
    checkout(entry, root, evidence)
    before = tracked_identity(root)
    host_test(entry, root, evidence, workspace)
    config = evidence / "project-runtime.toml"
    config.write_text(
        f"manager={json.dumps(entry['manager'])}\nenvironment={json.dumps(entry['environment'])}\ngroups={json.dumps(entry['groups'])}\nnative_libraries={json.dumps(entry.get('native_libraries', []))}\n"
    )
    execute(
        ["specfact", "code", "review", "runtime", "inspect", "--project-config", str(config), "--json"],
        cwd=root,
        evidence=evidence,
        name="inspect",
    )
    # Cold run exercises automatic preparation; the offline call must reuse it.
    review(root, evidence, config, entry["paths"], name="cold-auto")
    raw = execute(
        ["specfact", "code", "review", "runtime", "prepare", "--project-config", str(config), "--offline", "--json"],
        cwd=root,
        evidence=evidence,
        name="offline-prepare",
    )
    prepared = json_document(raw)
    descriptor = Path(prepared["descriptor"])
    data = json.loads(descriptor.read_text())
    (evidence / "runtime-identity.json").write_text(json.dumps(data, indent=2))
    (evidence / "runtime-bytes.json").write_text(
        json.dumps({"artifact_bytes": sum(p.stat().st_size for p in descriptor.parent.rglob("*") if p.is_file())})
    )
    review(root, evidence, config, entry["paths"], name="warm-attach", descriptor=str(descriptor))
    controlled_defect(root, evidence, config, workspace)
    if tracked_identity(root) != before:
        raise ValueError("capsule modified upstream source or environment inputs")
    (evidence / "acceptance.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "commit": entry["commit"],
                "mode": os.environ.get("MODE", "local-candidate"),
                "source_unchanged": True,
            },
            indent=2,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repository", choices=["requests", "hatch", "flask", "poetry", "hatch-detached"])
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() != "x86_64" or os.getuid() == 0:
        raise ValueError("corpus requires non-root Linux x86-64")
    manifest = json.loads(MANIFEST.read_text())
    if f"{sys.version_info.major}.{sys.version_info.minor}" not in manifest["python"]:
        raise ValueError("unsupported corpus Python ABI")
    failures = []
    for entry in [*manifest["repositories"], *manifest.get("reconstructions", [])]:
        if args.repository and args.repository != entry["name"]:
            continue
        try:
            run_entry(entry, args.workspace.resolve())
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            failures.append({"repository": entry["name"], "diagnostic": str(exc)})
    summary = args.workspace / "evidence" / "corpus-summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps({"status": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
