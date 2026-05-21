"""Review subgroup wiring for the code command surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer
from icontract import ensure, require
from icontract.errors import ViolationError

from specfact_code_review.ledger.commands import app as ledger_app
from specfact_code_review.rules.commands import app as rules_app
from specfact_code_review.run.commands import (
    ConflictingScopeError,
    InvalidOptionCombinationError,
    MissingOutForJsonError,
    NoReviewableFilesError,
    RunCommandError,
    run_command,
)


app = typer.Typer(help="Code command extensions for structured review workflows.", no_args_is_help=True)
review_app = typer.Typer(help="Governed code review workflows.", no_args_is_help=True)


@dataclass(frozen=True)
class _ReviewRunCliInputs:
    files: list[Path] | None
    include_tests: bool | None
    exclude_tests: bool | None
    focus: list[str] | None
    include_noise: bool
    suppress_noise: bool
    interactive: bool


def _friendly_run_command_error(exc: RunCommandError | ValueError | ViolationError) -> str:
    if isinstance(
        exc,
        (
            InvalidOptionCombinationError,
            MissingOutForJsonError,
            ConflictingScopeError,
            NoReviewableFilesError,
        ),
    ):
        return str(exc)
    return str(exc)


def _resolve_include_tests(*, files: list[Path], include_tests: bool | None, interactive: bool) -> bool:
    if include_tests is not None:
        return include_tests
    if files:
        return True
    if not interactive:
        return False
    return typer.confirm("Include changed and untracked test files in this review?", default=False)


def _validate_focus_flags(inputs: _ReviewRunCliInputs) -> list[str]:
    if inputs.include_tests is not None and inputs.exclude_tests is not None:
        raise typer.BadParameter("Cannot use both --include-tests and --exclude-tests")

    focus_list = list(inputs.focus) if inputs.focus else []
    if focus_list:
        if inputs.include_tests is not None or inputs.exclude_tests is not None:
            raise typer.BadParameter("Cannot combine --focus with --include-tests or --exclude-tests")
        unknown = [facet for facet in focus_list if facet not in {"source", "tests", "docs", "simplify"}]
        if unknown:
            raise typer.BadParameter(f"Invalid --focus value(s): {unknown!r}; use source, tests, docs, or simplify.")
    return focus_list


def _resolve_review_run_flags(inputs: _ReviewRunCliInputs) -> tuple[list[str], bool, bool]:
    focus_list = _validate_focus_flags(inputs)
    if focus_list:
        return focus_list, "tests" in focus_list, inputs.include_noise and not inputs.suppress_noise
    resolved_include_tests = _resolve_include_tests(
        files=inputs.files or [],
        include_tests=inputs.include_tests,
        interactive=inputs.interactive,
    )
    if inputs.exclude_tests is True:
        resolved_include_tests = False
    return focus_list, resolved_include_tests, inputs.include_noise and not inputs.suppress_noise


@review_app.command("run")
@require(lambda ctx: True, "run command validation")
@ensure(lambda result: result is None, "run command does not return")
def run(
    ctx: typer.Context,
    files: list[Path] = typer.Argument(None),
    scope: Literal["changed", "full"] = typer.Option(None),
    path: list[Path] = typer.Option(None, "--path"),
    include_tests: bool | None = typer.Option(None, "--include-tests"),
    exclude_tests: bool | None = typer.Option(None, "--exclude-tests"),
    focus: list[str] | None = typer.Option(None, "--focus", help="Limit to source, tests, and/or docs (repeatable)."),
    mode: Literal["shadow", "enforce"] = typer.Option("enforce", "--mode"),
    level: Literal["error", "warning"] | None = typer.Option(None, "--level"),
    bug_hunt: bool = typer.Option(False, "--bug-hunt"),
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
    _ = ctx.resilient_parsing
    focus_list, resolved_include_tests, resolved_include_noise = _resolve_review_run_flags(
        _ReviewRunCliInputs(
            files=files,
            include_tests=include_tests,
            exclude_tests=exclude_tests,
            focus=focus,
            include_noise=include_noise,
            suppress_noise=suppress_noise,
            interactive=interactive,
        )
    )

    try:
        exit_code, output = run_command(
            files or [],
            include_tests=resolved_include_tests,
            scope=scope,
            path_filters=path,
            focus_facets=tuple(focus_list),
            review_mode=mode,
            review_level=level,
            bug_hunt=bug_hunt,
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
