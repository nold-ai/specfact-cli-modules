"""Review subgroup wiring for the code command surface.

Operating guidance: command examples in this source are not the source of
truth; CLI help is authoritative. Check `specfact code review run --help`,
and ask the user before guessing when help output disagrees.
"""

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
    ReviewRunMode,
    RunCommandError,
    run_command,
)


app = typer.Typer(help="Code command extensions for structured review workflows.", no_args_is_help=True)
review_app = typer.Typer(help="Governed code review workflows.", no_args_is_help=True)

_RUN_INSTRUCTIONS = """\
SpecFact code review instructions for AI assistants

Use this when the user asks to remove AI bloat, simplify code, apply clean-code patterns, reduce boilerplate, or act on SpecFact review findings.

For merge-quality authority, run:
   specfact code review run --scope range --base-ref <full-base-ref> --head-ref <full-head-ref> --pr-context-file <event-derived-absolute-path> --enforcement full
A local range run without matching claimed context is range_preview; one with matching claimed context is range_candidate. Neither is pr_range until the protected consumer independently verifies and promotes the evidence.

1. Generate evidence first:
   specfact code review run --scope changed --enforcement shadow --focus simplify --preview-fixes --json --out .specfact/code-review.json

   Keep the canonical .specfact/code-review.json path unless every downstream consumer has been updated to read a custom simplify report path.

   If the worktree is clean on a PR branch and --scope changed finds no files, review the branch-delta Python files as explicit positional files and omit --scope. Find them with the PR base ref, for example: git diff --name-only <base-ref>...HEAD -- '*.py' '*.pyi'

2. Inspect cleanup_forecast before editing. Use reviewed_loc, estimated_deletion_lines, ai_bloat_index, and by_guidance_kind to decide where cleanup will actually pay off. These estimates are cleanup forecasts, not guarantees.

3. Sort findings by guidance_kind before editing, then treat guidance_kind and remediation_packet as the action contract:
   - safe_mechanical: apply only after local safety checks pass.
   - needs_tests: add or identify targeted tests before changing behavior.
   - design_judgment: inspect intent evidence and ask before editing.
   - preserve: keep by default and record preserve_reason.
   Findings without guidance_kind are unguided advisories: summarize them separately, do not auto-apply them, and ask before using them as refactor input.
   Prefer each finding's remediation_packet over prose instructions because the JSON report is the portable AI IDE handoff contract.

4. For vibe-coder or junior users, present each finding as a decision card:
   Finding, plain-language issue, why it might need to stay, exact patch preview or small before/after proposal, validation plan, recommended choice.

5. For design_judgment findings, check API, callback, framework hook, adapter, public symbol, CLI boundary, compatibility shim, and readability intent. If intent is unclear, default to keep or skip.

6. Apply one file at a time. After each accepted file or very small batch, run targeted tests or rerun:
   specfact code review run --scope changed --enforcement shadow --focus simplify --json --out .specfact/code-review.json

7. Log every action as recommended, applied, kept, skipped, or failed with evidence. Never batch-apply design_judgment findings just because the patch is shorter. Never treat ai_bloat findings as proof of AI authorship; they are cleanup signals only, not proof of AI authorship.
"""


@dataclass(frozen=True)
class _ReviewRunCliInputs:
    files: list[Path] | None
    include_tests: bool | None
    exclude_tests: bool | None
    focus: list[str] | None
    include_noise: bool
    suppress_noise: bool
    interactive: bool


@dataclass(frozen=True)
class _ReviewRunCommandInputs:
    ctx: typer.Context
    files: list[Path] | None
    scope: Literal["changed", "worktree", "index", "range", "full"] | None
    path: list[Path] | None
    base_ref: str | None
    head_ref: str | None
    pr_context_file: Path | None
    include_tests: bool | None
    exclude_tests: bool | None
    focus: list[str] | None
    enforcement: ReviewRunMode
    mode: Literal["shadow", "enforce"] | None
    level: Literal["error", "warning"] | None
    bug_hunt: bool
    include_noise: bool
    suppress_noise: bool
    json_output: bool
    out: Path | None
    score_only: bool
    no_tests: bool
    fix: bool
    preview_fixes: bool
    with_mutation: bool
    requirements_evidence: Path | None
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


