"""Govern aggregate command for govern bundle."""

from __future__ import annotations

import typer
from specfact_cli.modules import module_io_shim

from specfact_govern.enforce.commands import app as enforce_app
from specfact_govern.patch_mode.commands import app as patch_app


app = typer.Typer(
    help="Governance and quality gates: enforce, patch.",
    no_args_is_help=True,
)

app.add_typer(enforce_app, name="enforce")
app.add_typer(patch_app, name="patch")

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
