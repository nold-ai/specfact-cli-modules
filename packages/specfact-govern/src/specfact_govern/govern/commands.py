"""Govern aggregate command for govern bundle."""

from __future__ import annotations

import typer

from specfact_govern.enforce.commands import app as enforce_app
from specfact_govern.patch_mode.commands import app as patch_app


app = typer.Typer(
    help="Governance and quality gates: enforce, patch.",
    no_args_is_help=True,
)

app.add_typer(enforce_app, name="enforce")
app.add_typer(patch_app, name="patch")

__all__ = ["app"]
