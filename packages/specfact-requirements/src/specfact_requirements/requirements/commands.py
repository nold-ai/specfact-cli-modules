"""Command handlers for requirement context evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from beartype import beartype
from icontract import ensure, require

from specfact_requirements.requirements.evidence import write_requirements_evidence
from specfact_requirements.requirements.lifecycle import ReconciliationContext, reconcile_junit
from specfact_requirements.requirements.runtime import (
    auto_detect_openspec_change,
    auto_detect_speckit_feature,
    import_native_requirements_to_bundle,
    import_requirements_file_to_bundle,
    import_result_has_errors,
    inspect_requirements_bundle_coverage,
    is_requirement_context_profile_supported,
    list_requirements_with_coverage,
    requirements_gate_finding_counts,
    validate_requirements_bundle,
)


class OutputFormat(StrEnum):
    """Supported command output formats."""

    JSON = "json"
    TEXT = "text"


class RequiredMaturity(StrEnum):
    """Lifecycle maturity values accepted by the evidence command."""

    PLANNED = "planned"
    ACCEPTED = "accepted"
    TEST_AUTHORED = "test-authored"
    RED = "red"
    VERIFIED = "verified"


app = typer.Typer(
    help="Import, validate, and inspect requirement context evidence.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help", "--help-advanced", "-ha"]},
)


def _format_supported(output_format: OutputFormat) -> bool:
    return output_format in {OutputFormat.JSON, OutputFormat.TEXT}


@beartype
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def _emit_payload(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


def _selected_import_source(from_file: Path | None, from_openspec: bool, from_speckit: bool) -> str:
    selected = [
        name
        for name, enabled in (
            ("file", from_file is not None),
            ("openspec", from_openspec),
            ("speckit", from_speckit),
        )
        if enabled
    ]
    if len(selected) != 1:
        raise typer.BadParameter("choose exactly one of --from-file, --from-openspec, or --from-speckit")
    return selected[0]


@app.command("import", help="Import local, OpenSpec, or Spec Kit requirement evidence into a project bundle.")
@require(lambda bundle: bundle.is_dir(), "bundle must exist")
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def import_command(
    ctx: typer.Context,
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False, dir_okay=True, readable=True, writable=True),
    ],
    source_path: Annotated[
        Path | None,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Optional OpenSpec change or Spec Kit feature directory.",
        ),
    ] = None,
    from_file: Annotated[
        Path | None,
        typer.Option(
            "--from-file", exists=True, file_okay=True, dir_okay=False, readable=True, help="JSON/YAML records."
        ),
    ] = None,
    from_openspec: Annotated[
        bool,
        typer.Option(
            "--from-openspec", help="Import one OpenSpec change; an optional positional path overrides auto-detection."
        ),
    ] = False,
    from_speckit: Annotated[
        bool,
        typer.Option(
            "--from-speckit", help="Import one Spec Kit feature; an optional positional path overrides auto-detection."
        ),
    ] = False,
    output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format.")] = OutputFormat.TEXT,
) -> None:
    """Import one source of requirement evidence into a project bundle."""
    del ctx  # Typer injects the Click context so the command remains compatible with context-aware tooling.
    source_name = _selected_import_source(from_file, from_openspec, from_speckit)
    if source_name == "file":
        if source_path is not None:
            raise typer.BadParameter("--from-file does not accept a positional source path")
        if from_file is None:
            raise typer.BadParameter("--from-file requires a path")
        result = import_requirements_file_to_bundle(from_file, bundle)
    else:
        source_dir = source_path
        if source_dir is None:
            source_dir = (
                auto_detect_openspec_change(Path.cwd())
                if source_name == "openspec"
                else auto_detect_speckit_feature(Path.cwd())
            )
        result = import_native_requirements_to_bundle(
            source_name,
            source_dir,
            bundle,
        )
    _emit_payload(
        {
            "imported": len(result.requirements),
            "diagnostics": [diagnostic.model_dump(mode="json") for diagnostic in result.diagnostics],
        },
        output_format,
    )
    if import_result_has_errors(result):
        raise typer.Exit(1)


@app.command("validate", help="Validate requirement context evidence usefulness.")
@beartype
@require(lambda bundle: bundle.is_dir(), "bundle must exist")
@require(
    lambda profile: profile is None or is_requirement_context_profile_supported(profile),
    "profile must be a known requirement context profile when provided",
)
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def validate_command(
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False, dir_okay=True, readable=True),
    ],
    profile: Annotated[
        str | None, typer.Option("--profile", help="Validation profile; omit to use layered configuration.")
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format.")] = OutputFormat.TEXT,
) -> None:
    """Validate requirement context evidence usefulness."""
    report = validate_requirements_bundle(bundle, profile=profile)
    _emit_payload(report.model_dump(mode="json"), output_format)
    if report.status == "failed":
        raise typer.Exit(1)


@app.command("list", help="List normalized requirement inputs attached to a bundle.")
@beartype
@require(lambda bundle: bundle.is_dir(), "bundle must exist")
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def list_command(
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False, dir_okay=True, readable=True),
    ],
    show_coverage: Annotated[bool, typer.Option("--show-coverage", help="Include coverage summary.")] = False,
    output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format.")] = OutputFormat.TEXT,
) -> None:
    """List normalized requirement inputs attached to a bundle."""
    _emit_payload(list_requirements_with_coverage(bundle, show_coverage=show_coverage), output_format)


@app.command("coverage", help="Inspect requirement context coverage.")
@beartype
@require(lambda bundle: bundle.is_dir(), "bundle must exist")
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def coverage_command(
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False, dir_okay=True, readable=True),
    ],
    output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format.")] = OutputFormat.TEXT,
) -> None:
    """Inspect requirement context coverage."""
    coverage = inspect_requirements_bundle_coverage(bundle)
    payload = coverage.model_dump(mode="json")
    payload["gate_finding_counts"] = requirements_gate_finding_counts(bundle)
    _emit_payload(payload, output_format)


@dataclass(frozen=True)
class EvidenceCommandOptions:
    output: Path
    repo_root: Path
    base_ref: str | None
    staged: bool
    summary: Path | None
    required_maturity: str | None
    review_evidence: Path | None
    plan_output: Path | None


def _write_command_evidence(options: EvidenceCommandOptions) -> int:
    if (options.base_ref is None) != options.staged:
        raise typer.BadParameter("choose exactly one of --base-ref or --staged")
    return write_requirements_evidence(
        options.repo_root.resolve(),
        options.output,
        summary_path=options.summary,
        base_ref=options.base_ref,
        staged=options.staged,
        required_maturity=options.required_maturity,
        review_evidence_path=options.review_evidence,
        plan_output_path=options.plan_output,
    )


@app.command("evidence", help="Evaluate OpenSpec requirement evidence for a base ref or staged Git index.")
@beartype
@ensure(lambda result: result is None)
def evidence_command(
    output: Annotated[Path, typer.Option("--output", help="Destination JSON evidence report.")],
    repo_root: Annotated[
        Path, typer.Option("--repo-root", help="Repository root to inspect.", default_factory=Path.cwd)
    ],
    base_ref: Annotated[str | None, typer.Option("--base-ref", help="Git ref used for CI diff selection.")] = None,
    staged: Annotated[bool, typer.Option("--staged", help="Evaluate the current Git index snapshot.")] = False,
    summary: Annotated[Path | None, typer.Option("--summary", help="Optional Markdown remediation report.")] = None,
    required_maturity: Annotated[
        RequiredMaturity | None,
        typer.Option(
            "--required-maturity",
            help="Lifecycle maturity required for a schema-v2 sidecar.",
        ),
    ] = None,
    review_evidence: Annotated[
        Path | None,
        typer.Option(
            "--review-evidence",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Provider-neutral acceptance record bound to the mapping digest.",
        ),
    ] = None,
    plan_output: Annotated[
        Path | None, typer.Option("--plan-output", help="Optional normalized lifecycle plan JSON.")
    ] = None,
) -> None:
    """Write evidence reports before returning a non-zero verdict."""
    options = EvidenceCommandOptions(
        output=output,
        repo_root=repo_root,
        base_ref=base_ref,
        staged=staged,
        summary=summary,
        required_maturity=required_maturity,
        review_evidence=review_evidence,
        plan_output=plan_output,
    )
    try:
        exit_code = _write_command_evidence(options)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if exit_code:
        raise typer.Exit(exit_code)


def _load_json_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise typer.BadParameter(f"{label} must be readable JSON") from error
    if not isinstance(value, dict):
        raise typer.BadParameter(f"{label} must contain a JSON object")
    return value


@app.command("reconcile", help="Reconcile a lifecycle plan with trusted JUnit without running tests.")
@beartype
@ensure(lambda result: result is None)
def reconcile_command(
    plan: Annotated[Path, typer.Option("--plan", exists=True, file_okay=True, dir_okay=False, readable=True)],
    junit: Annotated[Path, typer.Option("--junit", exists=True, file_okay=True, dir_okay=False, readable=True)],
    run_stage: Annotated[str, typer.Option("--run-stage", help="Evidence stage: red or final.")],
    source_ref: Annotated[str, typer.Option("--source-ref", help="Full Git object ID for the executed source.")],
    output: Annotated[Path, typer.Option("--output", help="Destination JSON proof report.")],
    prior_red_proof: Annotated[
        Path | None,
        typer.Option("--prior-red-proof", exists=True, file_okay=True, dir_okay=False, readable=True),
    ] = None,
    legacy_tdd_evidence: Annotated[
        Path | None,
        typer.Option(
            "--legacy-tdd-evidence",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Explicit legacy TDD ledger migration record for final reconciliation.",
        ),
    ] = None,
    summary: Annotated[Path | None, typer.Option("--summary", help="Optional Markdown proof summary.")] = None,
) -> None:
    """Reconcile result artifacts while keeping test execution outside the module."""
    try:
        report = reconcile_junit(
            _load_json_mapping(plan, "plan"),
            junit,
            ReconciliationContext(
                run_stage=run_stage,
                source_ref=source_ref,
                prior_red_proof=_load_json_mapping(prior_red_proof, "prior red proof") if prior_red_proof else None,
                legacy_tdd_evidence=(
                    _load_json_mapping(legacy_tdd_evidence, "legacy TDD evidence") if legacy_tdd_evidence else None
                ),
            ),
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if summary is not None:
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text(
            "\n".join(
                [
                    "## Requirements lifecycle proof",
                    "",
                    f"- Gate decision: **{report['gate_decision']}**",
                    f"- Observed maturity: `{report['observed_maturity']}`",
                    f"- Implementation evidence: `{report['implementation_evidence']}`",
                    f"- Execution stage: `{report['execution_proof']['run_stage']}`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    if report["gate_decision"] == "fail":
        raise typer.Exit(1)