def _resolve_cli_enforcement(
    *, enforcement: ReviewRunMode, legacy_mode: Literal["shadow", "enforce"] | None
) -> ReviewRunMode:
    """Resolve new enforcement policy with backward-compatible --mode support."""
    if legacy_mode is None:
        return enforcement
    if enforcement != "changed":
        raise typer.BadParameter("Use either --enforcement or deprecated --mode, not both.")
    return "shadow" if legacy_mode == "shadow" else "full"


def _enforcement_was_defaulted(ctx: typer.Context) -> bool:
    """Return whether Click supplied the default --enforcement value."""
    get_parameter_source = getattr(ctx, "get_parameter_source", None)
    if not callable(get_parameter_source):
        return False
    source = get_parameter_source("enforcement")
    return getattr(source, "name", None) == "DEFAULT"


def _enforcement_was_explicit(ctx: typer.Context) -> bool:
    """Return whether the caller supplied --enforcement explicitly."""
    get_parameter_source = getattr(ctx, "get_parameter_source", None)
    if not callable(get_parameter_source):
        return False
    source = get_parameter_source("enforcement")
    return source is not None and getattr(source, "name", None) != "DEFAULT"


def _resolve_command_review_mode(inputs: _ReviewRunCommandInputs) -> tuple[ReviewRunMode, bool]:
    """Resolve the effective enforcement mode and whether Click supplied it."""
    enforcement_defaulted = _enforcement_was_defaulted(inputs.ctx)
    if inputs.mode is not None and _enforcement_was_explicit(inputs.ctx):
        raise typer.BadParameter("Use only one of --mode or --enforcement; --mode is deprecated.")
    review_mode = _resolve_cli_enforcement(enforcement=inputs.enforcement, legacy_mode=inputs.mode)
    if inputs.scope == "range" and inputs.mode is None and enforcement_defaulted:
        review_mode = "full"
    return review_mode, enforcement_defaulted


def _should_warn_about_default_enforcement(inputs: _ReviewRunCommandInputs, enforcement_defaulted: bool) -> bool:
    return (
        inputs.mode is None
        and inputs.enforcement == "changed"
        and enforcement_defaulted
        and inputs.scope != "range"
        and not inputs.json_output
        and not inputs.score_only
    )


def _execute_review_run(inputs: _ReviewRunCommandInputs) -> None:
    review_mode, enforcement_defaulted = _resolve_command_review_mode(inputs)
    if _should_warn_about_default_enforcement(inputs, enforcement_defaulted):
        typer.echo(
            "Code review enforcement default is 'changed'; use '--enforcement full' for strict CI gates "
            "or '--enforcement shadow' for evidence-only runs.",
            err=True,
        )
    focus_list, resolved_include_tests, resolved_include_noise = _resolve_review_run_flags(
        _ReviewRunCliInputs(
            files=inputs.files,
            include_tests=inputs.include_tests,
            exclude_tests=inputs.exclude_tests,
            focus=inputs.focus,
            include_noise=inputs.include_noise,
            suppress_noise=inputs.suppress_noise,
            interactive=inputs.interactive,
        )
    )
    if inputs.scope == "range" and inputs.include_tests is None and inputs.exclude_tests is None:
        resolved_include_tests = True

    try:
        exit_code, output = run_command(
            inputs.files or [],
            include_tests=resolved_include_tests,
            scope=inputs.scope,
            path_filters=inputs.path,
            base_ref=inputs.base_ref,
            head_ref=inputs.head_ref,
            pr_context_file=inputs.pr_context_file,
            focus_facets=tuple(focus_list),
            review_mode=review_mode,
            review_level=inputs.level,
            bug_hunt=inputs.bug_hunt,
            include_noise=resolved_include_noise,
            json_output=inputs.json_output,
            out=inputs.out,
            score_only=inputs.score_only,
            no_tests=inputs.no_tests,
            fix=inputs.fix,
            preview_fixes=inputs.preview_fixes,
            with_mutation=inputs.with_mutation,
            requirements_evidence=inputs.requirements_evidence,
        )
    except (ValueError, ViolationError) as exc:
        raise typer.BadParameter(_friendly_run_command_error(exc)) from exc
    if output is not None:
        typer.echo(output)
    raise typer.Exit(code=exit_code)


