"""Orchestration helpers for structured code-review runs."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.scorer import score_review
from specfact_code_review.tools import run_basedpyright, run_pylint, run_radon, run_ruff
from specfact_code_review.tools.contract_runner import run_contract_check


_SOURCE_ROOT = Path("packages/specfact-code-review/src")
_PACKAGE_ROOT = _SOURCE_ROOT / "specfact_code_review"
_COVERAGE_THRESHOLD = 80.0


def _normalize_path_variants(path_value: str | Path) -> set[str]:
    path = Path(path_value)
    variants = {
        os.path.normpath(str(path)),
        os.path.normpath(path.as_posix()),
    }
    try:
        resolved = path.resolve()
    except OSError:
        return variants
    variants.add(os.path.normpath(str(resolved)))
    variants.add(os.path.normpath(resolved.as_posix()))
    return variants


def _tool_error(file_path: Path, message: str) -> ReviewFinding:
    return ReviewFinding(
        category="tool_error",
        severity="error",
        tool="pytest",
        rule="tool_error",
        file=str(file_path),
        line=1,
        message=message,
        fixable=False,
    )


def _expected_test_path(source_file: Path) -> Path | None:
    try:
        relative_path = source_file.relative_to(_SOURCE_ROOT)
    except ValueError:
        return None
    return Path("tests/unit") / relative_path.parent / f"test_{relative_path.name}"


def _coverage_for_source(source_file: Path, payload: dict[str, object]) -> float | None:
    files_payload = payload.get("files")
    if not isinstance(files_payload, dict):
        return None
    allowed_paths = _normalize_path_variants(source_file)
    for filename, file_payload in files_payload.items():
        if not isinstance(filename, str):
            continue
        if _normalize_path_variants(filename).isdisjoint(allowed_paths):
            continue
        if not isinstance(file_payload, dict):
            return None
        summary = file_payload.get("summary")
        if not isinstance(summary, dict):
            return None
        percent_covered = summary.get("percent_covered")
        if isinstance(percent_covered, int | float):
            return float(percent_covered)
    return None


def _run_pytest_with_coverage(test_files: list[Path]) -> tuple[subprocess.CompletedProcess[str], Path]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as coverage_file:
        coverage_path = Path(coverage_file.name)

    command = [
        "pytest",
        "--cov",
        str(_PACKAGE_ROOT),
        f"--cov-report=json:{coverage_path}",
        *(str(test_file) for test_file in test_files),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return result, coverage_path


def _summary_for_findings(findings: list[ReviewFinding]) -> str:
    if not findings:
        return "Review completed with no findings."
    blocking_count = sum(finding.is_blocking() for finding in findings)
    return f"Review completed with {len(findings)} findings ({blocking_count} blocking)."


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_tdd_gate(files: list[Path]) -> list[ReviewFinding]:
    """Validate test-file presence and targeted test coverage for bundle source files."""
    source_files = [file_path for file_path in files if _expected_test_path(file_path) is not None]
    if not source_files:
        return []

    findings: list[ReviewFinding] = []
    test_files: list[Path] = []
    for source_file in source_files:
        expected_test = _expected_test_path(source_file)
        if expected_test is None:
            continue
        if not expected_test.exists():
            findings.append(
                ReviewFinding(
                    category="testing",
                    severity="error",
                    tool="pytest",
                    rule="TEST_FILE_MISSING",
                    file=str(source_file),
                    line=1,
                    message=f"Missing corresponding test file: {expected_test}",
                    fixable=False,
                )
            )
            continue
        test_files.append(expected_test)

    if findings:
        return findings

    try:
        test_result, coverage_path = _run_pytest_with_coverage(test_files)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return [_tool_error(source_files[0], f"Unable to execute targeted tests: {exc}")]

    if test_result.returncode != 0:
        return [
            ReviewFinding(
                category="testing",
                severity="error",
                tool="pytest",
                rule="TEST_FAILURE",
                file=str(source_files[0]),
                line=1,
                message="Targeted tests failed for the reviewed source files.",
                fixable=False,
            )
        ]

    try:
        coverage_payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_tool_error(source_files[0], f"Unable to read coverage report: {exc}")]
    finally:
        coverage_path.unlink(missing_ok=True)

    for source_file in source_files:
        percent_covered = _coverage_for_source(source_file, coverage_payload)
        if percent_covered is None:
            return [_tool_error(source_file, f"Coverage data missing for {source_file}")]
        if percent_covered >= _COVERAGE_THRESHOLD:
            continue
        findings.append(
            ReviewFinding(
                category="testing",
                severity="warning",
                tool="pytest",
                rule="TEST_COVERAGE_LOW",
                file=str(source_file),
                line=1,
                message=f"Coverage for {source_file} is {percent_covered:.1f}%, below required {_COVERAGE_THRESHOLD:.1f}%.",
                fixable=False,
            )
        )
    return findings


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a ReviewReport")
def run_review(files: list[Path], *, no_tests: bool = False) -> ReviewReport:
    """Run all configured review runners and build the governed report."""
    findings: list[ReviewFinding] = []
    findings.extend(run_ruff(files))
    findings.extend(run_radon(files))
    findings.extend(run_basedpyright(files))
    findings.extend(run_pylint(files))
    findings.extend(run_contract_check(files))
    if not no_tests:
        findings.extend(run_tdd_gate(files))

    score = score_review(
        findings=findings,
        zero_loc_violations=not any(finding.tool == "ruff" and finding.rule == "E501" for finding in findings),
        zero_complexity_violations=not any(finding.tool == "radon" for finding in findings),
        all_apis_have_icontract=not any(finding.rule == "MISSING_ICONTRACT" for finding in findings),
        coverage_90_plus=False,
        no_new_suppressions=False,
    )
    return ReviewReport(
        run_id=f"review-{uuid4()}",
        score=score.score,
        findings=findings,
        summary=_summary_for_findings(findings),
    )
