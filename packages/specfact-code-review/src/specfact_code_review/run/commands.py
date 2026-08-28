"""Implement ``specfact code review run``; its CLI help is the command contract.

Operating guidance in this source is not the source of truth; CLI help is
authoritative. Check the nearest command-specific ``--help`` and ask the user
before guessing when the available command or option differs.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.table import Table

from specfact_code_review.run import differential
from specfact_code_review.run.cleanup_evidence import (
    with_mutation_evidence,
    with_previewed_simplification_findings,
)
from specfact_code_review.run.findings import EvidenceRef, RequirementsEvidenceContext, ReviewFinding, ReviewReport
from specfact_code_review.run.runner import (
    LocalAssuranceKind,
    ReviewFocus,
    ReviewOptions,
    run_capsule_review as run_review,
    run_immutable_scope_review,
)
from specfact_code_review.run.scope import (
    ConflictingScopeError,
    GitResolutionError,
    LegacyFileSelectionRequest,
    NoReviewableFilesError,
    RunCommandError,
    ScopeRequest,
    ScopeResolution,
    cleanup_scope_resolution,
    discover_full_python_files,
    discover_worktree_python_files,
    filter_files_by_focus as _filter_files_by_focus,
    resolve_legacy_files,
    resolve_scope,
)


console = Console()
progress_console = Console(stderr=True)
AutoScope = Literal["changed", "worktree", "index", "range", "full"]
ReviewRunMode = Literal["full", "changed", "shadow"]
ReviewLevelFilter = Literal["error", "warning"]


class InvalidOptionCombinationError(RunCommandError):
    error_code = "invalid_option_combination"


class MissingOutForJsonError(RunCommandError):
    error_code = "missing_out_for_json"


@dataclass(frozen=True)
class ReviewRunRequest:
    """Inputs needed to execute a governed review run."""

    files: list[Path]
    include_tests: bool = False
    scope: AutoScope | None = None
    path_filters: list[Path] | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    pr_context_file: Path | None = None
    include_noise: bool = False
    json_output: bool = False
    out: Path | None = None
    score_only: bool = False
    no_tests: bool = False
    fix: bool = False
    preview_fixes: bool = False
    with_mutation: bool = False
    bug_hunt: bool = False
    review_mode: ReviewRunMode = "changed"
    review_level: ReviewLevelFilter | None = None
    focus_facets: tuple[str, ...] = ()
    review_focus: ReviewFocus | None = None
    requirements_evidence: Path | None = None


@dataclass(frozen=True)
class _ReviewLoopFlags:
    no_tests: bool
    include_noise: bool
    fix: bool
    preview_fixes: bool
    with_mutation: bool
    progress_callback: Callable[[str], None] | None
    bug_hunt: bool
    review_mode: ReviewRunMode
    review_level: ReviewLevelFilter | None
    review_focus: ReviewFocus | None
    assurance_kind: LocalAssuranceKind = "explicit_files"


def _changed_files_from_git_diff(*, include_tests: bool) -> list[Path]:
    try:
        return discover_worktree_python_files(Path.cwd(), include_tests=include_tests)
    except GitResolutionError as exc:
        raise RunCommandError(
            "Unable to determine changed tracked and untracked files from the worktree scope."
        ) from exc


def _all_python_files_from_git() -> list[Path]:
    try:
        return discover_full_python_files(Path.cwd(), include_tests=True)
    except GitResolutionError as exc:
        raise RunCommandError("Unable to determine tracked and untracked files from the full scope.") from exc


def _apply_fixes(files: list[Path]) -> None:
    commands = [
        ["ruff", "check", "--fix", *(str(file_path) for file_path in files)],
        ["ruff", "format", *(str(file_path) for file_path in files)],
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode in {0, 1} and command[1] == "check":
            continue
        if result.returncode == 0:
            continue
        error_output = (result.stderr or result.stdout).strip() or "unknown error"
        raise RuntimeError(f"Auto-fix command failed: {' '.join(command)}: {error_output}")


def _apply_simplification_fixes(report: ReviewReport) -> list[ReviewFinding]:
    """Apply deterministic safe-mechanical simplification rewrites and return applied evidence."""
    fixers: dict[str, Callable[[ReviewFinding], bool]] = {
        "ai-bloat.dead-branch": _apply_dead_branch_fix,
        "ai-bloat.pass-through-try-except": _apply_pass_through_try_except_fix,
        "ai-bloat.redundant-intermediate": _apply_redundant_intermediate_fix,
        "ai-bloat.verbose-bool-return": _apply_verbose_bool_return_fix,
    }
    applied: list[ReviewFinding] = []
    for finding in _fixable_simplifications_by_stable_line_order(report.findings):
        fixer = fixers.get(finding.rule)
        if fixer is None:
            continue
        if fixer(finding):
            applied.append(_applied_simplification_finding(finding))
    return applied


def _applied_simplification_finding(finding: ReviewFinding) -> ReviewFinding:
    deletion_lines = max(1, finding.estimated_deletion_lines or 1)
    before_ref = EvidenceRef(path=finding.file, start_line=finding.line, end_line=finding.line + deletion_lines - 1)
    after_ref = EvidenceRef(path=finding.file, start_line=finding.line, end_line=finding.line)
    return finding.model_copy(
        update={
            "action_status": "applied",
            "before_ref": before_ref,
            "after_ref": after_ref,
            "improvement": f"Applied safe-mechanical rewrite for {finding.rule}.",
        }
    )


def _with_applied_simplification_findings(report: ReviewReport, applied_findings: list[ReviewFinding]) -> ReviewReport:
    if not applied_findings:
        return report
    data = report.model_dump()
    data["findings"] = [*report.findings, *applied_findings]
    data["simplification_summary"] = None
    return ReviewReport(**data)


def _with_simplify_enforce_verdict(report: ReviewReport, flags: _ReviewLoopFlags) -> ReviewReport:
    if (
        flags.review_focus == "simplify"
        and flags.review_mode == "full"
        and report.simplification_summary is not None
        and report.simplification_summary.blocking_simplification_count > 0
    ):
        return report.model_copy(update={"overall_verdict": "FAIL", "ci_exit_code": 1})
    return report


def _fixable_simplifications_by_stable_line_order(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    indexed_findings = [
        (index, finding)
        for index, finding in enumerate(findings)
        if finding.is_safe_mechanical_simplification() and finding.fixable
    ]
    return [finding for _, finding in sorted(indexed_findings, key=lambda item: (item[1].file, -item[1].line, item[0]))]


def _apply_dead_branch_fix(finding: ReviewFinding) -> bool:
    parsed = _parsed_finding_source(finding)
    if parsed is None:
        return False
    file_path, source, tree = parsed
    for function_node in _iter_functions(tree):
        if _apply_duplicate_terminal_guard_fix(finding, file_path, source, function_node):
            return True
    return False


def _apply_duplicate_terminal_guard_fix(
    finding: ReviewFinding,
    file_path: Path,
    source: str,
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    prior_terminal_tests: set[str] = set()
    for stmt in function_node.body:
        if not isinstance(stmt, ast.If) or not _is_pure_test(stmt.test):
            prior_terminal_tests.clear()
            continue
        test_key = ast.dump(stmt.test, include_attributes=False)
        if _matches_duplicate_terminal_guard(stmt, finding.line, test_key, prior_terminal_tests):
            return _replace_line_range(
                file_path,
                source,
                start_line=stmt.lineno,
                end_line=stmt.end_lineno or stmt.lineno,
                replacement=[],
            )
        if _terminal_return(stmt.body) and not stmt.orelse:
            prior_terminal_tests.add(test_key)
        else:
            prior_terminal_tests.clear()
    return False


def _matches_duplicate_terminal_guard(
    stmt: ast.If,
    line: int,
    test_key: str,
    prior_terminal_tests: set[str],
) -> bool:
    return stmt.lineno == line and test_key in prior_terminal_tests and _terminal_return(stmt.body) and not stmt.orelse


def _apply_pass_through_try_except_fix(finding: ReviewFinding) -> bool:
    parsed = _parsed_finding_source(finding)
    if parsed is None:
        return False
    file_path, source, tree = parsed
    for function_node in _iter_functions(tree):
        for stmt in function_node.body:
            if stmt.lineno != finding.line or not isinstance(stmt, ast.Try) or not _is_pass_through_try_except(stmt):
                continue
            replacement = _dedented_try_body_lines(source, stmt)
            if replacement is None:
                return False
            return _replace_line_range(
                file_path,
                source,
                start_line=stmt.lineno,
                end_line=stmt.end_lineno or stmt.lineno,
                replacement=replacement,
            )
    return False


def _apply_redundant_intermediate_fix(finding: ReviewFinding) -> bool:
    parsed = _parsed_finding_source(finding)
    if parsed is None:
        return False
    file_path, source, tree = parsed
    for function_node in _iter_functions(tree):
        for index, stmt in enumerate(function_node.body[:-1]):
            next_stmt = function_node.body[index + 1]
            if not _matches_redundant_intermediate(stmt, next_stmt, finding.line):
                continue
            expression = ast.get_source_segment(source, stmt.value)
            if expression is None:
                return False
            return _replace_line_range(
                file_path,
                source,
                start_line=stmt.lineno,
                end_line=next_stmt.end_lineno or next_stmt.lineno,
                replacement=f"{_indent_for_line(source, stmt.lineno)}return {expression}",
            )
    return False


def _apply_verbose_bool_return_fix(finding: ReviewFinding) -> bool:
    parsed = _parsed_finding_source(finding)
    if parsed is None:
        return False
    file_path, source, tree = parsed
    for function_node in _iter_functions(tree):
        for index, stmt in enumerate(function_node.body[:-1]):
            next_stmt = function_node.body[index + 1]
            expression = _verbose_bool_replacement_expression(source, stmt, next_stmt, finding.line)
            if expression is None:
                continue
            return _replace_line_range(
                file_path,
                source,
                start_line=stmt.lineno,
                end_line=next_stmt.end_lineno or next_stmt.lineno,
                replacement=f"{_indent_for_line(source, stmt.lineno)}return {expression}",
            )
    return False


def _parsed_finding_source(finding: ReviewFinding) -> tuple[Path, str, ast.Module] | None:
    file_path = Path(finding.file)
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    return file_path, source, tree


def _matches_redundant_intermediate(stmt: ast.stmt, next_stmt: ast.stmt, line: int) -> bool:
    if stmt.lineno != line or not isinstance(stmt, ast.Assign):
        return False
    if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
        return False
    return (
        isinstance(next_stmt, ast.Return)
        and isinstance(next_stmt.value, ast.Name)
        and next_stmt.value.id == stmt.targets[0].id
    )


def _verbose_bool_replacement_expression(
    source: str,
    stmt: ast.stmt,
    next_stmt: ast.stmt,
    line: int,
) -> str | None:
    if stmt.lineno != line or not isinstance(stmt, ast.If):
        return None
    predicate = ast.get_source_segment(source, stmt.test)
    if predicate is None or len(stmt.body) != 1 or stmt.orelse:
        return None
    first_value = _return_bool_constant(stmt.body[0])
    second_value = _return_bool_constant(next_stmt)
    return (
        None
        if first_value is None or second_value is None or first_value == second_value
        else _bool_expr(predicate, first_value)
    )


def _is_pass_through_try_except(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Try) or stmt.orelse or stmt.finalbody or len(stmt.handlers) != 1:
        return False
    handler = stmt.handlers[0]
    return len(handler.body) == 1 and isinstance(handler.body[0], ast.Raise) and handler.body[0].exc is None


def _is_pure_test(test_node: ast.expr) -> bool:
    impure_nodes = (
        ast.Attribute,
        ast.Await,
        ast.Call,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Lambda,
        ast.ListComp,
        ast.NamedExpr,
        ast.SetComp,
        ast.Subscript,
        ast.Yield,
        ast.YieldFrom,
    )
    return not any(isinstance(node, impure_nodes) for node in ast.walk(test_node))


def _terminal_return(body: list[ast.stmt]) -> bool:
    return bool(body) and isinstance(body[-1], ast.Return)


def _dedented_try_body_lines(source: str, stmt: ast.Try) -> list[str] | None:
    if not stmt.body:
        return None
    lines = source.splitlines()
    start_line = stmt.body[0].lineno
    end_line = stmt.handlers[0].lineno - 1
    try_indent = _indent_for_line(source, stmt.lineno)
    body_indent = _indent_for_line(source, start_line)
    if len(body_indent) <= len(try_indent):
        return None
    body_lines = lines[start_line - 1 : end_line]
    return [try_indent + line[len(body_indent) :] if line.startswith(body_indent) else line for line in body_lines]


def _bool_expr(predicate: str, first_value: bool) -> str:
    return predicate if first_value else f"not ({predicate})"


def _iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _return_bool_constant(stmt: ast.stmt) -> bool | None:
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, bool):
        return stmt.value.value
    return None


def _indent_for_line(source: str, line_number: int) -> str:
    line = source.splitlines()[line_number - 1]
    return line[: len(line) - len(line.lstrip())]


def _replace_line_range(
    file_path: Path,
    source: str,
    *,
    start_line: int,
    end_line: int,
    replacement: str | list[str],
) -> bool:
    lines = source.splitlines()
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        return False
    replacement_lines = [replacement] if isinstance(replacement, str) else replacement
    lines[start_line - 1 : end_line] = replacement_lines
    trailing_newline = "\n" if source.endswith("\n") else ""
    file_path.write_text("\n".join(lines) + trailing_newline, encoding="utf-8")
    return True


def _render_report(report: ReviewReport) -> None:
    grouped: dict[str, list[ReviewFinding]] = defaultdict(list)
    for finding in report.findings:
        grouped[finding.category].append(finding)

    if not grouped:
        _render_empty_report(report)
        return

    for category in sorted(grouped):
        _render_category_report(category, grouped[category])

    console.print(
        f"Verdict: {report.overall_verdict} | CI exit: {report.ci_exit_code} | "
        f"Score: {report.score} | Reward delta: {report.reward_delta}"
    )
    console.print(report.summary)


def _render_empty_report(report: ReviewReport) -> None:
    console.print("Code Review")
    console.print(report.summary)


def _render_category_report(category: str, findings: list[ReviewFinding]) -> None:
    table = Table(title=f"Code Review: {category}", show_header=True, header_style="bold cyan")
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right")
    table.add_column("Tool")
    table.add_column("Rule")
    table.add_column("Severity")
    table.add_column("Message", overflow="fold")
    for finding in findings:
        table.add_row(
            finding.file,
            str(finding.line),
            finding.tool,
            finding.rule,
            finding.severity,
            finding.message,
        )
    console.print(table)


def _json_output_path(out: Path | None) -> Path:
    return out or Path("review-report.json")


def _is_interactive_terminal() -> bool:
    try:
        return bool(sys.stderr and sys.stderr.isatty())
    except OSError:
        return False


def _run_review_with_progress(
    files: list[Path],
    flags: _ReviewLoopFlags,
) -> ReviewReport:
    if _is_interactive_terminal():
        return _run_review_with_status(files, flags)

    def _emit_progress(description: str) -> None:
        progress_console.print(f"[dim]{description}[/dim]")

    return _run_review_once(
        files,
        _ReviewLoopFlags(
            no_tests=flags.no_tests,
            include_noise=flags.include_noise,
            fix=flags.fix,
            preview_fixes=flags.preview_fixes,
            with_mutation=flags.with_mutation,
            progress_callback=_emit_progress,
            bug_hunt=flags.bug_hunt,
            review_mode=flags.review_mode,
            review_level=flags.review_level,
            review_focus=flags.review_focus,
            assurance_kind=flags.assurance_kind,
        ),
    )


def _run_review_with_status(
    files: list[Path],
    flags: _ReviewLoopFlags,
) -> ReviewReport:
    with progress_console.status("Preparing code review...") as status:
        base = _ReviewLoopFlags(
            no_tests=flags.no_tests,
            include_noise=flags.include_noise,
            fix=False,
            preview_fixes=False,
            with_mutation=False,
            progress_callback=status.update,
            bug_hunt=flags.bug_hunt,
            review_mode=flags.review_mode,
            review_level=flags.review_level,
            review_focus=flags.review_focus,
            assurance_kind=flags.assurance_kind,
        )
        report = _run_review_once(files, base)
        applied_simplification_findings: list[ReviewFinding] = []
        if flags.fix:
            if flags.review_focus == "simplify":
                status.update("Applying safe mechanical simplification fixes...")
                applied_simplification_findings = _apply_simplification_fixes(report)
            status.update("Applying Ruff autofixes...")
            _apply_fixes(files)
            status.update("Re-running review after autofixes...")
            report = _run_review_once(files, base)
            report = _with_applied_simplification_findings(report, applied_simplification_findings)
        if flags.preview_fixes:
            status.update("Previewing safe mechanical simplification fixes...")
            report = with_previewed_simplification_findings(report, files, _apply_simplification_fixes)
        if flags.with_mutation:
            status.update("Recording mutation proof evidence...")
            report = with_mutation_evidence(report, files)
        return _with_simplify_enforce_verdict(report, flags)


def _run_review_once(files: list[Path], flags: _ReviewLoopFlags) -> ReviewReport:
    report = run_review(
        files,
        no_tests=flags.no_tests,
        include_noise=flags.include_noise,
        progress_callback=flags.progress_callback,
        bug_hunt=flags.bug_hunt,
        review_mode=flags.review_mode,
        review_level=flags.review_level,
        focus=flags.review_focus,
        assurance_kind=flags.assurance_kind,
    )
    applied_simplification_findings: list[ReviewFinding] = []
    if flags.fix:
        if flags.review_focus == "simplify":
            if flags.progress_callback is not None:
                flags.progress_callback("Applying safe mechanical simplification fixes...")
            else:
                progress_console.print("[dim]Applying safe mechanical simplification fixes...[/dim]")
            applied_simplification_findings = _apply_simplification_fixes(report)
        if flags.progress_callback is not None:
            flags.progress_callback("Applying Ruff autofixes...")
        else:
            progress_console.print("[dim]Applying Ruff autofixes...[/dim]")
        _apply_fixes(files)
        if flags.progress_callback is not None:
            flags.progress_callback("Re-running review after autofixes...")
        else:
            progress_console.print("[dim]Re-running review after autofixes...[/dim]")
        report = run_review(
            files,
            no_tests=flags.no_tests,
            include_noise=flags.include_noise,
            progress_callback=flags.progress_callback,
            bug_hunt=flags.bug_hunt,
            review_mode=flags.review_mode,
            review_level=flags.review_level,
            focus=flags.review_focus,
            assurance_kind=flags.assurance_kind,
        )
        report = _with_applied_simplification_findings(report, applied_simplification_findings)
    if flags.preview_fixes:
        report = with_previewed_simplification_findings(report, files, _apply_simplification_fixes)
    if flags.with_mutation:
        report = with_mutation_evidence(report, files)
    return _with_simplify_enforce_verdict(report, flags)


def _as_auto_scope(value: object) -> AutoScope | None:
    if value is None:
        return None
    if isinstance(value, str) and value in {"changed", "worktree", "index", "range", "full"}:
        return cast(AutoScope, value)
    raise RunCommandError(f"Invalid scope value: {value!r}")


def _as_path_filters(value: object) -> list[Path] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(path_filter, Path) for path_filter in value):
        return value
    raise RunCommandError("Path filters must be a list of Path instances.")


def _as_optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    raise RunCommandError("Output path must be a Path instance.")


def _as_review_mode(value: object) -> ReviewRunMode:
    if value is None:
        return "changed"
    if value == "enforce":
        return "full"
    if value in ("full", "changed", "shadow"):
        return cast(ReviewRunMode, value)
    raise RunCommandError(f"Invalid review mode: {value!r}")


def _as_review_level(value: object) -> ReviewLevelFilter | None:
    if value is None:
        return None
    if value in ("error", "warning"):
        return cast(ReviewLevelFilter, value)
    raise RunCommandError(f"Invalid review level: {value!r}")


def _as_focus_facets(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        for item in value:
            if item not in ("source", "tests", "docs", "simplify"):
                raise RunCommandError(f"Invalid focus facet: {item!r}")
        return tuple(value)
    raise RunCommandError("focus facets must be a list or tuple of strings")


def _review_focus_from_facets(facets: tuple[str, ...]) -> ReviewFocus | None:
    return "simplify" if "simplify" in facets else None


def _build_review_run_request(
    files: list[Path],
    kwargs: dict[str, object],
) -> ReviewRunRequest:
    # Validate files is a list of Path instances
    if not isinstance(files, list):
        raise RunCommandError(f"files must be a list, got {type(files).__name__}")
    if not all(isinstance(file_path, Path) for file_path in files):
        raise RunCommandError("files must contain only Path instances")

    request_kwargs = dict(kwargs)

    # Validate and extract known boolean flags with proper type checking
    def _get_bool_param(name: str, default: bool = False) -> bool:
        value = request_kwargs.pop(name, default)
        if value is None:
            return default
        if not isinstance(value, bool):
            raise RunCommandError(f"{name} must be a boolean, got {type(value).__name__}")
        return value

    # Validate and extract known path/scope parameters
    def _get_optional_param(name: str, validator: Callable[[object], object], default: object = None) -> object:
        value = request_kwargs.pop(name, default)
        if value is None or value == default:
            return default
        return validator(value)

    # Get include_tests with proper default
    include_tests_value = request_kwargs.pop("include_tests", None)
    include_tests = False  # default value
    if include_tests_value is not None:
        if not isinstance(include_tests_value, bool):
            raise RunCommandError(f"include_tests must be a boolean, got {type(include_tests_value).__name__}")
        include_tests = include_tests_value

    # Get optional parameters with proper type casting
    scope_value = _get_optional_param("scope", _as_auto_scope)
    path_filters_value = _get_optional_param("path_filters", _as_path_filters)
    out_value = _get_optional_param("out", _as_optional_path)
    requirements_evidence_value = _get_optional_param("requirements_evidence", _as_optional_path)
    base_ref_value = request_kwargs.pop("base_ref", None)
    head_ref_value = request_kwargs.pop("head_ref", None)
    if base_ref_value is not None and not isinstance(base_ref_value, str):
        raise RunCommandError("base_ref must be a string")
    if head_ref_value is not None and not isinstance(head_ref_value, str):
        raise RunCommandError("head_ref must be a string")
    pr_context_file_value = _get_optional_param("pr_context_file", _as_optional_path)

    # Cast the optional parameters to their proper types
    scope = cast(AutoScope | None, scope_value)
    path_filters = cast(list[Path] | None, path_filters_value)
    out = cast(Path | None, out_value)
    requirements_evidence = cast(Path | None, requirements_evidence_value)

    focus_facets = cast(tuple[str, ...], _as_focus_facets(request_kwargs.pop("focus_facets", None)))

    request = ReviewRunRequest(
        files=files,
        include_tests=include_tests,
        scope=scope,
        path_filters=path_filters,
        base_ref=cast(str | None, base_ref_value),
        head_ref=cast(str | None, head_ref_value),
        pr_context_file=cast(Path | None, pr_context_file_value),
        include_noise=_get_bool_param("include_noise"),
        json_output=_get_bool_param("json_output"),
        out=out,
        score_only=_get_bool_param("score_only"),
        no_tests=_get_bool_param("no_tests"),
        fix=_get_bool_param("fix"),
        preview_fixes=_get_bool_param("preview_fixes"),
        with_mutation=_get_bool_param("with_mutation"),
        bug_hunt=_get_bool_param("bug_hunt"),
        review_mode=_as_review_mode(request_kwargs.pop("review_mode", "changed")),
        review_level=_as_review_level(request_kwargs.pop("review_level", None)),
        focus_facets=focus_facets,
        review_focus=_review_focus_from_facets(focus_facets),
        requirements_evidence=requirements_evidence,
    )

    # Reject any unexpected keyword arguments
    if request_kwargs:
        unexpected = ", ".join(sorted(request_kwargs))
        raise RunCommandError(f"Unexpected keyword arguments: {unexpected}")

    return request


def _render_review_result(report: ReviewReport, request: ReviewRunRequest) -> tuple[int, str | None]:
    if request.json_output:
        output_path = _json_output_path(request.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.model_dump_json(), encoding="utf-8")
        return report.ci_exit_code or 0, str(output_path)
    if request.score_only:
        return report.ci_exit_code or 0, str(report.score)

    _render_report(report)
    return report.ci_exit_code or 0, None


def _scope_evidence(resolution: ScopeResolution) -> dict[str, object]:
    """Serialize immutable scope identity without exposing materialization paths."""

    return {
        "status": resolution.status,
        "reason": resolution.reason,
        "assurance_kind": resolution.assurance_kind,
        "effective_assurance_kind": resolution.effective_assurance_kind,
        "selected_paths": list(resolution.selected_paths),
        "merge_base_candidates": list(resolution.merge_base_candidates),
        "merge_base_candidate_digest": resolution.merge_base_candidate_digest,
        "context_digest": resolution.context_digest,
        "project_runtime_source_locks": [
            {"path": path, "blob_sha": blob_sha, "content_sha256": content_sha256}
            for path, blob_sha, content_sha256 in resolution.project_runtime_source_locks
        ],
        "resolved_target_commit": resolution.resolved_target_commit,
        "resolved_target_tree": resolution.resolved_target_tree,
        "resolved_head_commit": resolution.resolved_head_commit,
        "resolved_head_tree": resolution.resolved_head_tree,
        "exact_rename_digest": resolution.exact_rename_digest,
        "base_source_manifest_digest": resolution.base_source_manifest_digest,
        "head_source_manifest_digest": resolution.head_source_manifest_digest,
        "policy_manifest_digest": resolution.policy_manifest_digest,
        "candidate_policy_change_digest": resolution.candidate_policy_change_digest,
        "index_tree": resolution.index_tree,
        "selection_tree": resolution.selection_tree,
        "input_manifest": {
            path: {
                "object_type": identity.object_type,
                "git_mode": identity.git_mode,
                "blob_sha": identity.blob_sha,
                "content_digest": identity.content_digest,
                "open_policy": identity.open_policy,
            }
            for path, identity in sorted(resolution.input_manifest.items())
        },
        "index_metadata": {
            path: {
                "git_mode": metadata.git_mode,
                "blob_sha": metadata.blob_sha,
                "stage": metadata.stage,
                "intent_to_add": metadata.intent_to_add,
                "flag_tag": metadata.flag_tag,
            }
            for path, metadata in sorted(resolution.index_metadata.items())
        },
    }


def _repository_slug(repository: Path) -> str | None:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    match = re.search(r"github\.com(?::|/)([^/]+)/([^/]+?)(?:\.git)?$", result.stdout.strip())
    return f"{match.group(1)}/{match.group(2)}" if match is not None else None


def _immutable_scope_report(request: ReviewRunRequest) -> ReviewReport:
    """Resolve immutable scope and execute every active analyzer in its capsule."""

    resolution = resolve_scope(
        ScopeRequest(
            repository=Path.cwd(),
            scope=cast(Literal["index", "range"], request.scope),
            files=tuple(request.files),
            base_ref=request.base_ref,
            head_ref=request.head_ref,
            enforcement=request.review_mode,
            include_tests=request.include_tests,
            focus=request.focus_facets,
            path_filters=tuple(request.path_filters or ()),
            no_tests=request.no_tests,
            level=request.review_level,
            fix=request.fix,
            preview_fixes=request.preview_fixes,
            with_mutation=request.with_mutation,
            pr_context_file=request.pr_context_file,
            repository_slug=_repository_slug(Path.cwd()),
        )
    )
    try:
        status = resolution.status
        reason = resolution.reason
        if status == "PASS":
            return run_immutable_scope_review(
                resolution,
                options=ReviewOptions(
                    no_tests=request.no_tests,
                    include_noise=request.include_noise,
                    bug_hunt=request.bug_hunt,
                    review_level=request.review_level,
                    review_mode=request.review_mode,
                    focus=request.review_focus,
                ),
                scope_evidence={**_scope_evidence(resolution), "reason": reason},
            )
        run_identity = resolution.resolved_head_commit or resolution.index_tree or "unresolved"
        activation = differential.activate_packaged_suppression_catalog()
        catalog_ready = activation.status == "PASS" and activation.profile_activated and activation.digest is not None
        if status == "NOT_APPLICABLE" and not catalog_ready:
            status = "UNKNOWN"
            reason = activation.reason or "suppression_catalog_activation_failed"
        return ReviewReport(
            schema_version="1.6",
            run_id=f"review-scope-{run_identity}",
            score=0,
            findings=[],
            summary=resolution.diagnostics or reason.replace("_", " "),
            assurance_status=cast(Any, status),
            has_unknown_required_evidence=status == "UNKNOWN",
            scope_evidence={**_scope_evidence(resolution), "reason": reason},
            analyzer_evidence=[],
            suppression_catalog_digest=activation.digest if catalog_ready else None,
            enforcement_mode="shadow" if request.review_mode == "shadow" else "full",
        )
    finally:
        cleanup_scope_resolution(resolution)


def _validate_review_request(request: ReviewRunRequest) -> None:
    _raise_if_targeting_styles_conflict(request.files, scope=request.scope, path_filters=request.path_filters or [])
    _validate_output_options(request)
    _validate_simplification_options(request)
    _validate_immutable_scope_options(request)


def _validate_output_options(request: ReviewRunRequest) -> None:
    if request.json_output and request.score_only:
        raise InvalidOptionCombinationError("Use either --json or --score-only, not both.")
    if not request.json_output and request.out is not None:
        raise MissingOutForJsonError("Use --out together with --json.")


def _validate_simplification_options(request: ReviewRunRequest) -> None:
    if request.preview_fixes and request.fix:
        raise InvalidOptionCombinationError("Cannot combine --preview-fixes with --fix.")
    if request.preview_fixes and request.review_focus != "simplify":
        raise InvalidOptionCombinationError("Use --preview-fixes only with --focus simplify.")
    if request.with_mutation and request.review_focus != "simplify":
        raise InvalidOptionCombinationError("Use --with-mutation only with --focus simplify.")


def _validate_immutable_scope_options(request: ReviewRunRequest) -> None:
    immutable_options = (
        request.base_ref is not None or request.head_ref is not None or request.pr_context_file is not None
    )
    if immutable_options and request.scope != "range":
        raise InvalidOptionCombinationError("--base-ref, --head-ref, and --pr-context-file require --scope range.")
    if request.scope == "range" and (request.base_ref is None or request.head_ref is None):
        raise InvalidOptionCombinationError("--scope range requires both --base-ref and --head-ref.")
    if request.pr_context_file is not None and not request.pr_context_file.is_absolute():
        raise InvalidOptionCombinationError("--pr-context-file must be an absolute path.")


def _raise_if_targeting_styles_conflict(
    files: list[Path], *, scope: AutoScope | None, path_filters: list[Path]
) -> None:
    """Reject positional files combined with automatic scope or path controls."""

    if files and scope is not None:
        raise ConflictingScopeError("Choose positional files or auto-scope controls, not both.")
    if files and path_filters:
        raise ConflictingScopeError("Choose positional files or auto-scope controls, not both.")


def _normalize_review_request(request: ReviewRunRequest) -> ReviewRunRequest:
    if request.review_focus is not None or "simplify" not in request.focus_facets:
        return request
    return ReviewRunRequest(
        files=request.files,
        include_tests=request.include_tests,
        scope=request.scope,
        path_filters=request.path_filters,
        base_ref=request.base_ref,
        head_ref=request.head_ref,
        pr_context_file=request.pr_context_file,
        include_noise=request.include_noise,
        json_output=request.json_output,
        out=request.out,
        score_only=request.score_only,
        no_tests=request.no_tests,
        fix=request.fix,
        preview_fixes=request.preview_fixes,
        with_mutation=request.with_mutation,
        bug_hunt=request.bug_hunt,
        review_mode=request.review_mode,
        review_level=request.review_level,
        focus_facets=request.focus_facets,
        review_focus=_review_focus_from_facets(request.focus_facets),
        requirements_evidence=request.requirements_evidence,
    )


def _requirements_evidence_context(path: Path) -> RequirementsEvidenceContext:
    """Read only a complete final Requirements proof for review provenance."""
    try:
        payload = path.read_bytes()
        decoded = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunCommandError("finalized Requirements evidence must be readable JSON") from error
    if not isinstance(decoded, dict):
        raise RunCommandError("finalized Requirements evidence must contain a JSON object")
    if decoded.get("schema_version") != "2":
        raise RunCommandError("finalized Requirements evidence must have schema_version=2")
    execution_proof = decoded.get("execution_proof")
    if not isinstance(execution_proof, dict) or execution_proof.get("run_stage") != "final":
        raise RunCommandError("finalized Requirements evidence must have execution_proof.run_stage=final")
    if not _is_complete_final_requirements_proof(decoded, execution_proof):
        raise RunCommandError("finalized Requirements evidence must be a complete final Requirements proof")
    values: dict[str, Any] = {
        "path": str(path),
        "content_digest": _canonical_json_digest(decoded),
        "mapping_digest": decoded.get("mapping_digest"),
        "plan_digest": decoded.get("plan_digest"),
        "source_ref": execution_proof.get("source_ref"),
        "gate_decision": decoded.get("gate_decision"),
    }
    try:
        return RequirementsEvidenceContext.model_validate(values)
    except ValueError as error:
        raise RunCommandError("finalized Requirements evidence has invalid provenance") from error


def _attach_requirements_evidence(report: ReviewReport, context: RequirementsEvidenceContext) -> ReviewReport:
    """Attach Requirements provenance without downgrading authoritative review truth."""

    return report.model_copy(
        update={
            "requirements_evidence": context,
            "schema_version": report.schema_version if _schema_version_at_least(report.schema_version, 5) else "1.5",
        }
    )


def _schema_version_at_least(value: str, required_minor: int) -> bool:
    try:
        major_text, minor_text, *_ = value.split(".")
        major = int(major_text)
        minor = int(minor_text)
    except (ValueError, TypeError):
        return False
    return major > 1 or (major == 1 and minor >= required_minor)


def _is_complete_final_requirements_proof(decoded: dict[str, Any], execution_proof: dict[str, Any]) -> bool:
    """Return whether a final proof retains its plans, selectors, and reconciliation evidence."""
    execution_plan = decoded.get("execution_plan")
    findings = decoded.get("findings")
    selectors = execution_proof.get("selectors")
    if not isinstance(execution_plan, dict) or not isinstance(findings, list) or not isinstance(selectors, list):
        return False
    if not _proof_fields_are_complete(decoded, execution_proof):
        return False
    expected_selectors = _execution_plan_selectors(execution_plan)
    if not expected_selectors or selectors != sorted(expected_selectors):
        return False
    return _proof_decision_is_consistent(decoded, findings)


def _proof_fields_are_complete(decoded: dict[str, Any], execution_proof: dict[str, Any]) -> bool:
    """Return whether required final-proof fields have valid structural values."""
    mapping_digest = decoded.get("mapping_digest")
    plan_digest = decoded.get("plan_digest")
    findings = decoded.get("findings")
    selectors = execution_proof.get("selectors")
    if not isinstance(findings, list) or not isinstance(selectors, list):
        return False
    return all(
        (
            decoded.get("required_maturity") == "verified",
            decoded.get("observed_maturity") in {"verified", "incomplete"},
            _is_sha256_digest(mapping_digest),
            _is_sha256_digest(plan_digest),
            all(isinstance(finding, str) for finding in findings),
            _is_complete_plan(decoded.get("plan"), mapping_digest, plan_digest),
            _is_complete_plan(decoded.get("execution_plan"), mapping_digest),
            _is_sha256_digest(execution_proof.get("junit_digest")),
            bool(selectors),
            all(isinstance(selector, str) and selector for selector in selectors),
            _passing_proof_basis_is_complete(decoded, execution_proof),
        )
    )


def _passing_proof_basis_is_complete(decoded: dict[str, Any], execution_proof: dict[str, Any]) -> bool:
    """Require an auditable historical basis before accepting passing provenance."""
    if decoded.get("gate_decision") != "pass":
        return True
    proof_basis = execution_proof.get("proof_basis")
    if proof_basis == "red-junit":
        return True
    if proof_basis != "legacy-tdd-ledger":
        return False
    legacy_tdd_evidence = decoded.get("legacy_tdd_evidence")
    return (
        isinstance(legacy_tdd_evidence, dict)
        and legacy_tdd_evidence.get("schema_version") == "1"
        and legacy_tdd_evidence.get("kind") == "legacy-tdd-ledger"
        and isinstance(legacy_tdd_evidence.get("change_id"), str)
        and bool(legacy_tdd_evidence["change_id"])
        and _is_sha256_digest(legacy_tdd_evidence.get("ledger_digest"))
        and legacy_tdd_evidence.get("mapping_digest") == decoded.get("mapping_digest")
        and legacy_tdd_evidence.get("plan_digest") == decoded.get("plan_digest")
    )


def _execution_plan_selectors(execution_plan: dict[str, Any]) -> set[str]:
    """Return the exact test selectors emitted by one validated execution plan."""
    selectors: set[str] = set()
    for case in execution_plan.get("cases", []):
        if not isinstance(case, dict) or case.get("method") != "test":
            continue
        node_id = case.get("node_id")
        if isinstance(node_id, str):
            selectors.add(node_id)
    return selectors


def _proof_decision_is_consistent(decoded: dict[str, Any], findings: list[Any]) -> bool:
    """Return whether the proof decision agrees with its final maturity and findings."""
    proof_passes = decoded.get("observed_maturity") == "verified" and not findings
    return (decoded.get("gate_decision") == "pass") == proof_passes


def _is_complete_plan(plan: object, mapping_digest: object, plan_digest: object | None = None) -> bool:
    """Return whether one emitted Requirements plan has its identity and nonempty cases."""
    if (
        not isinstance(plan, dict)
        or plan.get("mapping_digest") != mapping_digest
        or not isinstance(plan.get("cases"), list)
    ):
        return False
    if not plan["cases"] or not _is_sha256_digest(plan.get("plan_digest")):
        return False
    if not isinstance(mapping_digest, str) or not all(isinstance(case, dict) for case in plan["cases"]):
        return False
    if plan.get("plan_digest") != _requirements_plan_digest(mapping_digest, [dict(case) for case in plan["cases"]]):
        return False
    return plan_digest is None or plan["plan_digest"] == plan_digest


def _requirements_plan_digest(mapping_digest: str, cases: list[dict[str, Any]]) -> str:
    """Use the Requirements producer's canonical plan identity algorithm."""
    try:
        lifecycle = importlib.import_module("specfact_requirements.requirements.lifecycle")
    except ImportError as exc:
        raise RunCommandError("Requirements bundle is unavailable; install the declared module dependency.") from exc
    plan = lifecycle.build_plan(mapping_digest, cases)
    return str(plan["plan_digest"])