@review_app.command("run")
@require(lambda ctx: True, "run command validation")
@ensure(lambda result: result is None, "run command does not return")
def run(
    ctx: typer.Context,
    files: list[Path] = typer.Argument(None),
    scope: Literal["changed", "worktree", "index", "range", "full"] = typer.Option(None),
    path: list[Path] = typer.Option(None, "--path"),
    base_ref: str | None = typer.Option(
        None,
        "--base-ref",
        help="Full target/base ref for immutable range resolution.",
    ),
    head_ref: str | None = typer.Option(
        None,
        "--head-ref",
        help="Full candidate/head ref for immutable range resolution.",
    ),
    pr_context_file: Path | None = typer.Option(
        None,
        "--pr-context-file",
        help="Absolute, event-derived GitHub Actions PR/merge-queue context JSON.",
    ),
    include_tests: bool | None = typer.Option(None, "--include-tests"),
    exclude_tests: bool | None = typer.Option(None, "--exclude-tests"),
    focus: list[str] | None = typer.Option(
        None,
        "--focus",
        help="Limit to source, tests, docs, and/or simplify (repeatable).",
    ),
    enforcement: ReviewRunMode = typer.Option(
        "changed",
        "--enforcement",
        help="Enforcement policy: full blocks all findings; changed blocks changed-line findings; shadow reports only.",
    ),
    mode: Literal["shadow", "enforce"] | None = typer.Option(
        None,
        "--mode",
        help="Deprecated alias: enforce maps to --enforcement full; shadow maps to --enforcement shadow.",
    ),
    level: Literal["error", "warning"] | None = typer.Option(None, "--level"),
    bug_hunt: bool = typer.Option(False, "--bug-hunt"),
    include_noise: bool = typer.Option(False, "--include-noise"),
    suppress_noise: bool = typer.Option(False, "--suppress-noise"),
    json_output: bool = typer.Option(False, "--json"),
    out: Path = typer.Option(None, "--out"),
    score_only: bool = typer.Option(False, "--score-only"),
    no_tests: bool = typer.Option(False, "--no-tests"),
    fix: bool = typer.Option(False, "--fix"),
    preview_fixes: bool = typer.Option(
        False,
        "--preview-fixes",
        help="Preview supported safe-mechanical simplify fixes without editing tracked files.",
    ),
    with_mutation: bool = typer.Option(
        False,
        "--with-mutation",
        help="Record opt-in mutation proof evidence for simplify cleanup candidates.",
    ),
    requirements_evidence: Path | None = typer.Option(
        None,
        "--requirements-evidence",
        help="Finalized Requirements proof JSON retained as independent review context.",
    ),
    interactive: bool = typer.Option(False, "--interactive"),
    instructions: bool = typer.Option(
        False,
        "--instructions",
        help="Print AI-facing instructions for guided simplify / clean-code review and exit.",
    ),
) -> None:
    """Run the full code review workflow."""
    _ = ctx.resilient_parsing
    if instructions:
        typer.echo(_RUN_INSTRUCTIONS)
        raise typer.Exit(code=0)
    _execute_review_run(
        _ReviewRunCommandInputs(
            ctx=ctx,
            files=files,
            scope=scope,
            path=path,
            base_ref=base_ref,
            head_ref=head_ref,
            pr_context_file=pr_context_file,
            include_tests=include_tests,
            exclude_tests=exclude_tests,
            focus=focus,
            enforcement=enforcement,
            mode=mode,
            level=level,
            bug_hunt=bug_hunt,
            include_noise=include_noise,
            suppress_noise=suppress_noise,
            json_output=json_output,
            out=out,
            score_only=score_only,
            no_tests=no_tests,
            fix=fix,
            preview_fixes=preview_fixes,
            with_mutation=with_mutation,
            requirements_evidence=requirements_evidence,
            interactive=interactive,
        )
    )


review_app.add_typer(ledger_app, name="ledger")
review_app.add_typer(rules_app, name="rules")
app.add_typer(review_app, name="review")

__all__ = ["app", "review_app"]
