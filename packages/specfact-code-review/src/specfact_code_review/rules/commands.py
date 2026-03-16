"""Typer command surface for house-rules skill management."""

from __future__ import annotations

from pathlib import Path

import typer

from specfact_code_review.ledger.client import LedgerClient
from specfact_code_review.rules.updater import MIRROR_PATH, SKILL_PATH, default_skill_content, update_house_rules


app = typer.Typer(help="Manage the code-review house-rules skill.", no_args_is_help=True)


@app.command("show")
def show() -> None:
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
def init() -> None:
    """Create the default skill file for the current project."""
    skill_path = _skill_path()
    if skill_path.exists():
        typer.echo(f"House-rules skill already exists at {skill_path}.", err=True)
        raise typer.Exit(code=1)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(default_skill_content(), encoding="utf-8")
    typer.echo(f"Created {skill_path}")


@app.command("update")
def update() -> None:
    """Update the TOP VIOLATIONS section from recent ledger data."""
    skill_path = _skill_path()
    if not skill_path.exists():
        typer.echo(
            f"No house-rules skill found at {skill_path}. Run `specfact code review rules init` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    runs = LedgerClient().get_recent_runs(limit=20)
    mirror_path = _mirror_path()
    update_house_rules(
        skill_path,
        runs,
        mirror_path=mirror_path if mirror_path.parent.exists() else None,
    )
    typer.echo(f"Updated {skill_path}")


def _skill_path() -> Path:
    return Path.cwd() / SKILL_PATH


def _mirror_path() -> Path:
    return Path.cwd() / MIRROR_PATH


__all__ = ["app"]
