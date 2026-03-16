"""Review subgroup wiring for the code command surface."""

from __future__ import annotations

from pathlib import Path

import typer
from icontract.errors import ViolationError

from specfact_code_review.ledger.commands import app as ledger_app
from specfact_code_review.rules.commands import app as rules_app
from specfact_code_review.run.commands import run_command


app = typer.Typer(help="Code command extensions for structured review workflows.", no_args_is_help=True)
review_app = typer.Typer(help="Governed code review workflows.", no_args_is_help=True)


def _friendly_run_command_error(exc: ValueError | ViolationError) -> str:
    message = str(exc)
    for expected in (
        "Use either --json or --score-only, not both.",
        "Use --out together with --json.",
    ):
        if expected in message:
            return expected
    return message


def _resolve_include_tests(*, files: list[Path], include_tests: bool | None, interactive: bool) -> bool:
    if include_tests is not None:
        return include_tests
    if files:
        return True
    if not interactive:
        return False
    return typer.confirm("Include changed and untracked test files in this review?", default=False)


@review_app.command("run")
def _run(
    files: list[Path] = typer.Argument(None, metavar="FILES..."),
    include_tests: bool | None = typer.Option(
        None,
        "--include-tests/--exclude-tests",
        help="Include changed test files when review scope is auto-detected from git diff.",
    ),
    include_noise: bool = typer.Option(
        False,
        "--include-noise/--suppress-noise",
        help="Include known low-signal findings such as test-scope contract noise.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Write ReviewReport JSON to a file. Use --out to override the default path.",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="JSON output file path used with --json. Default: review-report.json.",
    ),
    score_only: bool = typer.Option(False, "--score-only", help="Print only the reward delta integer."),
    no_tests: bool = typer.Option(False, "--no-tests", help="Skip the TDD gate."),
    fix: bool = typer.Option(False, "--fix", help="Apply Ruff autofixes and re-run the review."),
    interactive: bool = typer.Option(False, "--interactive", help="Ask review-scope questions before running."),
) -> None:
    """Execute code review runs."""
    try:
        resolved_include_tests = _resolve_include_tests(
            files=files,
            include_tests=include_tests,
            interactive=interactive,
        )
        exit_code, output = run_command(
            files,
            include_tests=resolved_include_tests,
            include_noise=include_noise,
            json_output=json_output,
            out=out,
            score_only=score_only,
            no_tests=no_tests,
            fix=fix,
        )
    except (ValueError, ViolationError) as exc:
        raise typer.BadParameter(_friendly_run_command_error(exc)) from exc
    if output is not None:
        typer.echo(output)
    raise typer.Exit(code=exit_code)


review_app.add_typer(ledger_app, name="ledger")
review_app.add_typer(rules_app, name="rules")
app.add_typer(review_app, name="review")

__all__ = ["app", "review_app"]
