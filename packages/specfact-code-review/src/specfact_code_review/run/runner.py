"""Orchestration helpers for structured code-review runs."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import normalize_path_variants, tool_error
from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.scorer import score_review
from specfact_code_review.tools.ai_bloat_runner import run_ai_bloat
from specfact_code_review.tools.ast_clean_code_runner import run_ast_clean_code
from specfact_code_review.tools.basedpyright_runner import run_basedpyright
from specfact_code_review.tools.contract_runner import run_contract_check
from specfact_code_review.tools.pylint_runner import run_pylint
from specfact_code_review.tools.radon_runner import run_radon
from specfact_code_review.tools.ruff_runner import run_ruff
from specfact_code_review.tools.semgrep_runner import run_semgrep, run_semgrep_bugs
from specfact_code_review.tools.tool_availability import skip_if_pytest_unavailable


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
_PYLINT_CLI_WRAPPER_NOISE_RULES = {"R0914", "R0917"}
_NOISE_MESSAGE_PREFIXES = ("ValidationError: 1 validation error for LedgerState",)
_PR_MODE_ENV = "SPECFACT_CODE_REVIEW_PR_MODE"
_PR_CONTEXT_ENVS = (
    "SPECFACT_CODE_REVIEW_PR_TITLE",
    "SPECFACT_CODE_REVIEW_PR_BODY",
    "SPECFACT_CODE_REVIEW_PR_PROPOSAL",
)
_CLEAN_CODE_CONTEXT_HINTS = ("clean code", "naming", "kiss", "yagni", "dry", "solid", "complexity")
_TARGETED_TEST_TIMEOUT = int(os.environ.get("SPECFACT_CODE_REVIEW_TARGETED_TEST_TIMEOUT", "120"))
ReviewFocus = Literal["simplify"]


@dataclass(frozen=True)
class ReviewOptions:
    """Optional controls for a governed review run."""

    no_tests: bool = False
    include_noise: bool = False
    progress_callback: Callable[[str], None] | None = None
    bug_hunt: bool = False
    review_level: Literal["error", "warning"] | None = None
    review_mode: Literal["shadow", "enforce"] = "enforce"
    focus: ReviewFocus | None = None


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
    return None if relative_path is None else Path("tests/unit") / relative_path.parent / f"test_{relative_path.name}"


def _coverage_for_source(source_file: Path, payload: dict[str, object]) -> float | None:
    files_payload = payload.get("files")
    if not isinstance(files_payload, dict):
        return None
    allowed_paths = normalize_path_variants(source_file)
    for filename, file_payload in files_payload.items():
        if not isinstance(filename, str):
            continue
        if normalize_path_variants(filename).isdisjoint(allowed_paths):
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
    pythonpath_entries: list[str] = [str(_SOURCE_ROOT.resolve()), str(Path.cwd().resolve())]
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
    return sys.executable


def _run_pytest_with_coverage(test_files: list[Path]) -> tuple[subprocess.CompletedProcess[str], Path]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as coverage_file:
        coverage_path = Path(coverage_file.name)

    test_targets = _pytest_targets(test_files)
    source_root = str(_SOURCE_ROOT.resolve())
    repo_root = str(Path.cwd().resolve())
    command = [
        _pytest_python_executable(),
        "-c",
        (
            "import pathlib, sys, pytest; "
            f"sys.path[:0] = [{source_root!r}, {repo_root!r}]; "
            "import specfact_code_review; "
            "raise SystemExit(pytest.main(sys.argv[1:]))"
        ),
        "--import-mode=importlib",
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
        timeout=_TARGETED_TEST_TIMEOUT,
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
        if _is_pylint_structural_noise(finding):
            continue
        if finding.tool == "crosshair" and finding.message.startswith(_NOISE_MESSAGE_PREFIXES):
            continue
        if _is_test_file(finding.file) and (finding.tool, finding.rule) in _TEST_NOISE_RULES:
            continue
        filtered.append(finding)
    return filtered


def _is_pylint_structural_noise(finding: ReviewFinding) -> bool:
    if finding.tool != "pylint":
        return False
    if finding.rule in _PYLINT_CLI_WRAPPER_NOISE_RULES and _path_name(finding.file) == "commands.py":
        return "argument" in finding.message or "local variable" in finding.message
    return (
        finding.rule == "R0902"
        and "Too many instance attributes" in finding.message
        and _line_targets_dataclass(finding.file, finding.line)
    )


def _path_name(file_path: str) -> str:
    return Path(file_path.replace("\\", "/")).name


def _line_targets_dataclass(file_path: str, line: int) -> bool:
    try:
        module = ast.parse(Path(file_path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return any(
        isinstance(node, ast.ClassDef)
        and (node.lineno == line or any(decorator.lineno == line for decorator in node.decorator_list))
        and any(_is_dataclass_decorator(decorator) for decorator in node.decorator_list)
        for node in ast.walk(module)
    )


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id == "dataclass"
    return isinstance(target, ast.Attribute) and target.attr == "dataclass"


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


def _tool_steps(*, bug_hunt: bool) -> list[tuple[str, Callable[[list[Path]], list[ReviewFinding]]]]:
    return [
        ("Running Ruff checks...", run_ruff),
        ("Running Radon complexity checks...", run_radon),
        ("Running Semgrep rules...", run_semgrep),
        ("Running Semgrep bug rules...", run_semgrep_bugs),
        ("Running AI-bloat AST checks...", run_ai_bloat),
        ("Running AST clean-code checks...", run_ast_clean_code),
        ("Running basedpyright type checks...", run_basedpyright),
        ("Running pylint checks...", run_pylint),
        ("Running contract checks...", partial(run_contract_check, bug_hunt=bug_hunt)),
    ]


def _filter_findings_by_review_level(
    findings: list[ReviewFinding],
    level: Literal["error", "warning"] | None,
) -> list[ReviewFinding]:
    if level is None:
        return findings
    if level == "error":
        return [finding for finding in findings if finding.severity == "error"]
    return [finding for finding in findings if finding.severity in {"error", "warning"}]


def _belongs_to_simplification_queue(finding: ReviewFinding) -> bool:
    if finding.category == "tool_error":
        return True
    if finding.category == "ai_bloat":
        return True
    return (
        finding.category in {"dry", "kiss"}
        and finding.confidence == "high"
        and finding.simplification_metadata_is_deterministic()
    )


def _filter_findings_by_focus(findings: list[ReviewFinding], focus: ReviewFocus | None) -> list[ReviewFinding]:
    if focus is None:
        return findings
    if focus == "simplify":
        return [finding for finding in findings if _belongs_to_simplification_queue(finding)]
    raise ValueError(f"Unsupported review focus: {focus}")


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


def _is_empty_init_file(source_file: Path) -> bool:
    """Check if __init__.py is a marker/empty module with no executable statements."""
    if source_file.name != "__init__.py":
        return False

    try:
        content = source_file.read_text(encoding="utf-8")
    except OSError:
        return False

    # Strip whitespace, comments, and docstrings
    stripped_content = re.sub(r'"""[^"""]*"""', "", content, flags=re.DOTALL)
    stripped_content = re.sub(r"'''[^']*'''", "", stripped_content, flags=re.DOTALL)
    stripped_content = re.sub(r"#.*$", "", stripped_content, flags=re.MULTILINE)
    stripped_content = stripped_content.strip()

    # Consider empty if only contains 'pass' or is completely empty
    return stripped_content in ("", "pass")


def _is_coverage_omitted_init_by_project_policy(source_file: Path) -> bool:
    """True when repo coverage omits this file (``pyproject.toml`` ``[tool.coverage.run]`` ``omit``).

    ``src/**/__init__.py`` and ``packages/**/__init__.py`` are omitted from coverage; the pytest-cov
    JSON report therefore has no ``percent_covered`` for them — not a TDD gap.
    """
    try:
        path = source_file if source_file.is_absolute() else (Path.cwd() / source_file).resolve()
        rel = path.relative_to(Path.cwd().resolve())
    except (ValueError, OSError):
        rel = source_file
    if rel.name != "__init__.py":
        return False
    parts = rel.parts
    return len(parts) >= 2 and parts[0] in ("src", "packages")


def _coverage_findings(
    source_files: list[Path],
    coverage_payload: dict[str, object],
) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    findings: list[ReviewFinding] = []
    coverage_by_source: dict[str, float] = {}
    for source_file in source_files:
        percent_covered = _coverage_for_source(source_file, coverage_payload)
        if percent_covered is None:
            if source_file.name == "__init__.py" and _is_empty_init_file(source_file):
                continue  # Exempt empty __init__.py files
            if _is_coverage_omitted_init_by_project_policy(source_file):
                continue
            return [
                tool_error(
                    tool="pytest",
                    file_path=source_file,
                    message=f"Coverage data missing for {source_file}",
                )
            ], None
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

    pytest_skip = skip_if_pytest_unavailable(source_files[0])
    if pytest_skip:
        return pytest_skip, None

    try:
        test_result, coverage_path = _run_pytest_with_coverage(test_files)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return [
            tool_error(
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
            tool_error(
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


def _review_options_from_kwargs(options: ReviewOptions | None, overrides: dict[str, object]) -> ReviewOptions:
    if options is not None and overrides:
        raise TypeError("pass either options or keyword review overrides, not both")
    if options is not None:
        return options
    allowed_keys = {
        "no_tests",
        "include_noise",
        "progress_callback",
        "bug_hunt",
        "review_level",
        "review_mode",
        "focus",
    }
    unknown_keys = set(overrides) - allowed_keys
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise TypeError(f"unknown review option override: {unknown}")
    for key in ("no_tests", "include_noise", "bug_hunt"):
        value = overrides.get(key, False)
        if not isinstance(value, bool):
            raise TypeError(f"{key} must be bool")
    no_tests = cast(bool, overrides.get("no_tests", False))
    include_noise = cast(bool, overrides.get("include_noise", False))
    bug_hunt = cast(bool, overrides.get("bug_hunt", False))
    progress_callback = overrides.get("progress_callback")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable or None")
    review_level = overrides.get("review_level")
    if review_level not in {"error", "warning", None}:
        raise TypeError("review_level must be one of error, warning, or None")
    review_mode = overrides.get("review_mode", "enforce")
    if review_mode not in {"shadow", "enforce"}:
        raise TypeError("review_mode must be one of shadow or enforce")
    focus = overrides.get("focus")
    if focus not in {"simplify", None}:
        raise TypeError("focus must be simplify or None")
    return ReviewOptions(
        no_tests=no_tests,
        include_noise=include_noise,
        progress_callback=cast(Callable[[str], None] | None, progress_callback),
        bug_hunt=bug_hunt,
        review_level=cast(Literal["error", "warning"] | None, review_level),
        review_mode=cast(Literal["shadow", "enforce"], review_mode),
        focus=cast(ReviewFocus | None, focus),
    )


def _collect_tool_findings(
    files: list[Path],
    *,
    bug_hunt: bool,
    progress_callback: Callable[[str], None] | None,
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for description, runner in _tool_steps(bug_hunt=bug_hunt):
        if progress_callback is not None:
            progress_callback(description)
        findings.extend(runner(files))
    return findings


def _collect_tdd_findings(
    files: list[Path],
    *,
    no_tests: bool,
    progress_callback: Callable[[str], None] | None,
) -> tuple[list[ReviewFinding], bool]:
    if no_tests:
        return [], False
    if progress_callback is not None:
        progress_callback("Running targeted tests and coverage...")
    findings, coverage_by_source = _evaluate_tdd_gate(files)
    coverage_90_plus = bool(coverage_by_source) and all(percent >= 90.0 for percent in coverage_by_source.values())
    return findings, coverage_90_plus


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a ReviewReport")
def run_review(
    files: list[Path],
    options: ReviewOptions | None = None,
    **overrides: object,
) -> ReviewReport:
    """Run all configured review runners and build the governed report."""
    review_options = _review_options_from_kwargs(options, overrides)
    findings = _collect_tool_findings(
        files,
        bug_hunt=review_options.bug_hunt,
        progress_callback=review_options.progress_callback,
    )
    tdd_findings, coverage_90_plus = _collect_tdd_findings(
        files,
        no_tests=review_options.no_tests,
        progress_callback=review_options.progress_callback,
    )
    findings.extend(tdd_findings)

    findings.extend(_checklist_findings())

    if not review_options.include_noise:
        findings = _suppress_known_noise(findings)

    findings = _filter_findings_by_review_level(findings, review_options.review_level)
    findings = _filter_findings_by_focus(findings, review_options.focus)

    score = score_review(
        findings=findings,
        zero_loc_violations=not any(finding.tool == "ruff" and finding.rule == "E501" for finding in findings),
        zero_complexity_violations=not any(finding.tool == "radon" for finding in findings),
        all_apis_have_icontract=not any(finding.rule == "MISSING_ICONTRACT" for finding in findings),
        coverage_90_plus=coverage_90_plus,
        no_new_suppressions=_has_no_suppressions(files),
        simplification_score_neutral=review_options.focus == "simplify",
    )
    report = ReviewReport(
        run_id=f"review-{uuid4()}",
        score=score.score,
        findings=findings,
        summary=_summary_for_findings(findings),
    )
    if review_options.review_mode == "shadow":
        return report.model_copy(update={"ci_exit_code": 0})
    if (
        review_options.focus == "simplify"
        and report.simplification_summary is not None
        and report.simplification_summary.blocking_simplification_count > 0
    ):
        return report.model_copy(update={"overall_verdict": "FAIL", "ci_exit_code": 1})
    return report
