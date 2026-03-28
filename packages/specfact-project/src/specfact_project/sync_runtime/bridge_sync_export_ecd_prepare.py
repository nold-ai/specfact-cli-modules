"""Prepare phase for export change proposals (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

from specfact_project.sync_runtime.bridge_sync import SyncResult


def ecd_resolve_adapter_instance(
    adapter_type: str,
    repo_owner: str | None,
    repo_name: str | None,
    api_token: str | None,
    use_gh_cli: bool,
    ado_org: str | None,
    ado_project: str | None,
    ado_base_url: str | None,
    ado_work_item_type: str | None,
    errors: list[str],
) -> Any | None:
    from specfact_cli.adapters.registry import AdapterRegistry

    adapter_class = AdapterRegistry._adapters.get(adapter_type.lower())
    if not adapter_class:
        errors.append(f"Adapter '{adapter_type}' not found in registry")
        return None
    adapter_kwargs: dict[str, Any] = {}
    if adapter_type.lower() == "github":
        adapter_kwargs = {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "api_token": api_token,
            "use_gh_cli": use_gh_cli,
        }
    elif adapter_type.lower() == "ado":
        adapter_kwargs = {
            "org": ado_org,
            "project": ado_project,
            "base_url": ado_base_url,
            "api_token": api_token,
            "work_item_type": ado_work_item_type,
        }
    return AdapterRegistry.get_adapter(adapter_type, **adapter_kwargs)


def ecd_read_change_proposals(
    bridge: Any,
    include_archived: bool,
    operations: list[Any],
    errors: list[str],
    warnings: list[str],
) -> list[dict[str, Any]] | SyncResult:
    try:
        return bridge._read_openspec_change_proposals(include_archived=include_archived)
    except Exception as e:
        warnings.append(f"OpenSpec adapter not available: {e}. Skipping change proposal sync.")
        return SyncResult(success=True, operations=operations, errors=errors, warnings=warnings)


def ecd_build_sanitizer_state(
    bridge: Any,
    sanitize: bool | None,
) -> tuple[Any, Any, Path]:
    from specfact_project.utils.content_sanitizer import ContentSanitizer

    sanitizer = ContentSanitizer()
    planning_repo = bridge.repo_path
    if bridge.bridge_config and hasattr(bridge.bridge_config, "external_base_path"):
        external_path = getattr(bridge.bridge_config, "external_base_path", None)
        if external_path:
            planning_repo = Path(external_path)
    should_sanitize = sanitizer.detect_sanitization_need(
        code_repo=bridge.repo_path,
        planning_repo=planning_repo,
        user_preference=sanitize,
    )
    return sanitizer, should_sanitize, planning_repo


def ecd_resolve_target_repo_string(
    target_repo: str | None,
    adapter_type: str,
    ado_org: str | None,
    ado_project: str | None,
    repo_owner: str | None,
    repo_name: str | None,
) -> str | None:
    if target_repo:
        return target_repo
    if adapter_type == "ado" and ado_org and ado_project:
        return f"{ado_org}/{ado_project}"
    if repo_owner and repo_name:
        return f"{repo_owner}/{repo_name}"
    return None


def ecd_filter_proposals_by_sync_rules(
    bridge: Any,
    change_proposals: list[dict[str, Any]],
    should_sanitize: bool,
    target_repo: str | None,
    warnings: list[str],
) -> list[dict[str, Any]]:
    active_proposals: list[dict[str, Any]] = []
    filtered_count = 0
    for proposal in change_proposals:
        proposal_status = proposal.get("status", "proposed")
        source_tracking_raw = proposal.get("source_tracking", {})
        target_entry = bridge._find_source_tracking_entry(source_tracking_raw, target_repo)
        has_target_entry = target_entry is not None
        if should_sanitize:
            should_sync = proposal_status == "applied"
        elif has_target_entry:
            should_sync = True
        else:
            should_sync = proposal_status in (
                "proposed",
                "in-progress",
                "applied",
                "deprecated",
                "discarded",
            )
        if should_sync:
            active_proposals.append(proposal)
        else:
            filtered_count += 1
    if filtered_count > 0:
        if should_sanitize:
            warnings.append(
                f"Filtered out {filtered_count} proposal(s) with non-applied status "
                f"(public repos only sync archived/completed proposals, regardless of source tracking). "
                f"Only {len(active_proposals)} applied proposal(s) will be synced."
            )
        else:
            warnings.append(
                f"Filtered out {filtered_count} proposal(s) without source tracking entry for target repo "
                f"and inactive status. Only {len(active_proposals)} proposal(s) will be synced."
            )
    return active_proposals


def ecd_apply_change_id_filter(
    active_proposals: list[dict[str, Any]],
    change_ids: list[str] | None,
    errors: list[str],
) -> list[dict[str, Any]]:
    if not change_ids:
        return active_proposals
    valid_change_ids = set(change_ids)
    available_change_ids = {p.get("change_id") for p in active_proposals if p.get("change_id")}
    available_change_ids = {cid for cid in available_change_ids if cid is not None}
    invalid_change_ids = valid_change_ids - available_change_ids
    if invalid_change_ids:
        errors.append(
            f"Invalid change IDs: {', '.join(sorted(invalid_change_ids))}. "
            f"Available: {', '.join(sorted(available_change_ids)) if available_change_ids else 'none'}"
        )
    return [p for p in active_proposals if p.get("change_id") in valid_change_ids]
