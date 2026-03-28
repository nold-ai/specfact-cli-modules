"""Implementation of `sync bridge` CLI (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

from specfact_cli.runtime import debug_log_operation, debug_print, get_configured_console, is_debug_mode
from specfact_cli.telemetry import telemetry

from specfact_project.sync_runtime.sync_bridge_command_setup import (
    adapter_type_from_lower,
    ensure_adapter_detected_or_exit,
    ensure_registered_adapter_or_exit,
    parse_change_and_backlog_ids,
    resolve_sync_mode,
    validate_sync_mode_for_adapter_or_exit,
    validate_tmp_flags_or_exit,
)


console = get_configured_console()


def run_sync_bridge_command(
    repo: Path,
    bundle: str | None,
    bidirectional: bool,
    mode: str | None,
    feature: str | None,
    all_features: bool,
    overwrite: bool,
    watch: bool,
    ensure_compliance: bool,
    adapter: str,
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
    change_ids: str | None,
    backlog_ids: str | None,
    backlog_ids_file: Path | None,
    export_to_tmp: bool,
    import_from_tmp: bool,
    tmp_file: Path | None,
    update_existing: bool,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo: Path | None,
    include_archived: bool,
    interval: int,
) -> None:
    if is_debug_mode():
        debug_log_operation(
            "command",
            "sync bridge",
            "started",
            extra={"repo": str(repo), "bundle": bundle, "adapter": adapter, "bidirectional": bidirectional},
        )
        debug_print("[dim]sync bridge: started[/dim]")

    adapter = ensure_adapter_detected_or_exit(repo, adapter)
    adapter_lower = ensure_registered_adapter_or_exit(adapter)
    adapter_type = adapter_type_from_lower(adapter_lower)
    adapter_value = adapter_type.value if adapter_type else adapter_lower
    sync_mode = resolve_sync_mode(mode, bidirectional, repo, adapter_lower, repo_owner, repo_name)
    adapter_capabilities: Any | None = validate_sync_mode_for_adapter_or_exit(sync_mode, adapter_lower, repo)
    validate_tmp_flags_or_exit(export_to_tmp, import_from_tmp)
    change_ids_list, backlog_items = parse_change_and_backlog_ids(change_ids, backlog_ids, backlog_ids_file)

    telemetry_metadata = {
        "adapter": adapter_value,
        "mode": sync_mode,
        "bidirectional": bidirectional,
        "watch": watch,
        "overwrite": overwrite,
        "interval": interval,
    }

    with telemetry.track_command("sync.bridge", telemetry_metadata) as record:
        from specfact_project.sync_runtime.sync_bridge_phases import run_sync_bridge_tracked_pipeline

        run_sync_bridge_tracked_pipeline(
            record=record,
            repo=repo,
            bundle=bundle,
            bidirectional=bidirectional,
            overwrite=overwrite,
            watch=watch,
            ensure_compliance=ensure_compliance,
            adapter=adapter,
            adapter_value=adapter_value,
            adapter_type=adapter_type,
            adapter_capabilities=adapter_capabilities,
            sync_mode=sync_mode,
            feature=feature,
            all_features=all_features,
            repo_owner=repo_owner,
            repo_name=repo_name,
            external_base_path=external_base_path,
            github_token=github_token,
            use_gh_cli=use_gh_cli,
            ado_org=ado_org,
            ado_project=ado_project,
            ado_base_url=ado_base_url,
            ado_token=ado_token,
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
            interval=interval,
            backlog_items=backlog_items,
        )
