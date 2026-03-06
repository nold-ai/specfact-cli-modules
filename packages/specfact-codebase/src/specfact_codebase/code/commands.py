"""Code aggregate command for codebase bundle."""

from __future__ import annotations

import typer
from specfact_cli.modules import module_io_shim

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

# Expose the standard bundle protocol at the aggregate entrypoint so core runtime
# compliance checks classify the installed bundle correctly.
import_to_bundle = module_io_shim.import_to_bundle
export_from_bundle = module_io_shim.export_from_bundle
sync_with_bundle = module_io_shim.sync_with_bundle
validate_bundle = module_io_shim.validate_bundle

__all__ = [
    "app",
    "export_from_bundle",
    "import_to_bundle",
    "sync_with_bundle",
    "validate_bundle",
]
