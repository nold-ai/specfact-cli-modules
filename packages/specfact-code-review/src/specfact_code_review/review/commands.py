"""Review subgroup wiring for the code command surface."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click
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


@dataclass(frozen=True)
class _RunInvocation:
    files: list[Path]
    scope: Literal["changed", "full"] | None
    path_filters: list[Path] | None
    include_tests: bool | None
    include_noise: bool
    json_output: bool
    out: Path | None
    score_only: bool
    no_tests: bool
    fix: bool
    interactive: bool


def _parse_run_invocation(arguments: list[str]) -> _RunInvocation:
    parser = argparse.ArgumentParser(prog="specfact code review run", add_help=False, allow_abbrev=False)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--scope", choices=("changed", "full"))
    parser.add_argument("--path", dest="path_filters", action="append", type=Path, default=None)

    include_tests_group = parser.add_mutually_exclusive_group()
    include_tests_group.add_argument("--include-tests", dest="include_tests", action="store_true")
    include_tests_group.add_argument("--exclude-tests", dest="include_tests", action="store_false")
    parser.set_defaults(include_tests=None)

    include_noise_group = parser.add_mutually_exclusive_group()
    include_noise_group.add_argument("--include-noise", dest="include_noise", action="store_true")
    include_noise_group.add_argument("--suppress-noise", dest="include_noise", action="store_false")
    parser.set_defaults(include_noise=False)

    parser.add_argument("--json", dest="json_output", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--score-only", dest="score_only", action="store_true")
    parser.add_argument("--no-tests", dest="no_tests", action="store_true")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parsed = parser.parse_args(arguments)
    return _RunInvocation(
        files=parsed.files,
        scope=parsed.scope,
        path_filters=parsed.path_filters,
        include_tests=parsed.include_tests,
        include_noise=parsed.include_noise,
        json_output=parsed.json_output,
        out=parsed.out,
        score_only=parsed.score_only,
        no_tests=parsed.no_tests,
        fix=parsed.fix,
        interactive=parsed.interactive,
    )


@review_app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
@require(lambda ctx: isinstance(ctx, click.Context), "ctx must be a Click context")
@ensure(lambda result: result is None, "run command does not return")
def run(ctx: click.Context) -> None:
    """Run the full code review workflow."""
    try:
        invocation = _parse_run_invocation(list(ctx.args))
        resolved_include_tests = _resolve_include_tests(
            files=invocation.files,
            include_tests=invocation.include_tests,
            interactive=invocation.interactive,
        )
        exit_code, output = run_command(
            invocation.files,
            include_tests=resolved_include_tests,
            scope=invocation.scope,
            path_filters=invocation.path_filters,
            include_noise=invocation.include_noise,
            json_output=invocation.json_output,
            out=invocation.out,
            score_only=invocation.score_only,
            no_tests=invocation.no_tests,
            fix=invocation.fix,
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
