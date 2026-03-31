"""Typer command surface for the review reward ledger."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from specfact_code_review.ledger.client import LedgerClient, LedgerStatus
from specfact_code_review.run.findings import ReviewReport


app = typer.Typer(help="Persist and inspect review reward history.", no_args_is_help=True)
console = Console()


def _render_status(status_payload: LedgerStatus) -> None:
    console.print(
        "Updated ledger: "
        f"{status_payload['coins']:.2f} coins, "
        f"pass streak {status_payload['streak_pass']}, "
        f"block streak {status_payload['streak_block']}, "
        f"last verdict {status_payload['last_verdict']}"
    )


@app.command("update")
def _update(
    report_file: Path | None = typer.Option(
        None,
        "--from",
        help="Read ReviewReport JSON from a file path instead of stdin.",
    ),
) -> None:
    """Update the ledger from stdin or a ReviewReport JSON file."""
    raw_payload = report_file.read_text(encoding="utf-8") if report_file is not None else sys.stdin.read()
    if not raw_payload.strip():
        typer.echo("ReviewReport JSON is required on stdin.", err=True)
        raise typer.Exit(code=1)

    try:
        report = ReviewReport.model_validate_json(raw_payload)
    except ValidationError:
        typer.echo("Invalid ReviewReport JSON.", err=True)
        raise typer.Exit(code=1) from None

    try:
        status = LedgerClient().record_run(report)
    except OSError as exc:
        typer.echo(f"Unable to write ledger state: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _render_status(status)


@app.command("status")
def _status() -> None:
    """Print the current ledger state."""
    try:
        current_status = LedgerClient().get_status()
    except OSError as exc:
        typer.echo(f"Unable to read ledger state: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    console.print(f"Coins: {current_status['coins']:.2f}")
    console.print(f"Pass streak: {current_status['streak_pass']}")
    console.print(f"Block streak: {current_status['streak_block']}")
    console.print(f"Last verdict: {current_status['last_verdict']}")

    top_violations = current_status["top_violations"]
    if top_violations:
        rendered = ", ".join(_format_violation(entry) for entry in top_violations)
        console.print(f"Top violations: {rendered}")


@app.command("reset")
def _reset(
    confirm: bool = typer.Option(False, "--confirm", help="Delete the local fallback ledger."),
) -> None:
    """Delete the local JSON fallback ledger."""
    if not confirm:
        typer.echo("Refusing to reset the local ledger without --confirm.", err=True)
        raise typer.Exit(code=1)

    try:
        LedgerClient().reset_local()
    except OSError as exc:
        typer.echo(f"Unable to reset ledger state: {exc}", err=True)
        raise typer.Exit(code=1) from exc
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
