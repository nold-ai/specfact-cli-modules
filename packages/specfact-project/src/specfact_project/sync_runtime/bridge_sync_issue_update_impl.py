"""Bridge sync helpers (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specfact_project.sync_runtime.bridge_sync import SyncOperation
from specfact_project.sync_runtime.bridge_sync_issue_subhelpers import (
    hcct_comment_is_duplicate,
    hcct_load_last_detection,
    hcct_persist_progress_comment,
    hcct_try_detect_changes,
    uei_patch_list_source_tracking,
    uicn_build_proposal_for_update,
    uicn_compute_current_hash,
    uicn_export_update_body,
    uicn_fetch_title_state_flags,
    uicn_needs_applied_github_comment,
)
from specfact_project.sync_runtime.bridge_sync_source_tracking_list_impl import run_update_source_tracking_entry


def run_update_issue_content_if_needed(
    bridge: Any,
    proposal: dict[str, Any],
    target_entry: dict[str, Any],
    issue_number: str | int,
    adapter: Any,
    adapter_type: str,
    target_repo: str | None,
    source_tracking_list: list[dict[str, Any]],
    repo_owner: str | None,
    repo_name: str | None,
    ado_org: str | None,
    ado_project: str | None,
    import_from_tmp: bool,
    tmp_file: Path | None,
    operations: list[Any],
    errors: list[str],
) -> None:
    _ = issue_number
    current_hash = uicn_compute_current_hash(bridge, proposal, import_from_tmp, tmp_file)
    stored_hash = None
    source_metadata = target_entry.get("source_metadata", {})
    if isinstance(source_metadata, dict):
        stored_hash = source_metadata.get("content_hash")
    needs_title_update, needs_state_update = (False, False)
    if target_entry:
        needs_title_update, needs_state_update = uicn_fetch_title_state_flags(
            adapter_type, target_entry, repo_owner, repo_name, ado_org, ado_project, proposal
        )
    needs_comment_for_applied = uicn_needs_applied_github_comment(
        adapter_type, proposal, target_entry, repo_owner, repo_name
    )
    if not (stored_hash != current_hash or needs_title_update or needs_state_update or needs_comment_for_applied):
        return
    try:
        proposal_for_update = uicn_build_proposal_for_update(proposal, import_from_tmp, tmp_file)
        uicn_export_update_body(
            adapter,
            bridge,
            proposal_for_update,
            repo_owner,
            repo_name,
            needs_comment_for_applied,
            stored_hash,
            current_hash,
            needs_title_update,
            needs_state_update,
        )
        if target_entry:
            sm = target_entry.get("source_metadata", {})
            if not isinstance(sm, dict):
                sm = {}
            updated_entry = {
                **target_entry,
                "source_metadata": {**sm, "content_hash": current_hash},
            }
            if target_repo:
                source_tracking_list = run_update_source_tracking_entry(
                    bridge, source_tracking_list, target_repo, updated_entry
                )
                proposal["source_tracking"] = source_tracking_list
        operations.append(
            SyncOperation(
                artifact_key="change_proposal_update",
                feature_id=proposal.get("change_id", "unknown"),
                direction="export",
                bundle_name="openspec",
            )
        )
    except Exception as e:
        errors.append(f"Failed to update issue body for {proposal.get('change_id', 'unknown')}: {e}")


def run_handle_code_change_tracking(
    bridge: Any,
    proposal: dict[str, Any],
    target_entry: dict[str, Any] | None,
    target_repo: str | None,
    source_tracking_list: list[dict[str, Any]],
    adapter: Any,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo_path: Path | None,
    should_sanitize: bool | None,
    operations: list[Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    from specfact_project.utils.code_change_detector import calculate_comment_hash, format_progress_comment

    change_id = proposal.get("change_id", "unknown")
    progress_data: dict[str, Any] = {}
    if track_code_changes:
        stop, pdata = hcct_try_detect_changes(
            bridge, code_repo_path, change_id, hcct_load_last_detection(target_entry), errors
        )
        if stop:
            return
        if pdata is None:
            return
        progress_data = pdata
    if add_progress_comment and not progress_data:
        progress_data = {
            "summary": "Manual progress update",
            "detection_timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    if not progress_data:
        return
    comment_text = format_progress_comment(
        progress_data, sanitize=should_sanitize if should_sanitize is not None else False
    )
    comment_hash = calculate_comment_hash(comment_text)
    progress_comments: list[Any] = []
    if target_entry:
        sm = target_entry.get("source_metadata", {})
        if isinstance(sm, dict):
            progress_comments = sm.get("progress_comments", [])
    if hcct_comment_is_duplicate(comment_hash, progress_comments):
        warnings.append(f"Skipped duplicate progress comment for {change_id}")
        return
    try:
        hcct_persist_progress_comment(
            bridge,
            proposal,
            target_entry,
            target_repo,
            source_tracking_list,
            progress_data,
            comment_hash,
            should_sanitize,
            adapter,
            operations,
        )
    except Exception as e:
        errors.append(f"Failed to add progress comment for {change_id}: {e}")


def run_update_existing_issue(
    bridge: Any,
    proposal: dict[str, Any],
    target_entry: dict[str, Any],
    issue_number: str | int,
    adapter: Any,
    adapter_type: str,
    target_repo: str | None,
    source_tracking_list: list[dict[str, Any]],
    source_tracking_raw: dict[str, Any] | list[dict[str, Any]],
    repo_owner: str | None,
    repo_name: str | None,
    ado_org: str | None,
    ado_project: str | None,
    update_existing: bool,
    import_from_tmp: bool,
    tmp_file: Path | None,
    should_sanitize: bool | None,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo_path: Path | None,
    operations: list[Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    # Issue exists - check if status changed or metadata needs update
    source_metadata = target_entry.get("source_metadata", {})
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    last_synced_status = source_metadata.get("last_synced_status")
    current_status = proposal.get("status")

    if last_synced_status != current_status:
        # Status changed - update issue
        adapter.export_artifact(
            artifact_key="change_status",
            artifact_data=proposal,
            bridge_config=bridge.bridge_config,
        )
        # Track status update operation
        operations.append(
            SyncOperation(
                artifact_key="change_status",
                feature_id=proposal.get("change_id", "unknown"),
                direction="export",
                bundle_name="openspec",
            )
        )

    # Always update metadata to ensure it reflects the current sync operation
    source_metadata = target_entry.get("source_metadata", {})
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    updated_entry = {
        **target_entry,
        "source_metadata": {
            **source_metadata,
            "last_synced_status": current_status,
            "sanitized": should_sanitize if should_sanitize is not None else False,
        },
    }

    # Always update source_tracking metadata to reflect current sync operation
    if target_repo:
        source_tracking_list = run_update_source_tracking_entry(
            bridge, source_tracking_list, target_repo, updated_entry
        )
        proposal["source_tracking"] = source_tracking_list
    else:
        # Backward compatibility: update single dict entry directly
        if isinstance(source_tracking_raw, dict):
            proposal["source_tracking"] = updated_entry
        else:
            uei_patch_list_source_tracking(source_tracking_list, updated_entry)
            proposal["source_tracking"] = source_tracking_list

    # Track metadata update operation (even if status didn't change)
    if last_synced_status == current_status:
        operations.append(
            SyncOperation(
                artifact_key="change_proposal_metadata",
                feature_id=proposal.get("change_id", "unknown"),
                direction="export",
                bundle_name="openspec",
            )
        )

    # Check if content changed (when update_existing is enabled)
    if update_existing:
        run_update_issue_content_if_needed(
            bridge,
            proposal,
            target_entry,
            issue_number,
            adapter,
            adapter_type,
            target_repo,
            source_tracking_list,
            repo_owner,
            repo_name,
            ado_org,
            ado_project,
            import_from_tmp,
            tmp_file,
            operations,
            errors,
        )

    # Code change tracking and progress comments (when enabled)
    if track_code_changes or add_progress_comment:
        run_handle_code_change_tracking(
            bridge,
            proposal,
            target_entry,
            target_repo,
            source_tracking_list,
            adapter,
            track_code_changes,
            add_progress_comment,
            code_repo_path,
            should_sanitize,
            operations,
            errors,
            warnings,
        )
