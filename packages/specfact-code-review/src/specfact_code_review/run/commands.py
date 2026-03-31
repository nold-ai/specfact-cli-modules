"""Command implementation for `specfact code review run`."""

from __future__ import annotations

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

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.runner import run_review


console = Console()
progress_console = Console(stderr=True)
AutoScope = Literal["changed", "full"]


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


def _is_test_file(file_path: Path) -> bool:
    return "tests" in file_path.parts


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
        raise ValueError(error_message)
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
        if file_path.suffix == ".py" and file_path.is_file() and not _is_ignored_review_path(file_path)
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
        if file_path.suffix == ".py" and file_path.is_file() and not _is_ignored_review_path(file_path)
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
            raise ValueError(f"Path filters must be repo-relative: {path_filter}")
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
        raise ValueError("Choose positional files or auto-scope controls, not both.")


def _resolve_positional_files(files: list[Path]) -> list[Path]:
    resolved = [file_path for file_path in files if not _is_ignored_review_path(file_path)]
    if resolved:
        return resolved
    raise ValueError("No Python files to review were provided or detected from tracked or untracked changes.")


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
    raise ValueError(
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
        raise ValueError(f"File not found: {missing[0]}")

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
    *,
    no_tests: bool,
    include_noise: bool,
    fix: bool,
) -> ReviewReport:
    if _is_interactive_terminal():
        return _run_review_with_status(files, no_tests=no_tests, include_noise=include_noise, fix=fix)

    def _emit_progress(description: str) -> None:
        progress_console.print(f"[dim]{description}[/dim]")

    return _run_review_once(
        files,
        no_tests=no_tests,
        include_noise=include_noise,
        fix=fix,
        progress_callback=_emit_progress,
    )


def _run_review_with_status(
    files: list[Path],
    *,
    no_tests: bool,
    include_noise: bool,
    fix: bool,
) -> ReviewReport:
    with progress_console.status("Preparing code review...") as status:
        report = _run_review_once(
            files,
            no_tests=no_tests,
            include_noise=include_noise,
            fix=False,
            progress_callback=status.update,
        )
        if fix:
            status.update("Applying Ruff autofixes...")
            _apply_fixes(files)
            status.update("Re-running review after autofixes...")
            report = _run_review_once(
                files,
                no_tests=no_tests,
                include_noise=include_noise,
                fix=False,
                progress_callback=status.update,
            )
        return report


def _run_review_once(
    files: list[Path],
    *,
    no_tests: bool,
    include_noise: bool,
    fix: bool,
    progress_callback: Callable[[str], None] | None,
) -> ReviewReport:
    report = run_review(
        files,
        no_tests=no_tests,
        include_noise=include_noise,
        progress_callback=progress_callback,
    )
    if fix:
        if progress_callback is not None:
            progress_callback("Applying Ruff autofixes...")
        else:
            progress_console.print("[dim]Applying Ruff autofixes...[/dim]")
        _apply_fixes(files)
        if progress_callback is not None:
            progress_callback("Re-running review after autofixes...")
        else:
            progress_console.print("[dim]Re-running review after autofixes...[/dim]")
        report = run_review(
            files,
            no_tests=no_tests,
            include_noise=include_noise,
            progress_callback=progress_callback,
        )
    return report


def _as_auto_scope(value: object) -> AutoScope | None:
    if value is None:
        return None
    if isinstance(value, str) and value in {"changed", "full"}:
        return cast(AutoScope, value)
    raise ValueError(f"Invalid scope value: {value!r}")


def _as_path_filters(value: object) -> list[Path] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(path_filter, Path) for path_filter in value):
        return value
    raise ValueError("Path filters must be a list of Path instances.")


def _as_optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    raise ValueError("Output path must be a Path instance.")


def _build_review_run_request(
    files: list[Path],
    kwargs: dict[str, object],
) -> ReviewRunRequest:
    # Validate files is a list of Path instances
    if not isinstance(files, list):
        raise ValueError(f"files must be a list, got {type(files).__name__}")
    if not all(isinstance(file_path, Path) for file_path in files):
        raise ValueError("files must contain only Path instances")

    request_kwargs = dict(kwargs)

    # Validate and extract known boolean flags with proper type checking
    def _get_bool_param(name: str, default: bool = False) -> bool:
        value = request_kwargs.pop(name, default)
        if value is None:
            return default
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean, got {type(value).__name__}")
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
            raise ValueError(f"include_tests must be a boolean, got {type(include_tests_value).__name__}")
        include_tests = include_tests_value

    # Get optional parameters with proper type casting
    scope_value = _get_optional_param("scope", _as_auto_scope)
    path_filters_value = _get_optional_param("path_filters", _as_path_filters)
    out_value = _get_optional_param("out", _as_optional_path)

    # Cast the optional parameters to their proper types
    scope = cast(AutoScope | None, scope_value)
    path_filters = cast(list[Path] | None, path_filters_value)
    out = cast(Path | None, out_value)

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
    )

    # Reject any unexpected keyword arguments
    if request_kwargs:
        unexpected = ", ".join(sorted(request_kwargs))
        raise ValueError(f"Unexpected keyword arguments: {unexpected}")

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
        raise ValueError("Use either --json or --score-only, not both.")
    if not request.json_output and request.out is not None:
        raise ValueError("Use --out together with --json.")


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
    _validate_review_request(request)

    resolved_files = _resolve_files(
        request.files,
        include_tests=request.include_tests,
        scope=request.scope,
        path_filters=request.path_filters or [],
    )
    report = _run_review_with_progress(
        resolved_files,
        no_tests=request.no_tests,
        include_noise=request.include_noise,
        fix=request.fix,
    )
    return _render_review_result(report, request)


__all__ = ["ReviewRunRequest", "run_command"]
