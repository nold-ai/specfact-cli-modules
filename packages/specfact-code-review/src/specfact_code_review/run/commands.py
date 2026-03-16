"""Command implementation for `specfact code review run`."""

from __future__ import annotations

import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.table import Table

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.runner import run_review


console = Console()
progress_console = Console(stderr=True)


def _is_test_file(file_path: Path) -> bool:
    return "tests" in file_path.parts


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
        if file_path.suffix == ".py" and file_path.is_file()
    ]
    deduped_python_files = list(dict.fromkeys(python_files))
    if include_tests:
        return deduped_python_files
    return [file_path for file_path in deduped_python_files if not _is_test_file(file_path)]


def _resolve_files(files: list[Path], *, include_tests: bool) -> list[Path]:
    resolved = files or _changed_files_from_git_diff(include_tests=include_tests)
    if not resolved:
        raise ValueError("No Python files to review were provided or detected from tracked or untracked changes.")

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
        console.print("Code Review")
        console.print(report.summary)
    else:
        for category in sorted(grouped):
            table = Table(title=f"Code Review: {category}", show_header=True, header_style="bold cyan")
            table.add_column("File", style="cyan")
            table.add_column("Line", justify="right")
            table.add_column("Tool")
            table.add_column("Rule")
            table.add_column("Severity")
            table.add_column("Message", overflow="fold")
            for finding in grouped[category]:
                row = [
                    finding.file,
                    str(finding.line),
                    finding.tool,
                    finding.rule,
                    finding.severity,
                    finding.message,
                ]
                table.add_row(
                    *row,
                )
            console.print(table)

    console.print(
        f"Verdict: {report.overall_verdict} | CI exit: {report.ci_exit_code} | "
        f"Score: {report.score} | Reward delta: {report.reward_delta}"
    )
    console.print(report.summary)


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
        with progress_console.status("Preparing code review...") as status:
            report = run_review(
                files,
                no_tests=no_tests,
                include_noise=include_noise,
                progress_callback=status.update,
            )
            if fix:
                status.update("Applying Ruff autofixes...")
                _apply_fixes(files)
                status.update("Re-running review after autofixes...")
                report = run_review(
                    files,
                    no_tests=no_tests,
                    include_noise=include_noise,
                    progress_callback=status.update,
                )
            return report

    def _emit_progress(description: str) -> None:
        progress_console.print(f"[dim]{description}[/dim]")

    report = run_review(
        files,
        no_tests=no_tests,
        include_noise=include_noise,
        progress_callback=_emit_progress,
    )
    if fix:
        _emit_progress("Applying Ruff autofixes...")
        _apply_fixes(files)
        _emit_progress("Re-running review after autofixes...")
        report = run_review(
            files,
            no_tests=no_tests,
            include_noise=include_noise,
            progress_callback=_emit_progress,
        )
    return report


@beartype
@require(lambda files: files is None or all(isinstance(file_path, Path) for file_path in files))
@require(
    lambda json_output, score_only: not (json_output and score_only),
    "Use either --json or --score-only, not both.",
)
@require(lambda json_output, out: json_output or out is None, "Use --out together with --json.")
@ensure(lambda result: isinstance(result, tuple))
def run_command(
    files: list[Path] | None = None,
    *,
    include_tests: bool = False,
    include_noise: bool = False,
    json_output: bool = False,
    out: Path | None = None,
    score_only: bool = False,
    no_tests: bool = False,
    fix: bool = False,
) -> tuple[int, str | None]:
    """Execute a governed review run over the provided files."""
    resolved_files = _resolve_files(files or [], include_tests=include_tests)
    report = _run_review_with_progress(
        resolved_files,
        no_tests=no_tests,
        include_noise=include_noise,
        fix=fix,
    )

    if json_output:
        output_path = _json_output_path(out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.model_dump_json(), encoding="utf-8")
        return report.ci_exit_code or 0, str(output_path)
    if score_only:
        return report.ci_exit_code or 0, str(report.reward_delta)

    _render_report(report)
    return report.ci_exit_code or 0, None


__all__ = ["run_command"]
