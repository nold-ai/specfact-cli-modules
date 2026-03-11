"""Stub command surface for `specfact code review run`."""

from __future__ import annotations

import typer


app = typer.Typer(help="Execute code review runs.", no_args_is_help=False)


@app.callback()
def run_callback() -> None:
    """Review run command stub."""


__all__ = ["app"]
