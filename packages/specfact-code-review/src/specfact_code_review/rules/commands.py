"""Typer command surface for house-rules skill management."""

from __future__ import annotations

from pathlib import Path

import typer

from specfact_code_review.ledger.client import LedgerClient
from specfact_code_review.rules.updater import (
    SKILL_PATH,
    SupportedIde,
    default_skill_content,
    load_bundled_skill_content,
    sync_skill_to_ide,
    update_house_rules,
)


app = typer.Typer(help="Manage the code-review house-rules skill.", no_args_is_help=True)


@app.command("show")
def _show() -> None:
    """Print the current skill content."""
    skill_path = _skill_path()
    if not skill_path.exists():
        typer.echo(
            f"No house-rules skill found at {skill_path}. Run `specfact code review rules init` first.",
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo(skill_path.read_text(encoding="utf-8"), nl=False)


@app.command("init")
def _init(
    ide: SupportedIde | None = typer.Option(
        None,
        "--ide",
        help=(
            "Install to the canonical target path for one IDE. Omit to keep only skills/specfact-code-review/SKILL.md."
        ),
    ),
) -> None:
    """Create the default skill file and optionally install it to one canonical IDE target."""
    skill_path = _skill_path()
    if skill_path.exists():
        typer.echo(f"House-rules skill already exists at {skill_path}.", err=True)
        raise typer.Exit(code=1)
    content = load_bundled_skill_content() or default_skill_content()
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(content, encoding="utf-8")
    mirrored = sync_skill_to_ide(content, Path.cwd(), ide=ide)
    typer.echo(f"Created {skill_path}")
    for path in mirrored:
        typer.echo(f"Installed to {path}")


@app.command("update")
def _update(
    ide: SupportedIde | None = typer.Option(
        None,
        "--ide",
        help=("Refresh one canonical IDE target. Omit to refresh only IDE targets already installed in the project."),
    ),
) -> None:
    """Update the TOP VIOLATIONS section and refresh canonical IDE targets."""
    skill_path = _skill_path()
    if not skill_path.exists():
        typer.echo(
            f"No house-rules skill found at {skill_path}. Run `specfact code review rules init` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    runs = LedgerClient().get_recent_runs(limit=20)
    updated = update_house_rules(skill_path, runs)
    sync_skill_to_ide(updated, Path.cwd(), ide=ide)
    typer.echo(f"Updated {skill_path}")


def _skill_path() -> Path:
    return Path.cwd() / SKILL_PATH


REGISTERED_COMMANDS = (_show, _init, _update)


__all__ = ["app"]
