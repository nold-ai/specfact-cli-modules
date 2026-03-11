"""Review subgroup wiring for the code command surface."""

from __future__ import annotations

import typer

from specfact_code_review.run.commands import app as run_app


app = typer.Typer(help="Code command extensions for structured review workflows.", no_args_is_help=True)
review_app = typer.Typer(help="Governed code review workflows.", no_args_is_help=True)
ledger_app = typer.Typer(help="Review ledger commands (stub).", no_args_is_help=False)
rules_app = typer.Typer(help="Review house rules commands (stub).", no_args_is_help=False)

review_app.add_typer(run_app, name="run")
review_app.add_typer(ledger_app, name="ledger")
review_app.add_typer(rules_app, name="rules")
app.add_typer(review_app, name="review")

__all__ = ["app", "review_app"]
