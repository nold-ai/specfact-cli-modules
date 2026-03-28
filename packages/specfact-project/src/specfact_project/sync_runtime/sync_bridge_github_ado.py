"""GitHub / Azure DevOps bidirectional backlog phases (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.runtime import get_configured_console

from specfact_project.sync_runtime.bridge_sync import BridgeSync
from specfact_project.sync_runtime.sync_command_common import infer_bundle_name, parse_backlog_selection


console = get_configured_console()


def _github_adapter_kwargs(
    repo_owner: str | None,
    repo_name: str | None,
    github_token: str | None,
    use_gh_cli: bool,
) -> dict[str, Any]:
    return {
        "repo_owner": repo_owner,
        "repo_name": repo_name,
        "api_token": github_token,
        "use_gh_cli": use_gh_cli,
    }


def _ado_adapter_kwargs(
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_token: str | None,
    ado_work_item_type: str | None,
) -> dict[str, Any]:
    return {
        "org": ado_org,
        "project": ado_project,
        "base_url": ado_base_url,
        "api_token": ado_token,
        "work_item_type": ado_work_item_type,
    }


def build_import_adapter_kwargs(
    adapter_value: str,
    *,
    repo_owner: str | None,
    repo_name: str | None,
    github_token: str | None,
    use_gh_cli: bool,
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_token: str | None,
    ado_work_item_type: str | None,
) -> dict[str, Any]:
    if adapter_value == "github":
        return _github_adapter_kwargs(repo_owner, repo_name, github_token, use_gh_cli)
    return _ado_adapter_kwargs(ado_org, ado_project, ado_base_url, ado_token, ado_work_item_type)


def resolve_interactive_backlog_items(
    backlog_items: list[str],
    interactive: bool,
) -> list[str]:
    from specfact_cli import runtime

    bi = list(backlog_items)
    if bi or not interactive or not runtime.is_interactive():
        return bi
    prompt = typer.prompt(
        "Enter backlog item IDs/URLs to import (comma-separated, leave blank to skip)",
        default="",
    )
    parsed = parse_backlog_selection(prompt)
    return list(dict.fromkeys(parsed))


def print_backlog_selection_status(bi: list[str]) -> None:
    if bi:
        console.print(f"[dim]Selected backlog items ({len(bi)}): {', '.join(bi)}[/dim]")
        return
    console.print("[yellow]⚠[/yellow] No backlog items selected; import skipped")


def import_backlog_items_or_exit(
    bridge_sync: BridgeSync,
    adapter_value: str,
    resolved_bundle: str,
    bi: list[str],
    adapter_kwargs: dict[str, Any],
) -> None:
    if not bi:
        return
    import_result = bridge_sync.import_backlog_items_to_bundle(
        adapter_type=adapter_value,
        bundle_name=resolved_bundle,
        backlog_items=bi,
        adapter_kwargs=adapter_kwargs,
    )
    if import_result.success:
        console.print(f"[bold green]✓[/bold green] Imported {len(import_result.operations)} backlog item(s)")
        for warning in import_result.warnings:
            console.print(f"[yellow]⚠[/yellow] {warning}")
        return
    console.print(f"[bold red]✗[/bold red] Import failed with {len(import_result.errors)} errors")
    for error in import_result.errors:
        console.print(f"[red]  • {error}[/red]")
    raise typer.Exit(1)


def export_backlog_from_bundle_or_exit(
    bridge_sync: BridgeSync,
    adapter_value: str,
    resolved_bundle: str,
    export_adapter_kwargs: dict[str, Any],
    update_existing: bool,
    change_ids_list: list[str] | None,
) -> None:
    export_result = bridge_sync.export_backlog_from_bundle(
        adapter_type=adapter_value,
        bundle_name=resolved_bundle,
        adapter_kwargs=export_adapter_kwargs,
        update_existing=update_existing,
        change_ids=change_ids_list,
    )
    if export_result.success:
        console.print(f"[bold green]✓[/bold green] Exported {len(export_result.operations)} backlog item(s)")
        for warning in export_result.warnings:
            console.print(f"[yellow]⚠[/yellow] {warning}")
        return
    console.print(f"[bold red]✗[/bold red] Export failed with {len(export_result.errors)} errors")
    for error in export_result.errors:
        console.print(f"[red]  • {error}[/red]")
    raise typer.Exit(1)


def phase_github_ado_bidirectional(
    *,
    adapter_value: str,
    sync_mode: str,
    resolved_repo: Path,
    bundle: str | None,
    interactive: bool,
    backlog_items: list[str],
    repo_owner: str | None,
    repo_name: str | None,
    github_token: str | None,
    use_gh_cli: bool,
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_token: str | None,
    ado_work_item_type: str | None,
    update_existing: bool,
    change_ids_list: list[str] | None,
) -> bool:
    if adapter_value not in ("github", "ado") or sync_mode != "bidirectional":
        return False
    resolved_bundle = bundle or infer_bundle_name(resolved_repo)
    if not resolved_bundle:
        console.print("[bold red]✗[/bold red] Bundle name required for backlog sync")
        console.print("[dim]Provide --bundle or set an active bundle in .specfact/config.yaml[/dim]")
        raise typer.Exit(1)
    bi = resolve_interactive_backlog_items(backlog_items, interactive)
    print_backlog_selection_status(bi)
    adapter_instance = AdapterRegistry.get_adapter(adapter_value)
    bridge_config = adapter_instance.generate_bridge_config(resolved_repo)
    bridge_sync = BridgeSync(resolved_repo, bridge_config=bridge_config)
    import_kwargs = build_import_adapter_kwargs(
        adapter_value,
        repo_owner=repo_owner,
        repo_name=repo_name,
        github_token=github_token,
        use_gh_cli=use_gh_cli,
        ado_org=ado_org,
        ado_project=ado_project,
        ado_base_url=ado_base_url,
        ado_token=ado_token,
        ado_work_item_type=ado_work_item_type,
    )
    import_backlog_items_or_exit(bridge_sync, adapter_value, resolved_bundle, bi, import_kwargs)
    export_kwargs = build_import_adapter_kwargs(
        adapter_value,
        repo_owner=repo_owner,
        repo_name=repo_name,
        github_token=github_token,
        use_gh_cli=use_gh_cli,
        ado_org=ado_org,
        ado_project=ado_project,
        ado_base_url=ado_base_url,
        ado_token=ado_token,
        ado_work_item_type=ado_work_item_type,
    )
    export_backlog_from_bundle_or_exit(
        bridge_sync,
        adapter_value,
        resolved_bundle,
        export_kwargs,
        update_existing,
        change_ids_list,
    )
    return True
