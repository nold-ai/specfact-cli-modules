"""Command surface for `specfact code review run`."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specfact_code_review.run.findings import ReviewReport
from specfact_code_review.run.runner import run_review


app = typer.Typer(help="Execute code review runs.", no_args_is_help=False)
console = Console()


def _changed_files_from_git_diff() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "HEAD", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise typer.BadParameter("Unable to determine changed files from `git diff HEAD --name-only`.")

    files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    return [file_path for file_path in files if file_path.suffix == ".py" and file_path.is_file()]


def _resolve_files(files: list[Path]) -> list[Path]:
    resolved = files or _changed_files_from_git_diff()
    if not resolved:
        raise typer.BadParameter("No Python files to review were provided or detected from git diff HEAD.")

    missing = [file_path for file_path in resolved if not file_path.is_file()]
    if missing:
        raise typer.BadParameter(f"File not found: {missing[0]}")

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
    grouped: dict[str, list[object]] = defaultdict(list)
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
                table.add_row(
                    finding.file,
                    str(finding.line),
                    finding.tool,
                    finding.rule,
                    finding.severity,
                    finding.message,
                )
            console.print(table)

    console.print(
        f"Verdict: {report.overall_verdict} | CI exit: {report.ci_exit_code} | "
        f"Score: {report.score} | Reward delta: {report.reward_delta}"
    )
    console.print(report.summary)


@app.callback(invoke_without_command=True)
def run_callback(
    files: list[Path] = typer.Argument(None, metavar="FILES..."),
    json_output: bool = typer.Option(False, "--json", help="Emit ReviewReport JSON to stdout."),
    score_only: bool = typer.Option(False, "--score-only", help="Print only the reward delta integer."),
    no_tests: bool = typer.Option(False, "--no-tests", help="Skip the TDD gate."),
    fix: bool = typer.Option(False, "--fix", help="Apply Ruff autofixes and re-run the review."),
    rules_path: Path | None = typer.Option(None, "--rules", help="Optional house-rules skill path."),
) -> None:
    """Execute a governed review run over the provided files."""
    if json_output and score_only:
        raise typer.BadParameter("Use either --json or --score-only, not both.")
    if rules_path is not None and not rules_path.exists():
        raise typer.BadParameter(f"Rules path not found: {rules_path}")

    resolved_files = _resolve_files(files)
    report = run_review(resolved_files, no_tests=no_tests)
    if fix:
        _apply_fixes(resolved_files)
        report = run_review(resolved_files, no_tests=no_tests)

    if json_output:
        typer.echo(report.model_dump_json())
    elif score_only:
        typer.echo(str(report.reward_delta))
    else:
        _render_report(report)

    raise typer.Exit(code=report.ci_exit_code or 0)


__all__ = ["app"]
