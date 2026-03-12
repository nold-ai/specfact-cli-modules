"""Code-owned import command surface for brownfield workflows."""

from __future__ import annotations

from pathlib import Path

import typer
from beartype import beartype
from icontract import require

from specfact_project.import_cmd.commands import from_bridge as legacy_from_bridge, from_code as legacy_from_code


app = typer.Typer(
    help="Import codebases and related external inputs into SpecFact project bundles.",
    context_settings={"help_option_names": ["-h", "--help", "--help-advanced", "-ha"]},
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback()
@require(lambda repo: repo.exists() and repo.is_dir(), "Repo path must exist and be directory")
@require(
    lambda bundle: bundle is None or (isinstance(bundle, str) and len(bundle) > 0),
    "Bundle name must be None or non-empty string",
)
@require(lambda confidence: 0.0 <= confidence <= 1.0, "Confidence must be 0.0-1.0")
@beartype
def import_codebase(
    bundle: str | None = typer.Argument(
        None,
        help="Project bundle name (e.g., legacy-api, auth-module). Default: active plan from 'specfact plan select'.",
    ),
    repo: Path = typer.Option(
        Path("."),
        "--repo",
        help="Path to repository to import. Default: current directory (.)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    entry_point: Path | None = typer.Option(
        None,
        "--entry-point",
        help="Subdirectory path for partial analysis (relative to repo root).",
        hidden=True,
    ),
    enrichment: Path | None = typer.Option(
        None,
        "--enrichment",
        help="Path to Markdown enrichment report from LLM.",
        hidden=True,
    ),
    report: Path | None = typer.Option(
        None,
        "--report",
        help="Path to write analysis report.",
    ),
    shadow_only: bool = typer.Option(
        False,
        "--shadow-only",
        help="Shadow mode - observe without enforcing. Default: False",
    ),
    enrich_for_speckit: bool = typer.Option(
        True,
        "--enrich-for-speckit/--no-enrich-for-speckit",
        help="Automatically enrich the imported bundle for Spec-Kit compliance. Default: enabled.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force full regeneration of all artifacts, ignoring incremental changes.",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests/--exclude-tests",
        help="Include or exclude test files in relationship mapping and dependency graph.",
    ),
    revalidate_features: bool = typer.Option(
        False,
        "--revalidate-features/--no-revalidate-features",
        help="Re-analyze existing features even if files have not changed.",
        hidden=True,
    ),
    confidence: float = typer.Option(
        0.5,
        "--confidence",
        min=0.0,
        max=1.0,
        help="Minimum confidence score for detected features.",
        hidden=True,
    ),
    key_format: str = typer.Option(
        "classname",
        "--key-format",
        help="Feature key format: 'classname' or 'sequential'.",
        hidden=True,
    ),
) -> None:
    """Import a codebase into a SpecFact project bundle."""
    legacy_from_code(
        bundle=bundle,
        repo=repo,
        entry_point=entry_point,
        enrichment=enrichment,
        report=report,
        shadow_only=shadow_only,
        enrich_for_speckit=enrich_for_speckit,
        force=force,
        include_tests=include_tests,
        revalidate_features=revalidate_features,
        confidence=confidence,
        key_format=key_format,
    )


app.command("from-code", hidden=True)(legacy_from_code)
app.command("from-bridge")(legacy_from_bridge)


__all__ = ["app", "import_codebase"]
