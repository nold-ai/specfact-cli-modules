"""Typer command surface for the review reward ledger."""

from __future__ import annotations

import sys

import typer
from pydantic import ValidationError
from rich.console import Console

from specfact_code_review.ledger.client import LedgerClient
from specfact_code_review.run.findings import ReviewReport


app = typer.Typer(help="Persist and inspect review reward history.", no_args_is_help=True)
console = Console()


@app.command("update")
def update() -> None:
    """Read a ReviewReport JSON payload from stdin and update the ledger."""
    raw_payload = sys.stdin.read()
    if not raw_payload.strip():
        typer.echo("ReviewReport JSON is required on stdin.", err=True)
        raise typer.Exit(code=1)

    try:
        report = ReviewReport.model_validate_json(raw_payload)
    except ValidationError:
        typer.echo("Invalid ReviewReport JSON.", err=True)
        raise typer.Exit(code=1) from None

    status = LedgerClient().record_run(report)
    console.print(
        "Updated ledger: "
        f"{float(status['coins']):.2f} coins, "
        f"pass streak {int(status['streak_pass'])}, "
        f"block streak {int(status['streak_block'])}, "
        f"last verdict {status['last_verdict']}"
    )


@app.command("status")
def status() -> None:
    """Print the current ledger state."""
    current_status = LedgerClient().get_status()
    console.print(f"Coins: {float(current_status['coins']):.2f}")
    console.print(f"Pass streak: {int(current_status['streak_pass'])}")
    console.print(f"Block streak: {int(current_status['streak_block'])}")
    console.print(f"Last verdict: {current_status['last_verdict']}")

    top_violations = current_status.get("top_violations", [])
    if isinstance(top_violations, list) and top_violations:
        rendered = ", ".join(_format_violation(entry) for entry in top_violations)
        console.print(f"Top violations: {rendered}")


@app.command("reset")
def reset(
    confirm: bool = typer.Option(False, "--confirm", help="Delete the local fallback ledger."),
) -> None:
    """Delete the local JSON fallback ledger."""
    if not confirm:
        typer.echo("Refusing to reset the local ledger without --confirm.", err=True)
        raise typer.Exit(code=1)

    LedgerClient().reset_local()
    console.print("Local ledger reset.")


def _format_violation(entry: object) -> str:
    if isinstance(entry, tuple) and len(entry) == 2:
        rule, count = entry
        return f"{rule} ({count})"
    if isinstance(entry, list) and len(entry) == 2:
        rule, count = entry
        return f"{rule} ({count})"
    if isinstance(entry, dict):
        rule = entry.get("rule", "unknown")
        count = entry.get("count", "?")
        return f"{rule} ({count})"
    return str(entry)


__all__ = ["app"]
