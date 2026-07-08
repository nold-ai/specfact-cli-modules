"""Command handlers for requirement context evidence."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from beartype import beartype
from icontract import ensure, require

from specfact_requirements.requirements.runtime import (
    KNOWN_REQUIREMENT_CONTEXT_PROFILES,
    import_requirements_file_to_bundle,
    inspect_requirements_bundle_coverage,
    list_requirements_with_coverage,
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


def _profile_supported(profile: str) -> bool:
    return profile in KNOWN_REQUIREMENT_CONTEXT_PROFILES


@beartype
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def _emit_payload(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


@app.command("import", help="Import local requirement records into a project bundle.")
@beartype
@require(lambda from_file: from_file.is_file(), "from_file must exist")
@require(lambda bundle: bundle.is_dir(), "bundle must exist")
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def import_command(
    from_file: Annotated[
        Path,
        typer.Option(
            "--from-file", exists=True, file_okay=True, dir_okay=False, readable=True, help="JSON/YAML records."
        ),
    ],
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False, dir_okay=True, readable=True, writable=True),
    ],
    output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format.")] = OutputFormat.TEXT,
) -> None:
    """Import local requirement records into a project bundle."""
    result = import_requirements_file_to_bundle(from_file, bundle)
    _emit_payload(
        {
            "imported": len(result.requirements),
            "diagnostics": [diagnostic.model_dump(mode="json") for diagnostic in result.diagnostics],
        },
        output_format,
    )


@app.command("validate", help="Validate requirement context evidence usefulness.")
@beartype
@require(lambda bundle: bundle.is_dir(), "bundle must exist")
@require(_profile_supported, "profile must be a known requirement context profile")
@require(_format_supported, "output format must be supported")
@ensure(lambda result: result is None)
def validate_command(
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False, dir_okay=True, readable=True),
    ],
    profile: Annotated[str, typer.Option("--profile", help="Validation profile.")] = "startup",
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
    _emit_payload(coverage.model_dump(mode="json"), output_format)
