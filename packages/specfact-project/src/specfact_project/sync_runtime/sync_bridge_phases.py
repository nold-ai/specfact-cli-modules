"""Phased dispatch for sync bridge command (radon cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.progress import Progress
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.models.bridge import AdapterType
from specfact_cli.runtime import get_configured_console
from specfact_cli.utils.terminal import get_progress_config

from specfact_project.sync_runtime.bridge_sync import BridgeSync
from specfact_project.sync_runtime.speckit_change_proposal_sync import sync_speckit_change_proposals
from specfact_project.sync_runtime.sync_bridge_compliance_helpers import run_bridge_compliance_section
from specfact_project.sync_runtime.sync_bridge_github_ado import phase_github_ado_bidirectional
from specfact_project.sync_runtime.sync_bridge_openapi_validation import run_bridge_openapi_bundle_validation
from specfact_project.sync_runtime.sync_command_common import infer_bundle_name, is_test_mode
from specfact_project.sync_runtime.sync_perform_operation_impl import run_perform_sync_operation


console = get_configured_console()


def phase_change_proposal(
    *,
    sync_mode: str,
    adapter_value: str,
    feature: str | None,
    all_features: bool,
    repo: Path,
) -> bool:
    if sync_mode != "change-proposal":
        return False
    if adapter_value != "speckit":
        console.print("[bold red]✗[/bold red] --mode change-proposal is only supported with --adapter speckit")
        raise typer.Exit(1)
    if feature and all_features:
        console.print("[bold red]✗[/bold red] --feature and --all are mutually exclusive")
        raise typer.Exit(1)
    sync_speckit_change_proposals(repo=repo, feature=feature, all_features=all_features, console=console)
    return True


def _export_only_backlog_bundle(
    *,
    repo: Path,
    adapter_value: str,
    bundle: str | None,
    bridge_sync: BridgeSync,
    github_token: str | None,
    ado_token: str | None,
    repo_owner: str | None,
    repo_name: str | None,
    use_gh_cli: bool,
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_work_item_type: str | None,
    update_existing: bool,
    change_ids_list: list[str] | None,
) -> bool:
    if adapter_value not in ("github", "ado") or not bundle:
        return False
    resolved_bundle = bundle or infer_bundle_name(repo)
    if not resolved_bundle:
        console.print("[bold red]✗[/bold red] Bundle name required for backlog export")
        console.print("[dim]Provide --bundle or set an active bundle in .specfact/config.yaml[/dim]")
        raise typer.Exit(1)
    console.print(f"[bold cyan]Exporting bundle backlog items to {adapter_value} ({resolved_bundle})...[/bold cyan]")
    if adapter_value == "github":
        adapter_kwargs: dict[str, Any] = {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "api_token": github_token,
            "use_gh_cli": use_gh_cli,
        }
    else:
        adapter_kwargs = {
            "org": ado_org,
            "project": ado_project,
            "base_url": ado_base_url,
            "api_token": ado_token,
            "work_item_type": ado_work_item_type,
        }
    result = bridge_sync.export_backlog_from_bundle(
        adapter_type=adapter_value,
        bundle_name=resolved_bundle,
        adapter_kwargs=adapter_kwargs,
        update_existing=update_existing,
        change_ids=change_ids_list,
    )
    if result.success:
        console.print(f"[bold green]✓[/bold green] Exported {len(result.operations)} backlog item(s) from bundle")
        for warning in result.warnings:
            console.print(f"[yellow]⚠[/yellow] {warning}")
    else:
        console.print(f"[bold red]✗[/bold red] Export failed with {len(result.errors)} errors")
        for error in result.errors:
            console.print(f"[red]  • {error}[/red]")
        raise typer.Exit(1)
    return True


def phase_export_only(
    *,
    sync_mode: str,
    repo: Path,
    adapter_value: str,
    bundle: str | None,
    github_token: str | None,
    ado_token: str | None,
    repo_owner: str | None,
    repo_name: str | None,
    use_gh_cli: bool,
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_work_item_type: str | None,
    sanitize: bool | None,
    target_repo: str | None,
    interactive: bool,
    change_ids_list: list[str] | None,
    export_to_tmp: bool,
    import_from_tmp: bool,
    tmp_file: Path | None,
    update_existing: bool,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo: Path | None,
    include_archived: bool,
) -> bool:
    if sync_mode != "export-only":
        return False
    console.print(f"[bold cyan]Exporting OpenSpec change proposals to {adapter_value}...[/bold cyan]")
    adapter_instance = AdapterRegistry.get_adapter(adapter_value)
    bridge_config = adapter_instance.generate_bridge_config(repo)
    bridge_sync = BridgeSync(repo, bridge_config=bridge_config)
    if _export_only_backlog_bundle(
        repo=repo,
        adapter_value=adapter_value,
        bundle=bundle,
        bridge_sync=bridge_sync,
        github_token=github_token,
        ado_token=ado_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        use_gh_cli=use_gh_cli,
        ado_org=ado_org,
        ado_project=ado_project,
        ado_base_url=ado_base_url,
        ado_work_item_type=ado_work_item_type,
        update_existing=update_existing,
        change_ids_list=change_ids_list,
    ):
        return True
    progress_columns, progress_kwargs = get_progress_config()
    with Progress(*progress_columns, console=console, **progress_kwargs) as progress:
        task = progress.add_task("[cyan]Syncing change proposals to DevOps...[/cyan]", total=None)
        code_repo_path_for_export = Path(code_repo).resolve() if code_repo else repo.resolve()
        result = bridge_sync.export_change_proposals_to_devops(
            include_archived=include_archived,
            adapter_type=adapter_value,
            repo_owner=repo_owner,
            repo_name=repo_name,
            api_token=github_token if adapter_value == "github" else ado_token,
            use_gh_cli=use_gh_cli,
            sanitize=sanitize,
            target_repo=target_repo,
            interactive=interactive,
            change_ids=change_ids_list,
            export_to_tmp=export_to_tmp,
            import_from_tmp=import_from_tmp,
            tmp_file=tmp_file,
            update_existing=update_existing,
            track_code_changes=track_code_changes,
            add_progress_comment=add_progress_comment,
            code_repo_path=code_repo_path_for_export,
            ado_org=ado_org,
            ado_project=ado_project,
            ado_base_url=ado_base_url,
            ado_work_item_type=ado_work_item_type,
        )
        progress.update(task, description="[green]✓[/green] Sync complete")
    if result.success:
        console.print(f"[bold green]✓[/bold green] Successfully synced {len(result.operations)} change proposals")
        if result.warnings:
            for warning in result.warnings:
                console.print(f"[yellow]⚠[/yellow] {warning}")
    else:
        console.print(f"[bold red]✗[/bold red] Sync failed with {len(result.errors)} errors")
        for error in result.errors:
            console.print(f"[red]  • {error}[/red]")
        raise typer.Exit(1)
    return True


def _import_openspec_specs_for_bundle(bridge_sync: BridgeSync, bridge_config: Any, repo: Path, bundle: str) -> None:
    openspec_specs_dir = (
        bridge_config.external_base_path / "openspec" / "specs"
        if bridge_config.external_base_path
        else repo / "openspec" / "specs"
    )
    if not openspec_specs_dir.exists():
        return
    for spec_dir in openspec_specs_dir.iterdir():
        if spec_dir.is_dir() and (spec_dir / "spec.md").exists():
            feature_id = spec_dir.name
            result = bridge_sync.import_artifact("specification", feature_id, bundle)
            if not result.success:
                console.print(f"[yellow]⚠[/yellow] Failed to import {feature_id}: {', '.join(result.errors)}")


def phase_read_only(
    *,
    sync_mode: str,
    repo: Path,
    bundle: str | None,
    external_base_path: Path | None,
) -> bool:
    if sync_mode != "read-only":
        return False
    from specfact_cli.models.bridge import BridgeConfig

    console.print(f"[bold cyan]Syncing OpenSpec artifacts (read-only) from:[/bold cyan] {repo}")
    bridge_config = BridgeConfig.preset_openspec()
    if external_base_path:
        if not external_base_path.exists() or not external_base_path.is_dir():
            console.print(
                f"[bold red]✗[/bold red] External base path does not exist or is not a directory: {external_base_path}"
            )
            raise typer.Exit(1)
        bridge_config.external_base_path = external_base_path.resolve()
    bridge_sync = BridgeSync(repo, bridge_config=bridge_config)
    if is_test_mode():
        console.print("[cyan]Importing OpenSpec artifacts...[/cyan]")
        if bundle:
            _import_openspec_specs_for_bundle(bridge_sync, bridge_config, repo, bundle)
        console.print("[green]✓[/green] Import complete")
    else:
        progress_columns, progress_kwargs = get_progress_config()
        with Progress(*progress_columns, console=console, **progress_kwargs) as progress:
            task = progress.add_task("[cyan]Importing OpenSpec artifacts...[/cyan]", total=None)
            if bundle:
                _import_openspec_specs_for_bundle(bridge_sync, bridge_config, repo, bundle)
            progress.update(task, description="[green]✓[/green] Import complete")
            progress.refresh()
    if bundle:
        console.print("\n[bold]Generating alignment report...[/bold]")
        bridge_sync.generate_alignment_report(bundle)
    console.print("[bold green]✓[/bold green] Read-only sync complete")
    return True


def _bridge_check_bidirectional_capability(adapter_capabilities: Any, adapter_value: str) -> None:
    if not adapter_capabilities:
        return
    if not adapter_capabilities.supported_sync_modes:
        return
    if "bidirectional" in adapter_capabilities.supported_sync_modes:
        return
    console.print(f"[yellow]⚠ Adapter '{adapter_value}' does not support bidirectional sync[/yellow]")
    console.print(f"[dim]Supported modes: {', '.join(adapter_capabilities.supported_sync_modes)}[/dim]")
    console.print("[dim]Use read-only mode for adapters that don't support bidirectional sync[/dim]")
    raise typer.Exit(1)


def run_sync_bridge_tracked_pipeline(
    *,
    record: Any,
    repo: Path,
    bundle: str | None,
    bidirectional: bool,
    overwrite: bool,
    watch: bool,
    ensure_compliance: bool,
    adapter: str,
    adapter_value: str,
    adapter_type: AdapterType | None,
    adapter_capabilities: Any,
    sync_mode: str,
    feature: str | None,
    all_features: bool,
    repo_owner: str | None,
    repo_name: str | None,
    external_base_path: Path | None,
    github_token: str | None,
    use_gh_cli: bool,
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_token: str | None,
    ado_work_item_type: str | None,
    sanitize: bool | None,
    target_repo: str | None,
    interactive: bool,
    change_ids_list: list[str] | None,
    export_to_tmp: bool,
    import_from_tmp: bool,
    tmp_file: Path | None,
    update_existing: bool,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo: Path | None,
    include_archived: bool,
    interval: int,
    backlog_items: list[str],
) -> None:
    from specfact_cli.runtime import debug_log_operation, debug_print, is_debug_mode

    if phase_change_proposal(
        sync_mode=sync_mode,
        adapter_value=adapter_value,
        feature=feature,
        all_features=all_features,
        repo=repo,
    ):
        return
    if phase_export_only(
        sync_mode=sync_mode,
        repo=repo,
        adapter_value=adapter_value,
        bundle=bundle,
        github_token=github_token,
        ado_token=ado_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        use_gh_cli=use_gh_cli,
        ado_org=ado_org,
        ado_project=ado_project,
        ado_base_url=ado_base_url,
        ado_work_item_type=ado_work_item_type,
        sanitize=sanitize,
        target_repo=target_repo,
        interactive=interactive,
        change_ids_list=change_ids_list,
        export_to_tmp=export_to_tmp,
        import_from_tmp=import_from_tmp,
        tmp_file=tmp_file,
        update_existing=update_existing,
        track_code_changes=track_code_changes,
        add_progress_comment=add_progress_comment,
        code_repo=code_repo,
        include_archived=include_archived,
    ):
        return
    if phase_read_only(sync_mode=sync_mode, repo=repo, bundle=bundle, external_base_path=external_base_path):
        return

    console.print(f"[bold cyan]Syncing {adapter_value} artifacts from:[/bold cyan] {repo}")
    _bridge_check_bidirectional_capability(adapter_capabilities, adapter_value)
    run_bridge_compliance_section(
        ensure_compliance=ensure_compliance,
        bundle=bundle,
        repo=repo,
        adapter_type=adapter_type,
        adapter_value=adapter_value,
    )

    resolved_repo = repo.resolve()
    if not resolved_repo.exists():
        console.print(f"[red]Error:[/red] Repository path does not exist: {resolved_repo}")
        raise typer.Exit(1)
    if not resolved_repo.is_dir():
        console.print(f"[red]Error:[/red] Repository path is not a directory: {resolved_repo}")
        raise typer.Exit(1)

    if phase_github_ado_bidirectional(
        adapter_value=adapter_value,
        sync_mode=sync_mode,
        resolved_repo=resolved_repo,
        bundle=bundle,
        interactive=interactive,
        backlog_items=backlog_items,
        repo_owner=repo_owner,
        repo_name=repo_name,
        github_token=github_token,
        use_gh_cli=use_gh_cli,
        ado_org=ado_org,
        ado_project=ado_project,
        ado_base_url=ado_base_url,
        ado_token=ado_token,
        ado_work_item_type=ado_work_item_type,
        update_existing=update_existing,
        change_ids_list=change_ids_list,
    ):
        return

    if watch:
        from specfact_project.sync_runtime.bridge_watch import BridgeWatch

        console.print("[bold cyan]Watch mode enabled[/bold cyan]")
        console.print(f"[dim]Watching for changes every {interval} seconds[/dim]\n")
        bridge_watch = BridgeWatch(repo_path=resolved_repo, bundle_name=bundle, interval=interval)
        bridge_watch.watch()
        return

    run_bridge_openapi_bundle_validation(bundle, resolved_repo, bidirectional)

    if adapter_type is None:
        console.print(f"[yellow]⚠ Adapter '{adapter_value}' requires bridge-based sync (not legacy)[/yellow]")
        console.print("[dim]Use read-only mode for OpenSpec adapter[/dim]")
        raise typer.Exit(1)

    run_perform_sync_operation(
        repo=resolved_repo,
        bidirectional=bidirectional,
        bundle=bundle,
        overwrite=overwrite,
        adapter_type=adapter_type,
        console=console,
    )
    if is_debug_mode():
        debug_log_operation("command", "sync bridge", "success", extra={"adapter": adapter, "bundle": bundle})
        debug_print("[dim]sync bridge: success[/dim]")
    record({"sync_completed": True})
