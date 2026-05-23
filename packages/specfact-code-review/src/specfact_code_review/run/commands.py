"""Command implementation for `specfact code review run`."""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.table import Table

from specfact_code_review.run.findings import EvidenceRef, ReviewFinding, ReviewReport
from specfact_code_review.run.runner import ReviewFocus, run_review


console = Console()
progress_console = Console(stderr=True)
AutoScope = Literal["changed", "full"]
ReviewRunMode = Literal["shadow", "enforce"]
ReviewLevelFilter = Literal["error", "warning"]


class RunCommandError(ValueError):
    """Structured validation error for review run command options."""

    error_code = "run_command_error"


class InvalidOptionCombinationError(RunCommandError):
    error_code = "invalid_option_combination"


class MissingOutForJsonError(RunCommandError):
    error_code = "missing_out_for_json"


class ConflictingScopeError(RunCommandError):
    error_code = "conflicting_scope"


class NoReviewableFilesError(RunCommandError):
    error_code = "no_reviewable_files"


@dataclass(frozen=True)
class ReviewRunRequest:
    """Inputs needed to execute a governed review run."""

    files: list[Path]
    include_tests: bool = False
    scope: AutoScope | None = None
    path_filters: list[Path] | None = None
    include_noise: bool = False
    json_output: bool = False
    out: Path | None = None
    score_only: bool = False
    no_tests: bool = False
    fix: bool = False
    bug_hunt: bool = False
    review_mode: ReviewRunMode = "enforce"
    review_level: ReviewLevelFilter | None = None
    focus_facets: tuple[str, ...] = ()
    review_focus: ReviewFocus | None = None


@dataclass(frozen=True)
class _ReviewLoopFlags:
    no_tests: bool
    include_noise: bool
    fix: bool
    progress_callback: Callable[[str], None] | None
    bug_hunt: bool
    review_mode: ReviewRunMode
    review_level: ReviewLevelFilter | None
    review_focus: ReviewFocus | None


def _is_test_file(file_path: Path) -> bool:
    return "tests" in file_path.parts


def _filter_files_by_focus(files: list[Path], facets: tuple[str, ...]) -> list[Path]:
    """Restrict files to the union of facet selections (Python files only)."""
    file_facets = tuple(facet for facet in facets if facet in {"source", "tests", "docs"})
    if not file_facets:
        return files

    def _matches_focus(file_path: Path, facet: str) -> bool:
        if file_path.suffix not in (".py", ".pyi"):
            return False
        if facet == "tests":
            return _is_test_file(file_path)
        if facet == "docs":
            return "docs" in file_path.parts
        if facet == "source":
            return not _is_test_file(file_path) and "docs" not in file_path.parts
        return False

    return [file_path for file_path in files if any(_matches_focus(file_path, f) for f in file_facets)]


def _is_ignored_review_path(file_path: Path) -> bool:
    parent_parts = file_path.parts[:-1]
    return any(part.startswith(".") and len(part) > 1 for part in parent_parts)


def _git_file_list(command: list[str], *, error_message: str) -> list[Path]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise RunCommandError(error_message)
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _changed_files_from_git_diff(*, include_tests: bool) -> list[Path]:
    tracked_files = _git_file_list(
        ["git", "diff", "HEAD", "--name-only"],
        error_message="Unable to determine changed tracked files from `git diff HEAD --name-only`.",
    )
    untracked_files = _git_file_list(
        ["git", "ls-files", "--others", "--exclude-standard"],
        error_message="Unable to determine untracked files from `git ls-files --others --exclude-standard`.",
    )

    python_files = [
        file_path
        for file_path in [*tracked_files, *untracked_files]
        if file_path.suffix in (".py", ".pyi") and file_path.is_file() and not _is_ignored_review_path(file_path)
    ]
    deduped_python_files = list(dict.fromkeys(python_files))
    if include_tests:
        return deduped_python_files
    return [file_path for file_path in deduped_python_files if not _is_test_file(file_path)]


