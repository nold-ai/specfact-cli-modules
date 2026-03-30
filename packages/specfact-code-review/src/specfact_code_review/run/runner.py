"""Orchestration helpers for structured code-review runs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import _normalize_path_variants, _tool_error
from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.scorer import score_review
from specfact_code_review.tools.ast_clean_code_runner import run_ast_clean_code
from specfact_code_review.tools.basedpyright_runner import run_basedpyright
from specfact_code_review.tools.contract_runner import run_contract_check
from specfact_code_review.tools.pylint_runner import run_pylint
from specfact_code_review.tools.radon_runner import run_radon
from specfact_code_review.tools.ruff_runner import run_ruff
from specfact_code_review.tools.semgrep_runner import run_semgrep


_SOURCE_ROOT = Path("packages/specfact-code-review/src")
_PACKAGE_ROOT = _SOURCE_ROOT / "specfact_code_review"
_COVERAGE_THRESHOLD = 80.0
_SUPPRESSION_MARKERS = ("# noqa", "# type: ignore", "# pyright: ignore", "# pylint: disable")
_TEST_NOISE_RULES = {
    ("contract_runner", "MISSING_ICONTRACT"),
    ("basedpyright", "reportMissingImports"),
    ("basedpyright", "reportAttributeAccessIssue"),
    ("pylint", "W0212"),
}
_GLOBAL_NOISE_RULES = {
    ("pylint", "R0801"),
}
_NOISE_MESSAGE_PREFIXES = ("ValidationError: 1 validation error for LedgerState",)
_PR_MODE_ENV = "SPECFACT_CODE_REVIEW_PR_MODE"
_PR_CONTEXT_ENVS = (
    "SPECFACT_CODE_REVIEW_PR_TITLE",
    "SPECFACT_CODE_REVIEW_PR_BODY",
    "SPECFACT_CODE_REVIEW_PR_PROPOSAL",
)
_CLEAN_CODE_CONTEXT_HINTS = ("clean code", "naming", "kiss", "yagni", "dry", "solid", "complexity")


def _source_relative_path(source_file: Path) -> Path | None:
    source_root_candidates = [_SOURCE_ROOT, *_resolved_path_variants(_SOURCE_ROOT)]
    source_file_candidates = [source_file, *_resolved_path_variants(source_file)]
    return next(
        (
            relative_path
            for candidate in source_file_candidates
            for source_root in source_root_candidates
            if (relative_path := _relative_to(candidate, source_root)) is not None
        ),
        None,
    )


def _resolved_path_variants(path: Path) -> list[Path]:
    try:
        return [path.resolve()]
    except OSError:
        return []


def _relative_to(candidate: Path, source_root: Path) -> Path | None:
    with suppress(ValueError):
        return candidate.relative_to(source_root)
    return None


def _expected_test_path(source_file: Path) -> Path | None:
    relative_path = _source_relative_path(source_file)
    if relative_path is None:
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


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_entries: list[str] = [str(Path.cwd().resolve()), str(_SOURCE_ROOT.resolve())]
    _extend_unique_entries(pythonpath_entries, env.get("PYTHONPATH", ""), split_by=os.pathsep)
    _extend_unique_entries(
        pythonpath_entries,
        (str(Path(entry).resolve()) for entry in sys.path if entry and Path(entry).exists()),
    )
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return env


def _extend_unique_entries(
    entries: list[str],
    values: Iterable[str] | str,
    *,
    split_by: str | None = None,
) -> None:
    for entry in _iter_unique_entries(values, split_by=split_by):
        if entry and entry not in entries:
            entries.append(entry)


def _iter_unique_entries(
    values: Iterable[str] | str,
    *,
    split_by: str | None = None,
) -> Iterable[str]:
    if isinstance(values, str):
        yield from values.split(split_by) if split_by is not None else [values]
        return
    yield from values


def _pytest_targets(test_files: list[Path]) -> list[Path]:
    if len(test_files) <= 1:
        return test_files
    common_root = Path(os.path.commonpath([str(test_file) for test_file in test_files]))
    if common_root.is_dir() and common_root.parts[:2] == ("tests", "unit") and len(common_root.parts) > 3:
        return [common_root]
    return test_files


def _pytest_python_executable() -> str:
    local_candidates = [Path(".venv/bin/python"), Path(".venv/Scripts/python.exe")]
    for candidate in local_candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return str(resolved)
    return sys.executable


def _run_pytest_with_coverage(test_files: list[Path]) -> tuple[subprocess.CompletedProcess[str], Path]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as coverage_file:
        coverage_path = Path(coverage_file.name)

    test_targets = _pytest_targets(test_files)
    command = [
        _pytest_python_executable(),
        "-m",
        "pytest",
        "--cov",
        str(_PACKAGE_ROOT),
        "--cov-fail-under=0",
        f"--cov-report=json:{coverage_path}",
        *(str(test_target) for test_target in test_targets),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=_pytest_env(),
    )
    return result, coverage_path


def _summary_for_findings(findings: list[ReviewFinding]) -> str:
    if not findings:
        return "Review completed with no findings."
    blocking_count = sum(finding.is_blocking() for finding in findings)
    return f"Review completed with {len(findings)} findings ({blocking_count} blocking)."


def _is_test_file(file_path: str | Path) -> bool:
    return "tests" in Path(file_path).parts


def _suppress_known_noise(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    filtered: list[ReviewFinding] = []
    for finding in findings:
        if (finding.tool, finding.rule) in _GLOBAL_NOISE_RULES:
            continue
        if finding.tool == "crosshair" and finding.message.startswith(_NOISE_MESSAGE_PREFIXES):
            continue
        if _is_test_file(finding.file) and (finding.tool, finding.rule) in _TEST_NOISE_RULES:
            continue
        filtered.append(finding)
    return filtered


def _is_truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _checklist_findings() -> list[ReviewFinding]:
    if not _is_truthy_env(_PR_MODE_ENV):
        return []

    context = "\n".join(
        os.environ.get(name, "").strip() for name in _PR_CONTEXT_ENVS if os.environ.get(name, "").strip()
    )
    if any(re.search(rf"\b{re.escape(hint)}\b", context, flags=re.IGNORECASE) for hint in _CLEAN_CODE_CONTEXT_HINTS):
        return []

    return [
        ReviewFinding(
            category="clean_code",
            severity="info",
            tool="checklist",
            rule="clean-code.pr-checklist-missing-rationale",
            file="PR_CONTEXT",
            line=1,
            message=(
                "PR context is missing explicit clean-code reasoning. "
                "Call out the naming, KISS, YAGNI, DRY, or SOLID impact in the proposal or PR body."
            ),
            fixable=False,
        )
    ]


def _tool_steps() -> list[tuple[str, Callable[[list[Path]], list[ReviewFinding]]]]:
    return [
        ("Running Ruff checks...", run_ruff),
        ("Running Radon complexity checks...", run_radon),
        ("Running Semgrep rules...", run_semgrep),
        ("Running AST clean-code checks...", run_ast_clean_code),
        ("Running basedpyright type checks...", run_basedpyright),
        ("Running pylint checks...", run_pylint),
        ("Running contract checks...", run_contract_check),
    ]


def _collect_tdd_inputs(files: list[Path]) -> tuple[list[Path], list[Path], list[ReviewFinding]]:
    source_files = [file_path for file_path in files if _expected_test_path(file_path) is not None]
    findings: list[ReviewFinding] = []
    test_files: list[Path] = []
    for source_file in source_files:
        expected_test = _expected_test_path(source_file)
        if expected_test is None:
            continue
        if expected_test.exists():
            test_files.append(expected_test)
            continue
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
    return source_files, test_files, findings


def _coverage_findings(
    source_files: list[Path],
    coverage_payload: dict[str, object],
) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    findings: list[ReviewFinding] = []
    coverage_by_source: dict[str, float] = {}
    for source_file in source_files:
        percent_covered = _coverage_for_source(source_file, coverage_payload)
        if percent_covered is None and source_file.name != "__init__.py":
            return [
                _tool_error(
                    tool="pytest",
                    file_path=source_file,
                    message=f"Coverage data missing for {source_file}",
                )
            ], None
        if percent_covered is None:
            continue
        coverage_by_source[str(source_file)] = percent_covered
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
                message=(
                    f"Coverage for {source_file} is {percent_covered:.1f}%, below required {_COVERAGE_THRESHOLD:.1f}%."
                ),
                fixable=False,
            )
        )
    return findings, coverage_by_source


def _evaluate_tdd_gate(files: list[Path]) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    """Validate tests and return findings plus per-source coverage when available."""
    source_files, test_files, findings = _collect_tdd_inputs(files)
    if not source_files:
        return [], None
    if findings:
        return findings, None

    try:
        test_result, coverage_path = _run_pytest_with_coverage(test_files)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return [
            _tool_error(
                tool="pytest",
                file_path=source_files[0],
                message=f"Unable to execute targeted tests: {exc}",
            )
        ], None

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
        ], None

    try:
        coverage_payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            _tool_error(
                tool="pytest",
                file_path=source_files[0],
                message=f"Unable to read coverage report: {exc}",
            )
        ], None
    finally:
        coverage_path.unlink(missing_ok=True)

    return _coverage_findings(source_files, coverage_payload)


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
    findings, _coverage_by_source = _evaluate_tdd_gate(files)
    return findings


def _has_no_suppressions(files: list[Path]) -> bool:
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            return False
        if any(marker in content for marker in _SUPPRESSION_MARKERS):
            return False
    return True


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a ReviewReport")
def run_review(
    files: list[Path],
    *,
    no_tests: bool = False,
    include_noise: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> ReviewReport:
    """Run all configured review runners and build the governed report."""
    findings: list[ReviewFinding] = []
    for description, runner in _tool_steps():
        if progress_callback is not None:
            progress_callback(description)
        findings.extend(runner(files))

    coverage_90_plus = False
    if not no_tests:
        if progress_callback is not None:
            progress_callback("Running targeted tests and coverage...")
        tdd_findings, coverage_by_source = _evaluate_tdd_gate(files)
        findings.extend(tdd_findings)
        coverage_90_plus = bool(coverage_by_source) and all(percent >= 90.0 for percent in coverage_by_source.values())

    findings.extend(_checklist_findings())

    if not include_noise:
        findings = _suppress_known_noise(findings)

    score = score_review(
        findings=findings,
        zero_loc_violations=not any(finding.tool == "ruff" and finding.rule == "E501" for finding in findings),
        zero_complexity_violations=not any(finding.tool == "radon" for finding in findings),
        all_apis_have_icontract=not any(finding.rule == "MISSING_ICONTRACT" for finding in findings),
        coverage_90_plus=coverage_90_plus,
        no_new_suppressions=_has_no_suppressions(files),
    )
    return ReviewReport(
        run_id=f"review-{uuid4()}",
        score=score.score,
        findings=findings,
        summary=_summary_for_findings(findings),
    )
