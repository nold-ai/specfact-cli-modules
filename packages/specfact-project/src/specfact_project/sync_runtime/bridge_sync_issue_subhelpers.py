"""Small helpers for issue / progress sync (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any


def uicn_compute_current_hash(
    bridge: Any, proposal: dict[str, Any], import_from_tmp: bool, tmp_file: Path | None
) -> str:
    if import_from_tmp:
        change_id = proposal.get("change_id", "unknown")
        sanitized_file = tmp_file or (Path(tempfile.gettempdir()) / f"specfact-proposal-{change_id}-sanitized.md")
        if sanitized_file.exists():
            sanitized_content = sanitized_file.read_text(encoding="utf-8")
            proposal_for_hash = {"rationale": "", "description": sanitized_content}
            return bridge._calculate_content_hash(proposal_for_hash)
        return bridge._calculate_content_hash(proposal)
    return bridge._calculate_content_hash(proposal)


def uicn_github_title_state(
    adapter_instance: Any,
    repo_owner: str | None,
    repo_name: str | None,
    issue_num: Any,
    proposal: dict[str, Any],
) -> tuple[str | None, str | None, bool, bool]:
    import requests

    proposal_title = proposal.get("title", "")
    proposal_status = proposal.get("status", "proposed")
    url = f"{adapter_instance.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_num}"
    headers = {
        "Authorization": f"token {adapter_instance.api_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    issue_data = response.json()
    current_issue_title = issue_data.get("title", "")
    current_issue_state = issue_data.get("state", "open")
    needs_title_update = current_issue_title and proposal_title and current_issue_title != proposal_title
    should_close = proposal_status in ("applied", "deprecated", "discarded")
    desired_state = "closed" if should_close else "open"
    needs_state_update = current_issue_state != desired_state
    return current_issue_title, current_issue_state, needs_title_update, needs_state_update


def uicn_ado_title_state(
    adapter_instance: Any,
    issue_num: Any,
    ado_org: str,
    ado_project: str,
    proposal: dict[str, Any],
) -> tuple[str | None, str | None, bool, bool]:
    proposal_title = proposal.get("title", "")
    proposal_status = proposal.get("status", "proposed")
    work_item_data = adapter_instance._get_work_item_data(issue_num, ado_org, ado_project)
    if not work_item_data:
        return None, None, False, False
    current_issue_title = work_item_data.get("title", "")
    current_issue_state = work_item_data.get("state", "")
    needs_title_update = current_issue_title and proposal_title and current_issue_title != proposal_title
    desired_ado_state = adapter_instance.map_openspec_status_to_backlog(proposal_status)
    needs_state_update = current_issue_state != desired_ado_state
    return current_issue_title, current_issue_state, needs_title_update, needs_state_update


def uicn_fetch_title_state_flags(
    adapter_type: str,
    target_entry: dict[str, Any],
    repo_owner: str | None,
    repo_name: str | None,
    ado_org: str | None,
    ado_project: str | None,
    proposal: dict[str, Any],
) -> tuple[bool, bool]:
    if not target_entry:
        return False, False
    issue_num = target_entry.get("source_id")
    if not issue_num:
        return False, False
    try:
        from specfact_cli.adapters.registry import AdapterRegistry

        adapter_instance = AdapterRegistry.get_adapter(adapter_type)
        if not adapter_instance or not hasattr(adapter_instance, "api_token"):
            return False, False
        if adapter_type.lower() == "github":
            _t, _s, nt, ns = uicn_github_title_state(adapter_instance, repo_owner, repo_name, issue_num, proposal)
            return nt, ns
        if (
            adapter_type.lower() == "ado"
            and hasattr(adapter_instance, "_get_work_item_data")
            and ado_org
            and ado_project
        ):
            _t, _s, nt, ns = uicn_ado_title_state(adapter_instance, issue_num, ado_org, ado_project, proposal)
            return nt, ns
    except Exception as e:
        logging.getLogger(__name__).warning(
            "uicn_fetch_title_state_flags failed for adapter_type=%s, issue_num=%s: %s",
            adapter_type,
            issue_num,
            e,
        )
    return False, False


def uicn_needs_applied_github_comment(
    adapter_type: str,
    proposal: dict[str, Any],
    target_entry: dict[str, Any],
    repo_owner: str | None,
    repo_name: str | None,
) -> bool:
    if proposal.get("status") != "applied" or not target_entry:
        return False
    issue_num = target_entry.get("source_id")
    if not issue_num or adapter_type.lower() != "github":
        return False
    try:
        import requests
        from specfact_cli.adapters.registry import AdapterRegistry

        adapter_instance = AdapterRegistry.get_adapter(adapter_type)
        if not adapter_instance or not hasattr(adapter_instance, "api_token") or not adapter_instance.api_token:
            return False
        url = f"{adapter_instance.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_num}"
        headers = {
            "Authorization": f"token {adapter_instance.api_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        issue_data = response.json()
        return issue_data.get("state", "open") == "closed"
    except Exception:
        return False


def uicn_build_proposal_for_update(
    proposal: dict[str, Any],
    import_from_tmp: bool,
    tmp_file: Path | None,
) -> dict[str, Any]:
    if not import_from_tmp:
        return proposal
    change_id = proposal.get("change_id", "unknown")
    sanitized_file = tmp_file or (Path(tempfile.gettempdir()) / f"specfact-proposal-{change_id}-sanitized.md")
    if sanitized_file.exists():
        sanitized_content = sanitized_file.read_text(encoding="utf-8")
        return {**proposal, "description": sanitized_content, "rationale": ""}
    return proposal


def uicn_export_update_body(
    adapter: Any,
    bridge: Any,
    proposal_for_update: dict[str, Any],
    repo_owner: str | None,
    repo_name: str | None,
    needs_comment_for_applied: bool,
    stored_hash: Any,
    current_hash: str,
    needs_title_update: bool,
    needs_state_update: bool,
) -> None:
    code_repo_path = None
    if repo_owner and repo_name:
        code_repo_path = bridge._find_code_repo_path(repo_owner, repo_name)
    path_val = str(code_repo_path) if code_repo_path else None
    proposal_with_repo = {**proposal_for_update, "_code_repo_path": path_val}
    comment_only = needs_comment_for_applied and not (
        stored_hash != current_hash or needs_title_update or needs_state_update
    )
    key = "change_proposal_comment" if comment_only else "change_proposal_update"
    adapter.export_artifact(
        artifact_key=key,
        artifact_data=proposal_with_repo,
        bridge_config=bridge.bridge_config,
    )


def uei_patch_list_source_tracking(
    source_tracking_list: list[dict[str, Any]],
    updated_entry: dict[str, Any],
) -> None:
    for i, entry in enumerate(source_tracking_list):
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("source_id")
        entry_repo = entry.get("source_repo")
        updated_id = updated_entry.get("source_id")
        updated_repo = updated_entry.get("source_repo")
        if (entry_id and entry_id == updated_id) or (entry_repo and entry_repo == updated_repo):
            source_tracking_list[i] = updated_entry
            break


def hcct_load_last_detection(target_entry: dict[str, Any] | None) -> Any:
    if not target_entry:
        return None
    source_metadata = target_entry.get("source_metadata", {})
    if isinstance(source_metadata, dict):
        return source_metadata.get("last_code_change_detected")
    return None


def hcct_try_detect_changes(
    bridge: Any,
    code_repo_path: Path | None,
    change_id: str,
    last_detection: Any,
    errors: list[str],
) -> tuple[bool, dict[str, Any] | None]:
    """Returns (stop_caller, progress_data_or_none)."""
    from specfact_project.utils.code_change_detector import detect_code_changes

    try:
        code_repo = code_repo_path if code_repo_path else bridge.repo_path
        code_changes = detect_code_changes(
            repo_path=code_repo,
            change_id=change_id,
            since_timestamp=last_detection,
        )
        if code_changes.get("has_changes"):
            return False, code_changes
        return True, None
    except Exception as e:
        errors.append(f"Failed to detect code changes for {change_id}: {e}")
        return True, None


def hcct_comment_is_duplicate(comment_hash: str, progress_comments: Any) -> bool:
    if not isinstance(progress_comments, list):
        return False
    for existing_comment in progress_comments:
        if isinstance(existing_comment, dict) and existing_comment.get("comment_hash") == comment_hash:
            return True
    return False


def hcct_persist_progress_comment(
    bridge: Any,
    proposal: dict[str, Any],
    target_entry: dict[str, Any] | None,
    target_repo: str | None,
    source_tracking_list: list[dict[str, Any]],
    progress_data: dict[str, Any],
    comment_hash: str,
    should_sanitize: bool | None,
    adapter: Any,
    operations: list[Any],
) -> None:
    from specfact_project.sync_runtime.bridge_sync import SyncOperation
    from specfact_project.sync_runtime.bridge_sync_source_tracking_list_impl import run_update_source_tracking_entry

    proposal_with_progress = {
        **proposal,
        "source_tracking": source_tracking_list,
        "progress_data": progress_data,
        "sanitize": should_sanitize if should_sanitize is not None else False,
    }
    adapter.export_artifact(
        artifact_key="code_change_progress",
        artifact_data=proposal_with_progress,
        bridge_config=bridge.bridge_config,
    )
    if target_entry:
        source_metadata = target_entry.get("source_metadata", {})
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        progress_comments = source_metadata.get("progress_comments", [])
        if not isinstance(progress_comments, list):
            progress_comments = []
        progress_comments.append(
            {
                "comment_hash": comment_hash,
                "timestamp": progress_data.get("detection_timestamp"),
                "summary": progress_data.get("summary", ""),
            }
        )
        updated_entry = {
            **target_entry,
            "source_metadata": {
                **source_metadata,
                "progress_comments": progress_comments,
                "last_code_change_detected": progress_data.get("detection_timestamp"),
            },
        }
        if target_repo:
            new_list = run_update_source_tracking_entry(bridge, source_tracking_list, target_repo, updated_entry)
            proposal["source_tracking"] = new_list
    operations.append(
        SyncOperation(
            artifact_key="code_change_progress",
            feature_id=proposal.get("change_id", "unknown"),
            direction="export",
            bundle_name="openspec",
        )
    )
    bridge._save_openspec_change_proposal(proposal)