def _all_python_files_from_git() -> list[Path]:
    tracked_files = _git_file_list(
        ["git", "ls-files", "--cached"],
        error_message="Unable to determine tracked repository files from `git ls-files --cached`.",
    )
    untracked_files = _git_file_list(
        ["git", "ls-files", "--others", "--exclude-standard"],
        error_message="Unable to determine untracked files from `git ls-files --others --exclude-standard`.",
    )
    python_files = [
        file_path
        for file_path in [*tracked_files, *untracked_files]
        if file_path.suffix in (".py", ".pyi") and file_path.is_file() and not _is_ignored_review_path(file_path)
    ]
    return list(dict.fromkeys(python_files))


def _path_filter_matches(file_path: Path, path_filter: Path) -> bool:
    return file_path == path_filter or path_filter in file_path.parents


def _filtered_files(files: Iterable[Path], *, path_filters: list[Path]) -> list[Path]:
    if not path_filters:
        return list(files)
    normalized_filters = [path_filter for path_filter in path_filters if str(path_filter).strip()]
    for path_filter in normalized_filters:
        if path_filter.is_absolute():
            raise RunCommandError(f"Path filters must be repo-relative: {path_filter}")
    return [
        file_path
        for file_path in files
        if any(_path_filter_matches(file_path, path_filter) for path_filter in normalized_filters)
    ]


def _auto_scope_message(*, scope: AutoScope, path_filters: list[Path]) -> str:
    parts = [f"--scope {scope}", *(f"--path {path_filter}" for path_filter in path_filters)]
    return " ".join(parts)


def _raise_if_targeting_styles_conflict(
    files: list[Path],
    *,
    scope: AutoScope | None,
    path_filters: list[Path],
) -> None:
    if files and (scope is not None or path_filters):
        raise ConflictingScopeError("Choose positional files or auto-scope controls, not both.")


def _resolve_positional_files(files: list[Path]) -> list[Path]:
    resolved = [file_path for file_path in files if not _is_ignored_review_path(file_path)]
    if resolved:
        return resolved
    raise NoReviewableFilesError(
        "No Python files to review were provided or detected from tracked or untracked changes."
    )


def _resolve_auto_discovered_files(
    *,
    include_tests: bool,
    scope: AutoScope,
    path_filters: list[Path],
) -> list[Path]:
    if scope == "full":
        return _resolve_full_scope_files(include_tests=include_tests, path_filters=path_filters)
    return _resolve_changed_scope_files(include_tests=include_tests, path_filters=path_filters)


def _resolve_full_scope_files(*, include_tests: bool, path_filters: list[Path]) -> list[Path]:
    resolved = _all_python_files_from_git()
    if not include_tests and not path_filters:
        return [file_path for file_path in resolved if not _is_test_file(file_path)]
    return resolved


def _resolve_changed_scope_files(*, include_tests: bool, path_filters: list[Path]) -> list[Path]:
    changed_include_tests = include_tests or bool(path_filters)
    return _changed_files_from_git_diff(include_tests=changed_include_tests)


def _raise_for_empty_auto_scope(*, scope: AutoScope, path_filters: list[Path]) -> None:
    auto_scope_message = _auto_scope_message(scope=scope, path_filters=path_filters)
    raise NoReviewableFilesError(
        f"No reviewable files matched the selected auto-scope controls ({auto_scope_message}). "
        "Adjust --scope/--path or pass positional files."
    )


