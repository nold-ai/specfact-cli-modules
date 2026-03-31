"""Review subgroup wiring for the code command surface."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import typer
from icontract import ensure, require
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
        "Choose positional files or auto-scope controls, not both.",
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
@require(lambda ctx: True, "run command validation")
@ensure(lambda result: result is None, "run command does not return")
def run(
    ctx: typer.Context,
    files: list[Path] = typer.Argument(None),
    scope: Literal["changed", "full"] = typer.Option(None),
    path: list[Path] = typer.Option(None, "--path"),
    include_tests: bool = typer.Option(None, "--include-tests"),
    exclude_tests: bool = typer.Option(None, "--exclude-tests"),
    include_noise: bool = typer.Option(False, "--include-noise"),
    suppress_noise: bool = typer.Option(False, "--suppress-noise"),
    json_output: bool = typer.Option(False, "--json"),
    out: Path = typer.Option(None, "--out"),
    score_only: bool = typer.Option(False, "--score-only"),
    no_tests: bool = typer.Option(False, "--no-tests"),
    fix: bool = typer.Option(False, "--fix"),
    interactive: bool = typer.Option(False, "--interactive"),
) -> None:
    """Run the full code review workflow."""
    # Resolve mutually exclusive test inclusion options
    if include_tests is not None and exclude_tests is not None:
        raise typer.BadParameter("Cannot use both --include-tests and --exclude-tests")

    resolved_include_tests = _resolve_include_tests(
        files=files or [],
        include_tests=include_tests,
        interactive=interactive,
    )

    # Resolve noise inclusion (suppress-noise takes precedence)
    resolved_include_noise = include_noise and not suppress_noise

    try:
        exit_code, output = run_command(
            files or [],
            include_tests=resolved_include_tests,
            scope=scope,
            path_filters=path,
            include_noise=resolved_include_noise,
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
