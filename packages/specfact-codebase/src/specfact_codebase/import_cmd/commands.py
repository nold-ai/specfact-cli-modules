"""Code-owned import command surface for brownfield workflows.

Operating guidance: embedded command examples are not the source of truth;
CLI help is authoritative, so run the relevant --help command and ask the user
before acting when examples and runtime behavior diverge.
"""

from __future__ import annotations

from pathlib import Path

import click
import typer
from icontract import require
from typer.core import TyperGroup

from specfact_project.import_cmd.commands import from_bridge as legacy_from_bridge, from_code as legacy_from_code


class _ImportCommandGroup(TyperGroup):
    """Detect common legacy callback ordering and print a migration-quality hint."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] in self.commands:
            if any(arg in ("--help", "-h", "--help-advanced", "-ha") for arg in args[1:]):
                command = self.commands[args[0]]
                try:
                    command.main(
                        args=args[1:],
                        prog_name=f"{ctx.command_path} {args[0]}",
                        standalone_mode=False,
                    )
                except click.exceptions.Exit as exc:
                    ctx.exit(exc.exit_code)
                ctx.exit(0)
            return self._parse_explicit_subcommand_args(ctx, args)
        if args and args[0] not in self.commands and any(arg.startswith("-") for arg in args[1:]):
            self._raise_legacy_order_error(ctx)
        return super().parse_args(ctx, args)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] not in self.commands and any(arg.startswith("-") for arg in args[1:]):
            self._raise_legacy_order_error(ctx)
        return super().resolve_command(ctx, args)

    def _raise_legacy_order_error(self, ctx: click.Context) -> None:
        click.echo(ctx.get_help())
        click.echo(
            "\nError: Invalid option order for `specfact code import`.\n"
            "Use the canonical form: specfact code import --repo . <bundle>\n"
            "Or use the explicit command: specfact code import from-code <bundle> --repo ."
        )
        raise click.UsageError("Invalid option order for specfact code import")

    def _parse_explicit_subcommand_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        original_params = self.params
        self.params = [param for param in self.params if not isinstance(param, click.Argument)]
        try:
            return super().parse_args(ctx, args)
        finally:
            self.params = original_params


app = typer.Typer(
    help="Import codebases and related external inputs into SpecFact project bundles.",
    context_settings={"help_option_names": ["-h", "--help", "--help-advanced", "-ha"]},
    invoke_without_command=True,
    no_args_is_help=False,
    cls=_ImportCommandGroup,
)


@app.callback()
@require(lambda repo: repo.exists() and repo.is_dir(), "Repo path must exist and be directory")
@require(
    lambda bundle: bundle is None or (isinstance(bundle, str) and len(bundle) > 0),
    "Bundle name must be None or non-empty string",
)
@require(lambda confidence: 0.0 <= confidence <= 1.0, "Confidence must be 0.0-1.0")
def import_codebase(
    ctx: typer.Context,
    bundle: str | None = typer.Argument(
        None,
        help="Project bundle name (e.g., legacy-api, auth-module). Default: active project bundle configuration.",
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
    if ctx.invoked_subcommand is not None:
        return
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


app.command("from-code")(legacy_from_code)
app.command("from-bridge")(legacy_from_bridge)


__all__ = ["app", "import_codebase"]