def _resolve_files(
    files: list[Path],
    *,
    include_tests: bool,
    scope: AutoScope | None,
    path_filters: list[Path],
) -> list[Path]:
    _raise_if_targeting_styles_conflict(files, scope=scope, path_filters=path_filters)
    if files:
        resolved = _resolve_positional_files(files)
    else:
        selected_scope: AutoScope = scope or "changed"
        resolved = _resolve_auto_discovered_files(
            include_tests=include_tests,
            scope=selected_scope,
            path_filters=path_filters,
        )
        resolved = _filtered_files(resolved, path_filters=path_filters)
        resolved = [file_path for file_path in resolved if not _is_ignored_review_path(file_path)]

    if not resolved:
        _raise_for_empty_auto_scope(scope=scope or "changed", path_filters=path_filters)

    missing = [file_path for file_path in resolved if not file_path.is_file()]
    if missing:
        raise NoReviewableFilesError(f"File not found: {missing[0]}")

    return resolved


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
            progress_callback=_emit_progress,
            bug_hunt=flags.bug_hunt,
            review_mode=flags.review_mode,
            review_level=flags.review_level,
            review_focus=flags.review_focus,
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
            progress_callback=status.update,
            bug_hunt=flags.bug_hunt,
            review_mode=flags.review_mode,
            review_level=flags.review_level,
            review_focus=flags.review_focus,
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
        return report


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
        )
        report = _with_applied_simplification_findings(report, applied_simplification_findings)
    return report


def _as_auto_scope(value: object) -> AutoScope | None:
    if value is None:
        return None
    if isinstance(value, str) and value in {"changed", "full"}:
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
    if value is None or value == "enforce":
        return "enforce"
    if value == "shadow":
        return "shadow"
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

    # Cast the optional parameters to their proper types
    scope = cast(AutoScope | None, scope_value)
    path_filters = cast(list[Path] | None, path_filters_value)
    out = cast(Path | None, out_value)

    focus_facets = cast(tuple[str, ...], _as_focus_facets(request_kwargs.pop("focus_facets", None)))

    request = ReviewRunRequest(
        files=files,
        include_tests=include_tests,
        scope=scope,
        path_filters=path_filters,
        include_noise=_get_bool_param("include_noise"),
        json_output=_get_bool_param("json_output"),
        out=out,
        score_only=_get_bool_param("score_only"),
        no_tests=_get_bool_param("no_tests"),
        fix=_get_bool_param("fix"),
        bug_hunt=_get_bool_param("bug_hunt"),
        review_mode=_as_review_mode(request_kwargs.pop("review_mode", "enforce")),
        review_level=_as_review_level(request_kwargs.pop("review_level", None)),
        focus_facets=focus_facets,
        review_focus=_review_focus_from_facets(focus_facets),
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


def _validate_review_request(request: ReviewRunRequest) -> None:
    if request.json_output and request.score_only:
        raise InvalidOptionCombinationError("Use either --json or --score-only, not both.")
    if not request.json_output and request.out is not None:
        raise MissingOutForJsonError("Use --out together with --json.")


def _normalize_review_request(request: ReviewRunRequest) -> ReviewRunRequest:
    if request.review_focus is not None or "simplify" not in request.focus_facets:
        return request
    return ReviewRunRequest(
        files=request.files,
        include_tests=request.include_tests,
        scope=request.scope,
        path_filters=request.path_filters,
        include_noise=request.include_noise,
        json_output=request.json_output,
        out=request.out,
        score_only=request.score_only,
        no_tests=request.no_tests,
        fix=request.fix,
        bug_hunt=request.bug_hunt,
        review_mode=request.review_mode,
        review_level=request.review_level,
        focus_facets=request.focus_facets,
        review_focus=_review_focus_from_facets(request.focus_facets),
    )


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

    file_focus_facets = tuple(facet for facet in request.focus_facets if facet in {"source", "tests", "docs"})
    include_for_resolve = request.include_tests or bool(file_focus_facets)
    resolved_files = _resolve_files(
        request.files,
        include_tests=include_for_resolve,
        scope=request.scope,
        path_filters=request.path_filters or [],
    )
    resolved_files = _filter_files_by_focus(resolved_files, request.focus_facets)
    if not resolved_files:
        raise NoReviewableFilesError(
            "No reviewable Python files matched the selected --focus facets."
            if request.focus_facets
            else "No Python files to review were provided or detected."
        )

    report = _run_review_with_progress(
        resolved_files,
        _ReviewLoopFlags(
            no_tests=request.no_tests,
            include_noise=request.include_noise,
            fix=request.fix,
            progress_callback=None,
            bug_hunt=request.bug_hunt,
            review_mode=request.review_mode,
            review_level=request.review_level,
            review_focus=request.review_focus,
        ),
    )
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