def _is_sha256_digest(value: object) -> bool:
    """Return whether value is a lowercase SHA-256 digest with its canonical prefix."""
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _canonical_json_digest(value: dict[str, Any]) -> str:
    """Return the stable digest for a semantically equivalent JSON object."""
    canonical_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()}"


@beartype
@require(
    lambda request_or_files: request_or_files is None or isinstance(request_or_files, (list, ReviewRunRequest)),
    "request must be a review request or a list of Path objects",
)
@ensure(lambda result: isinstance(result, tuple))
def run_command(
    request_or_files: ReviewRunRequest | list[Path] | None = None,
    **kwargs: object,
) -> tuple[int, str | None]:
    """Execute a governed review run over the provided files."""
    request = (
        request_or_files
        if isinstance(request_or_files, ReviewRunRequest)
        else _build_review_run_request(
            list(request_or_files or []),
            kwargs,
        )
    )
    request = _normalize_review_request(request)
    _validate_review_request(request)

    if request.scope in {"index", "range"}:
        report = _immutable_scope_report(request)
        if request.requirements_evidence is not None:
            report = _attach_requirements_evidence(
                report,
                _requirements_evidence_context(request.requirements_evidence),
            )
        return _render_review_result(report, request)

    file_focus_facets = tuple(facet for facet in request.focus_facets if facet in {"source", "tests", "docs"})
    include_for_resolve = request.include_tests or bool(file_focus_facets)
    legacy_scope: Literal["changed", "full"] | None = None
    if request.scope in {"changed", "worktree"}:
        legacy_scope = "changed"
    elif request.scope == "full":
        legacy_scope = "full"
    resolved_files = resolve_legacy_files(
        request.files,
        LegacyFileSelectionRequest(
            include_tests=include_for_resolve,
            scope=legacy_scope,
            path_filters=request.path_filters or [],
            changed_discovery=_changed_files_from_git_diff,
            full_discovery=_all_python_files_from_git,
        ),
    )
    resolved_files = _filter_files_by_focus(resolved_files, request.focus_facets)
    if not resolved_files:
        raise NoReviewableFilesError(
            "No reviewable Python files matched the selected --focus facets."
            if request.focus_facets
            else "No Python files to review were provided or detected."
        )

    requirements_evidence = (
        _requirements_evidence_context(request.requirements_evidence)
        if request.requirements_evidence is not None
        else None
    )
    report = _run_review_with_progress(
        resolved_files,
        _ReviewLoopFlags(
            no_tests=request.no_tests,
            include_noise=request.include_noise,
            fix=request.fix,
            preview_fixes=request.preview_fixes,
            with_mutation=request.with_mutation,
            progress_callback=None,
            bug_hunt=request.bug_hunt,
            review_mode=request.review_mode,
            review_level=request.review_level,
            review_focus=request.review_focus,
            assurance_kind=("explicit_files" if request.files else "full" if request.scope == "full" else "worktree"),
        ),
    )
    if requirements_evidence is not None:
        report = _attach_requirements_evidence(report, requirements_evidence)
    return _render_review_result(report, request)


__all__ = [
    "ConflictingScopeError",
    "InvalidOptionCombinationError",
    "MissingOutForJsonError",
    "NoReviewableFilesError",
    "ReviewRunRequest",
    "RunCommandError",
    "run_command",
]
