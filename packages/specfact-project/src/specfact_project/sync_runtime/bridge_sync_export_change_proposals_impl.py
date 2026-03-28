"""Export change proposals to DevOps — implementation (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

from specfact_project.sync_runtime.bridge_sync import SyncOperation, SyncResult
from specfact_project.sync_runtime.bridge_sync_export_ecd_prepare import (
    ecd_apply_change_id_filter,
    ecd_build_sanitizer_state,
    ecd_filter_proposals_by_sync_rules,
    ecd_read_change_proposals,
    ecd_resolve_adapter_instance,
    ecd_resolve_target_repo_string,
)


def run_export_change_proposals_to_devops(
    bridge: Any,
    adapter_type: str,
    repo_owner: str | None = None,
    repo_name: str | None = None,
    api_token: str | None = None,
    use_gh_cli: bool = True,
    sanitize: bool | None = None,
    target_repo: str | None = None,
    interactive: bool = False,
    change_ids: list[str] | None = None,
    export_to_tmp: bool = False,
    import_from_tmp: bool = False,
    tmp_file: Path | None = None,
    update_existing: bool = False,
    track_code_changes: bool = False,
    add_progress_comment: bool = False,
    code_repo_path: Path | None = None,
    include_archived: bool = False,
    ado_org: str | None = None,
    ado_project: str | None = None,
    ado_base_url: str | None = None,
    ado_work_item_type: str | None = None,
) -> SyncResult:
    operations: list[SyncOperation] = []
    errors: list[str] = []
    warnings: list[str] = []

    try:
        adapter = ecd_resolve_adapter_instance(
            adapter_type,
            repo_owner,
            repo_name,
            api_token,
            use_gh_cli,
            ado_org,
            ado_project,
            ado_base_url,
            ado_work_item_type,
            errors,
        )
        if adapter is None:
            return SyncResult(success=False, operations=[], errors=errors, warnings=warnings)

        read_out = ecd_read_change_proposals(bridge, include_archived, operations, errors, warnings)
        if isinstance(read_out, SyncResult):
            return read_out
        change_proposals = read_out

        sanitizer, should_sanitize, _planning_repo = ecd_build_sanitizer_state(bridge, sanitize)
        target_repo = ecd_resolve_target_repo_string(
            target_repo, adapter_type, ado_org, ado_project, repo_owner, repo_name
        )
        active_proposals = ecd_filter_proposals_by_sync_rules(
            bridge, change_proposals, should_sanitize, target_repo, warnings
        )
        active_proposals = ecd_apply_change_id_filter(active_proposals, change_ids, errors)

        from specfact_project.sync_runtime.bridge_sync_export_change_proposals_loop import ecd_iterate_active_proposals

        ecd_iterate_active_proposals(
            bridge,
            active_proposals,
            adapter,
            adapter_type,
            target_repo,
            repo_owner,
            repo_name,
            ado_org,
            ado_project,
            update_existing,
            import_from_tmp,
            tmp_file,
            export_to_tmp,
            should_sanitize,
            track_code_changes,
            add_progress_comment,
            code_repo_path,
            sanitizer,
            operations,
            errors,
            warnings,
        )
    except Exception as e:
        errors.append(f"Export to DevOps failed: {e}")

    return SyncResult(
        success=len(errors) == 0,
        operations=operations,
        errors=errors,
        warnings=warnings,
    )
