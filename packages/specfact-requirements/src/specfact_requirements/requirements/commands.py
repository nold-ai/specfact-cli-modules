"""Command handlers for requirement context evidence."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from beartype import beartype
from icontract import ensure, require

from specfact_requirements.requirements.evidence import write_requirements_evidence
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


@app.command("evidence", help="Evaluate OpenSpec requirement evidence for a base ref or staged Git index.")
@beartype
@ensure(lambda result: result is None)
def evidence_command(
    output: Annotated[Path, typer.Option("--output", help="Destination JSON evidence report.")],
    base_ref: Annotated[str | None, typer.Option("--base-ref", help="Git ref used for CI diff selection.")] = None,
    staged: Annotated[bool, typer.Option("--staged", help="Evaluate the current Git index snapshot.")] = False,
    summary: Annotated[Path | None, typer.Option("--summary", help="Optional Markdown remediation report.")] = None,
    repo_root: Annotated[Path, typer.Option("--repo-root", help="Repository root to inspect.")] = Path.cwd(),
) -> None:
    """Write evidence reports before returning a non-zero verdict."""
    if (base_ref is None) != staged:
        raise typer.BadParameter("choose exactly one of --base-ref or --staged")
    exit_code = write_requirements_evidence(repo_root.resolve(), output, summary, base_ref=base_ref, staged=staged)
    if exit_code:
        raise typer.Exit(exit_code)
