"""Utility functions for backlog_core module."""

from __future__ import annotations

from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.prompt import Prompt


console = Console()


@beartype
@require(lambda message: isinstance(message, str) and len(message) > 0, "Message must be non-empty string")
def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[bold green]✅ {message}[/bold green]")


@beartype
@require(lambda message: isinstance(message, str) and len(message) > 0, "Message must be non-empty string")
def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[bold red]❌ {message}[/bold red]")


@beartype
@require(lambda message: isinstance(message, str) and len(message) > 0, "Message must be non-empty string")
def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


@beartype
@require(lambda message: isinstance(message, str) and len(message) > 0, "Message must be non-empty string")
def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


@beartype
@require(lambda message: isinstance(message, str) and len(message) > 0, "Message must be non-empty string")
@require(lambda default: default is None or isinstance(default, str), "Default must be None or string")
@ensure(lambda result: isinstance(result, str), "Must return string")
def prompt_text(message: str, default: str | None = None, required: bool = True) -> str:
    """
    Prompt user for text input.

    Args:
        message: Prompt message
        default: Default value
        required: Whether input is required

    Returns:
        User input string
    """
    while True:
        rich_default = default if default is not None else ""
        result = Prompt.ask(message, default=rich_default)
        if default and not result.strip():
            return default
        if result or not required:
            return result
        console.print("[yellow]This field is required[/yellow]")
