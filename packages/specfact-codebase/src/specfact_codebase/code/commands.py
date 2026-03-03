"""Code aggregate command for codebase bundle."""

from __future__ import annotations

import typer

from specfact_codebase.analyze.commands import app as analyze_app
from specfact_codebase.drift.commands import app as drift_app
from specfact_codebase.repro.commands import app as repro_app
from specfact_codebase.validate.commands import app as validate_app


app = typer.Typer(
    help="Codebase quality commands: analyze, drift, validate, repro.",
    no_args_is_help=True,
)

app.add_typer(analyze_app, name="analyze")
app.add_typer(drift_app, name="drift")
app.add_typer(validate_app, name="validate")
app.add_typer(repro_app, name="repro")

__all__ = ["app"]
