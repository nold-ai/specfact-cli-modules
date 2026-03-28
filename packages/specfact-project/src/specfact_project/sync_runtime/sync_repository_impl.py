"""Helpers for commands.sync_repository (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from specfact_project.sync_runtime.sync_command_common import is_test_mode


def repository_run_specmatic_validation(resolved_repo: Path, console: Any) -> None:
    from specfact_cli.integrations.specmatic import check_specmatic_available, validate_spec_with_specmatic

    spec_files = []
    for pattern in [
        "**/openapi.yaml",
        "**/openapi.yml",
        "**/openapi.json",
        "**/asyncapi.yaml",
        "**/asyncapi.yml",
        "**/asyncapi.json",
    ]:
        spec_files.extend(resolved_repo.glob(pattern))
    if not spec_files:
        return
    console.print(f"\n[cyan]🔍 Found {len(spec_files)} API specification file(s)[/cyan]")
    is_available, error_msg = check_specmatic_available()
    if not is_available:
        console.print(f"[dim]💡 Tip: Install Specmatic to validate API specs: {error_msg}[/dim]")
        return
    for spec_file in spec_files[:3]:
        console.print(f"[dim]Validating {spec_file.relative_to(resolved_repo)} with Specmatic...[/dim]")
        try:
            result = asyncio.run(validate_spec_with_specmatic(spec_file))
            if result.is_valid:
                console.print(f"  [green]✓[/green] {spec_file.name} is valid")
            else:
                console.print(f"  [yellow]⚠[/yellow] {spec_file.name} has validation issues")
                if result.errors:
                    for error in result.errors[:2]:
                        console.print(f"    - {error}")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Validation error: {e!s}")
    if len(spec_files) > 3:
        console.print(
            f"[dim]... and {len(spec_files) - 3} more spec file(s) (run 'specfact spec validate' to validate all)[/dim]"
        )


def repository_sync_run_once(sync: Any, resolved_repo: Path, console: Any) -> Any:
    if is_test_mode():
        return sync.sync_repository_changes(resolved_repo)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting code changes...", total=None)
        result = sync.sync_repository_changes(resolved_repo)
        progress.update(task, description=f"✓ Detected {len(result.code_changes)} code changes")
        if result.plan_updates:
            task = progress.add_task("Updating plan artifacts...", total=None)
            total_features = sum(update.get("features", 0) for update in result.plan_updates)
            progress.update(task, description=f"✓ Updated plan artifacts ({total_features} features)")
        if result.deviations:
            task = progress.add_task("Tracking deviations...", total=None)
            progress.update(task, description=f"✓ Found {len(result.deviations)} deviations")
    return result


def make_repository_watch_callback(sync: Any, resolved_repo: Path, console: Any):
    """Return a callback for SyncWatcher (module-level to avoid nested def CC)."""

    def sync_callback(changes: list) -> None:
        code_changes = [c for c in changes if getattr(c, "change_type", None) == "code"]
        if not code_changes:
            return
        console.print(f"[cyan]Detected {len(code_changes)} code change(s), syncing...[/cyan]")
        try:
            if not resolved_repo.exists():
                console.print(f"[yellow]⚠[/yellow] Repository path no longer exists: {resolved_repo}\n")
                return
            if not resolved_repo.is_dir():
                console.print(f"[yellow]⚠[/yellow] Repository path is no longer a directory: {resolved_repo}\n")
                return
            result = sync.sync_repository_changes(resolved_repo)
            if result.status == "success":
                console.print("[green]✓[/green] Repository sync complete\n")
            elif result.status == "deviation_detected":
                console.print(f"[yellow]⚠[/yellow] Deviations detected: {len(result.deviations)}\n")
            else:
                console.print(f"[red]✗[/red] Sync failed: {result.status}\n")
        except Exception as e:
            console.print(f"[red]✗[/red] Sync failed: {e}\n")

    return sync_callback
