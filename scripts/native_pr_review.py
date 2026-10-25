"""CI-only completeness barrier around the independently installed signed reviewer."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import yaml


REQUIRED_MEMBERS = (
    "ruff",
    "radon",
    "semgrep-clean",
    "semgrep-bugs",
    "ai-bloat-ast",
    "ast-clean-code",
    "basedpyright",
    "pylint",
    "contracts",
    "targeted-pytest-coverage",
)
_INCOMPLETE_STATES = {"UNKNOWN", "skipped", "error", "timeout", "unavailable"}


def _incomplete(finding: dict) -> bool:
    return (
        finding.get("category") == "tool_error"
        or finding.get("evidence_outcome") in _INCOMPLETE_STATES
        or finding.get("execution_state") in _INCOMPLETE_STATES
    )


def _validate_receipt(receipt: dict, *, expected_head: str) -> None:
    members = receipt.get("members")
    if not isinstance(members, list) or any(not isinstance(item, dict) for item in members):
        raise ValueError("incomplete member inventory")
    ids = [item.get("id") for item in members]
    if len(ids) != len(REQUIRED_MEMBERS) or set(ids) != set(REQUIRED_MEMBERS):
        raise ValueError("incomplete or duplicate member inventory")
    for item in members:
        _validate_member(item, no_python_sources=receipt.get("files") == {})
    if receipt.get("head") != expected_head:
        raise ValueError("receipt head differs from event head")
    if not receipt.get("source_before") or receipt.get("source_before") != receipt.get("source_after"):
        raise ValueError("source changed during review")
    if receipt.get("policy_exit") != 0:
        raise ValueError("native review policy failed")


def _member_not_applicable(item: dict, no_python_sources: bool) -> bool:
    return (
        no_python_sources
        and item.get("outcome") == "NOT_APPLICABLE"
        and item.get("id") != "targeted-pytest-coverage"
        and item.get("reason") == "no_changed_python_sources"
        and item.get("findings") == []
    )


def _validate_member(item: dict, *, no_python_sources: bool) -> None:
    if _member_not_applicable(item, no_python_sources):
        return
    findings = item.get("findings")
    if item.get("outcome") != "COMPLETE" or not isinstance(findings, list):
        raise ValueError("incomplete member execution")
    if any(not isinstance(finding, dict) or _incomplete(finding) for finding in findings):
        raise ValueError("incomplete raw analyzer evidence")


def _rule_identities(root: Path) -> dict[str, str]:
    identities = {}
    for name in (".semgrep/clean_code.yaml", ".semgrep/bugs.yaml", "resources/semgrep-rules/ai-bloat.yaml"):
        path = root / name
        if not path.is_file():
            raise ValueError(f"required signed rule pack missing: {name}")
        payload = path.read_bytes()
        rules = yaml.safe_load(payload).get("rules")
        if not isinstance(rules, list) or not rules:
            raise ValueError(f"required signed rule pack empty: {name}")
        identities[name] = hashlib.sha256(payload).hexdigest()
    return identities


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _source_identity(root: Path) -> str:
    digest = hashlib.sha256()
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    for name in sorted(set(names) - {""}):
        path = root / name
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            data = os.fsencode(os.readlink(path))
        elif stat.S_ISREG(mode):
            data = path.read_bytes()
        else:
            raise ValueError(f"unsupported tracked input: {name}")
        digest.update(json.dumps([name, mode, hashlib.sha256(data).hexdigest()]).encode())
    return digest.hexdigest()


def _subject(root: Path, head: str, base: str) -> tuple[str, list[Path]]:
    if any(re.fullmatch(r"[0-9a-f]{40}", value) is None for value in (head, base)):
        raise ValueError("exact head and merge-base object IDs required")
    tree = _git(root, "rev-parse", f"{head}^{{tree}}")
    if _git(root, "rev-parse", "HEAD") != base or _git(root, "write-tree") != tree:
        raise ValueError("staged subject does not match the exact event head and merge-base")
    if subprocess.run(["git", "-C", str(root), "diff", "--quiet", "--"], check=False).returncode:
        raise ValueError("working source differs from staged subject")
    names = _git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", "--", "*.py")
    files = [Path(name) for name in names.split("\0") if name]
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError(f"unsafe or missing review input: {path}")
    return _source_identity(root), files


def _trusted_configuration(root: Path, base: str, output: Path) -> tuple[Path, Path, dict]:
    payload = _git(root, "show", f"{base}:pyproject.toml")
    config = output / "pyproject.toml"
    config.write_text(payload + "\n")
    parsed = tomllib.loads(payload)
    types = dict(parsed["tool"]["basedpyright"])
    types["extraPaths"] = [str(root / path) for path in types.get("extraPaths", [])]
    types["venvPath"] = str(root)
    types["include"] = [str(root / path) for path in ("src", "packages", "scripts", "tests", "tools")]
    for environment in types.get("executionEnvironments", []):
        environment["root"] = str(root / environment["root"])
    type_config = output / "pyrightconfig.json"
    type_config.write_text(json.dumps(types))
    return config, type_config, parsed


def _analyzers(reviewer: Path, config: Path, type_config: Path) -> list[tuple[str, Callable[..., list[Any]]]]:
    modules = {
        name: importlib.import_module(f"specfact_code_review.tools.{name}_runner")
        for name in ("ruff", "radon", "semgrep", "ai_bloat", "ast_clean_code", "basedpyright", "pylint", "contract")
    }
    return [
        ("ruff", partial(modules["ruff"].run_ruff, extra_args=("--config", str(config), "--no-respect-gitignore"))),
        ("radon", modules["radon"].run_radon),
        ("semgrep-clean", partial(modules["semgrep"].run_semgrep, bundle_root=reviewer)),
        ("semgrep-bugs", partial(modules["semgrep"].run_semgrep_bugs, bundle_root=reviewer)),
        ("ai-bloat-ast", modules["ai_bloat"].run_ai_bloat),
        ("ast-clean-code", modules["ast_clean_code"].run_ast_clean_code),
        ("basedpyright", partial(modules["basedpyright"].run_basedpyright, extra_args=("--project", str(type_config)))),
        ("pylint", partial(modules["pylint"].run_pylint, extra_args=("--rcfile", str(config)))),
        ("contracts", partial(modules["contract"].run_contract_check, bug_hunt=True)),
    ]


def _native_test_command(*, python: Path, config: Path, output: Path, selectors: tuple[str, ...] = ()) -> list[str]:
    required = {"tests/host/proof_capsule_deferred_review_ci.py", "tests/integration/test_hatch_project_runtime.py"}
    command = [str(python), "-m", "pytest", *sorted(required | set(selectors))]
    command.extend(
        (
            "-c",
            str(config),
            "--rootdir=.",
            "-o",
            "junit_family=xunit1",
            f"--cov-config={config}",
            f"--junitxml={output / 'tests.xml'}",
            "--cov=.",
            "--cov-fail-under=0",
            f"--cov-report=json:{output / 'coverage.json'}",
        )
    )
    return command


def _test_inventory(root: Path, files: list[Path]) -> tuple[str, ...]:
    tests = {str(path) for path in files if path.parts[0] == "tests" and path.name.startswith("test_")}
    for path in files:
        if path.parts[0] != "packages" or "src" not in path.parts or path.name == "__init__.py":
            continue
        relative = Path(*path.parts[path.parts.index("src") + 1 :])
        expected = Path("tests/unit") / relative.parent / f"test_{relative.name}"
        if not (root / expected).is_file():
            raise ValueError(f"required source test missing: {expected}")
        tests.add(str(expected))
    return tuple(sorted(tests))


def _native_test_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("SPECFACT_CODE_REVIEW_CHANGED_DIFF", None)
    return environment


def _require_native_test_evidence(junit: Path, *, selectors: tuple[str, ...] = ()) -> None:
    cases = list(ET.parse(junit).getroot().iter("testcase"))
    if not cases or any(case.find(tag) is not None for case in cases for tag in ("failure", "error")):
        raise ValueError("native test evidence missing or failed")
    if any(case.find("skipped") is not None for case in cases):
        raise ValueError("required targeted native test skipped")
    required = {"tests/host/proof_capsule_deferred_review_ci.py", "tests/integration/test_hatch_project_runtime.py"}
    observed = {case.get("file") for case in cases}
    missing = (required | set(selectors)) - observed
    if missing:
        raise ValueError(f"required native test files missing: {sorted(missing)}")


def _native_tests(root: Path, python: Path, output: Path, parsed: dict) -> tuple[list, int]:
    from specfact_code_review.run.runner import _coverage_findings

    junit, coverage = output / "tests.xml", output / "coverage.json"
    _, files = _subject(root, os.environ["NATIVE_REVIEW_HEAD"], os.environ["NATIVE_REVIEW_BASE"])
    selectors = _test_inventory(root, files)
    command = _native_test_command(python=python, config=output / "pyproject.toml", output=output, selectors=selectors)
    command.extend(
        (
            "-o",
            "pythonpath="
            + " ".join(str(root / path) for path in parsed["tool"]["pytest"]["ini_options"]["pythonpath"]),
        )
    )
    with (output / "pytest.log").open("w") as log:
        result = subprocess.run(
            command, stdout=log, stderr=subprocess.STDOUT, check=False, timeout=600, env=_native_test_environment()
        )
    _require_native_test_evidence(junit, selectors=selectors)
    roots = parsed["tool"]["coverage"]["run"]["source"]
    sources = [path for path in files if path.parts[0] in roots and "tests" not in path.parts]
    findings, _ = _coverage_findings(
        sources,
        json.loads(coverage.read_text()),
        threshold=float(parsed["tool"]["coverage"]["report"]["fail_under"]),
        blocking_low_coverage=True,
    )
    return findings, result.returncode


def _run_analyzer(run: Callable[..., list[Any]], files: list[Path], record: dict) -> list[Any]:
    records = run(files)
    record.update(outcome="COMPLETE", findings=[f.model_dump(mode="json") for f in records])
    if any(_incomplete(finding) for finding in record["findings"]):
        record["outcome"] = "INCOMPLETE"
        raise ValueError(f"required analyzer incomplete: {record['id']}")
    return records


def _tool_versions() -> dict[str, str]:
    versions = {
        name: importlib.metadata.version(name)
        for name in ("specfact-cli", "ruff", "radon", "basedpyright", "pylint", "crosshair-tool")
    }
    result = subprocess.run(["semgrep", "--version"], capture_output=True, text=True, check=True, timeout=30)
    versions["semgrep"] = result.stdout.strip()
    if not versions["semgrep"]:
        raise ValueError("required Semgrep version is unavailable")
    return versions


def _review(root: Path, reviewer: Path, project_python: Path, output: Path, receipt: dict) -> None:
    from specfact_code_review.run.findings import ReviewReport
    from specfact_code_review.run.runner import _suppress_known_noise, _with_enforcement
    from specfact_code_review.run.scorer import score_review

    head, base = receipt["head"], receipt["merge_base"]
    before, files = _subject(root, head, base)
    config, type_config, parsed = _trusted_configuration(root, base, output)
    receipt.update(
        {
            "source_before": before,
            "rules": _rule_identities(reviewer),
            "configuration": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (config, type_config)},
            "files": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
            "tools": _tool_versions(),
        }
    )
    findings = []
    for member, run in _analyzers(reviewer, config, type_config):
        if not files:
            receipt["members"].append(
                {"id": member, "outcome": "NOT_APPLICABLE", "reason": "no_changed_python_sources", "findings": []}
            )
            continue
        record = {"id": member, "outcome": "INCOMPLETE", "findings": []}
        receipt["members"].append(record)
        findings.extend(_run_analyzer(run, files, record))
    record = {"id": "targeted-pytest-coverage", "outcome": "INCOMPLETE", "findings": []}
    receipt["members"].append(record)
    tests, test_exit = _native_tests(root, project_python, output, parsed)
    findings.extend(tests)
    record.update(outcome="COMPLETE", findings=[f.model_dump(mode="json") for f in tests])
    findings = _suppress_known_noise(findings)
    score = score_review(findings)
    report = ReviewReport(
        run_id=f"native-ci-{head}", score=score.score, findings=findings, summary="Independent native CI review"
    )
    report = _with_enforcement(report, mode="changed", files=files)
    receipt["policy_exit"] = int(bool(report.ci_exit_code or test_exit or any(f.is_blocking() for f in tests)))
    receipt["policy_report"] = report.model_dump(mode="json")
    receipt["source_after"], _ = _subject(root, head, base)


def _reviewer_identity(reviewer: Path) -> dict[str, str]:
    manifest = reviewer.parent.parent / "module-package.yaml"
    data = manifest.read_bytes()
    if yaml.safe_load(data).get("version") != "0.51.2":
        raise ValueError("independent reviewer version differs from verified installed version")
    for name, module in tuple(sys.modules.items()):
        if name == "specfact_code_review" or name.startswith("specfact_code_review."):
            source = getattr(module, "__file__", None)
            if source is None or not Path(source).resolve().is_relative_to(reviewer):
                raise ValueError("reviewer import resolved outside signed installation")
    return {"version": "0.51.2", "manifest_sha256": hashlib.sha256(data).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--project-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from specfact_cli.registry import CommandRegistry

    CommandRegistry.get_module_typer("code")
    import specfact_code_review

    reviewer = Path(specfact_code_review.__file__).resolve().parent
    if reviewer.is_relative_to(args.subject.resolve()):
        raise ValueError("independent reviewer resolved inside candidate")
    args.output.mkdir(parents=True, exist_ok=True)
    os.chdir(args.subject)
    head, base = os.environ["NATIVE_REVIEW_HEAD"], os.environ["NATIVE_REVIEW_BASE"]
    os.environ["SPECFACT_CODE_REVIEW_CHANGED_DIFF"] = "cached"
    receipt = {"head": head, "merge_base": base, "members": [], "status": "INCOMPLETE"}
    try:
        receipt["reviewer"] = _reviewer_identity(reviewer)
        _review(args.subject.resolve(), reviewer, args.project_python, args.output, receipt)
        _reviewer_identity(reviewer)
        _validate_receipt(receipt, expected_head=head)
        receipt["status"] = "PASS"
    except Exception as exc:
        receipt["diagnostic"] = f"{type(exc).__name__}: {str(exc)[:1000]}"
        raise
    finally:
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
