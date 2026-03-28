"""Import/export bundle backlog operations (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
from typing import Any

from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.utils.bundle_loader import load_project_bundle, save_project_bundle
from specfact_cli.utils.structure import SpecFactStructure

from specfact_project.sync_runtime.bridge_sync_backlog_helpers import get_backlog_entries_list


logger = logging.getLogger(__name__)


def _ibi_match_entry_to_item(entry: dict[str, Any], item_ref_str: str, item_ref_clean: str) -> bool:
    entry_id = entry.get("source_id")
    if not entry_id:
        return False
    entry_id_str = str(entry_id)
    return entry_id_str in (item_ref_str, item_ref_clean) or item_ref_str.endswith(
        (f"/{entry_id_str}", f"#{entry_id_str}")
    )


def _ibi_find_proposal_by_backlog_id(project_bundle: Any, item_ref: Any) -> Any | None:
    if not hasattr(project_bundle, "change_tracking") or not project_bundle.change_tracking:
        return None
    item_ref_clean = str(item_ref).rsplit("/", maxsplit=1)[-1]
    item_ref_str = str(item_ref)
    logger.debug("Looking for proposal matching backlog item '%s' (clean: '%s')", item_ref, item_ref_clean)
    for proposal in project_bundle.change_tracking.proposals.values():
        if not proposal.source_tracking:
            continue
        source_metadata = proposal.source_tracking.source_metadata
        if not isinstance(source_metadata, dict):
            continue
        backlog_entries = source_metadata.get("backlog_entries", [])
        for entry in backlog_entries:
            if isinstance(entry, dict) and _ibi_match_entry_to_item(entry, item_ref_str, item_ref_clean):
                logger.debug("Found proposal '%s' by source_id match", proposal.name)
                return proposal
    return None


def _ibi_fallback_last_proposal(project_bundle: Any, adapter_type: str) -> Any | None:
    if not project_bundle.change_tracking.proposals:
        return None
    proposal_list = list(project_bundle.change_tracking.proposals.values())
    if not proposal_list:
        return None
    imported_proposal = proposal_list[-1]
    if imported_proposal.source_tracking:
        source_tool = imported_proposal.source_tracking.tool
        if source_tool != adapter_type:
            logger.debug(
                "Fallback proposal has different source tool (%s vs %s), using as fallback",
                source_tool,
                adapter_type,
            )
    return imported_proposal


def _ibi_process_after_import(
    bridge: Any,
    project_bundle: Any,
    item_ref: Any,
    adapter_type: str,
    bridge_config: Any,
    warnings: list[str],
) -> None:
    imported_proposal = _ibi_find_proposal_by_backlog_id(project_bundle, item_ref)
    if not imported_proposal:
        imported_proposal = _ibi_fallback_last_proposal(project_bundle, adapter_type)
    if imported_proposal:
        file_warnings = bridge._write_openspec_change_from_proposal(imported_proposal, bridge_config)
        warnings.extend(file_warnings)
        return
    warning_msg = (
        f"Could not find imported proposal for backlog item '{item_ref}'. "
        f"OpenSpec files will not be created. "
        f"Proposals in bundle: {list(project_bundle.change_tracking.proposals.keys()) if project_bundle.change_tracking.proposals else 'none'}"
    )
    logger.warning("%s", warning_msg)
    warnings.append(warning_msg)


def run_import_backlog_items_to_bundle(
    bridge: Any,
    adapter_type: str,
    bundle_name: str,
    backlog_items: list[str],
    adapter_kwargs: dict[str, Any] | None,
) -> Any:
    from specfact_project.sync_runtime.bridge_sync import SyncOperation, SyncResult

    operations: list[SyncOperation] = []
    errors: list[str] = []
    warnings: list[str] = []
    adapter_kwargs = adapter_kwargs or {}
    adapter = AdapterRegistry.get_adapter(adapter_type, **adapter_kwargs)
    artifact_key_map = {"github": "github_issue", "ado": "ado_work_item"}
    artifact_key = artifact_key_map.get(adapter_type)
    if not artifact_key:
        errors.append(f"Unsupported backlog adapter: {adapter_type}")
        return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)
    if not hasattr(adapter, "fetch_backlog_item"):
        errors.append(f"Adapter '{adapter_type}' does not support backlog fetch operations")
        return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)
    bundle_dir = SpecFactStructure.project_dir(base_path=bridge.repo_path, bundle_name=bundle_name)
    if not bundle_dir.exists():
        errors.append(f"Project bundle not found: {bundle_dir}")
        return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)
    project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)
    bridge_config = adapter.generate_bridge_config(bridge.repo_path)
    for item_ref in backlog_items:
        try:
            item_data = adapter.fetch_backlog_item(item_ref)
            adapter.import_artifact(artifact_key, item_data, project_bundle, bridge_config)
            if hasattr(project_bundle, "change_tracking") and project_bundle.change_tracking:
                _ibi_process_after_import(bridge, project_bundle, item_ref, adapter_type, bridge_config, warnings)
            operations.append(
                SyncOperation(
                    artifact_key=artifact_key,
                    feature_id=str(item_ref),
                    direction="import",
                    bundle_name=bundle_name,
                )
            )
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
            errors.append(f"Failed to import backlog item '{item_ref}': {e}")
        except (KeyboardInterrupt, MemoryError, SystemExit):
            raise
    if operations:
        save_project_bundle(project_bundle, bundle_dir, atomic=True)
    return SyncResult(
        success=len(errors) == 0,
        operations=operations,
        errors=errors,
        warnings=warnings,
    )


def _ebb_resolve_target_repo(adapter: Any, adapter_type: str) -> str | None:
    if adapter_type == "github":
        repo_owner = getattr(adapter, "repo_owner", None)
        repo_name = getattr(adapter, "repo_name", None)
        if repo_owner and repo_name:
            return f"{repo_owner}/{repo_name}"
        return None
    if adapter_type == "ado":
        org = getattr(adapter, "org", None)
        project = getattr(adapter, "project", None)
        if org and project:
            return f"{org}/{project}"
    return None


def _ebb_collect_source_state(entries: list[dict[str, Any]], adapter_type: str) -> tuple[Any, Any] | None:
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_type = entry.get("source_type", "").lower()
        if not entry_type or entry_type == adapter_type.lower():
            continue
        source_metadata = entry.get("source_metadata", {})
        entry_source_state = source_metadata.get("source_state")
        if entry_source_state:
            return entry_source_state, entry_type
    return None


def _ebb_apply_raw_metadata(proposal: Any, proposal_dict: dict[str, Any]) -> None:
    if not isinstance(proposal.source_tracking.source_metadata, dict):
        return
    raw_title = proposal.source_tracking.source_metadata.get("raw_title")
    raw_body = proposal.source_tracking.source_metadata.get("raw_body")
    if raw_title:
        proposal_dict["raw_title"] = raw_title
    if raw_body:
        proposal_dict["raw_body"] = raw_body


def _ebb_entry_by_repo(entries: list[dict[str, Any]], target_repo: str) -> dict[str, Any] | None:
    return next((e for e in entries if isinstance(e, dict) and e.get("source_repo") == target_repo), None)


def _ebb_entry_by_adapter(entries: list[dict[str, Any]], adapter_type: str) -> dict[str, Any] | None:
    return next(
        (e for e in entries if isinstance(e, dict) and e.get("source_type") == adapter_type and e.get("source_id")),
        None,
    )


def _ebb_merge_speckit_mappings(
    bridge: Any,
    proposal: Any,
    entries: list[dict[str, Any]],
    adapter_type: str,
) -> dict[str, Any] | None:
    imported_mappings = bridge._detect_speckit_backlog_mappings_for_proposal(proposal.name, adapter_type)
    if not imported_mappings:
        return None
    entries.extend(imported_mappings)
    if isinstance(proposal.source_tracking.source_metadata, dict):
        proposal.source_tracking.source_metadata["backlog_entries"] = entries
    return _ebb_entry_by_adapter(imported_mappings, adapter_type)


def _ebb_resolve_target_entry(
    bridge: Any,
    proposal: Any,
    entries: list[dict[str, Any]],
    adapter_type: str,
    target_repo: str | None,
) -> dict[str, Any] | None:
    if target_repo:
        by_repo = _ebb_entry_by_repo(entries, target_repo)
        if by_repo:
            return by_repo
    by_adapter = _ebb_entry_by_adapter(entries, adapter_type)
    if by_adapter:
        return by_adapter
    return _ebb_merge_speckit_mappings(bridge, proposal, entries, adapter_type)


def _ebb_export_one_proposal(
    bridge: Any,
    proposal: Any,
    adapter: Any,
    bridge_config: Any,
    adapter_type: str,
    bundle_name: str,
    target_repo: str | None,
    update_existing: bool,
    entries: list[dict[str, Any]],
    operations: list[Any],
    errors: list[str],
) -> None:
    from specfact_project.sync_runtime.bridge_sync import SyncOperation
    from specfact_project.sync_runtime.bridge_sync_backlog_helpers import (
        build_backlog_entry_from_result,
        upsert_backlog_entry_list,
    )

    target_entry = _ebb_resolve_target_entry(bridge, proposal, entries, adapter_type, target_repo)
    proposal_dict: dict[str, Any] = {
        "change_id": proposal.name,
        "title": proposal.title,
        "description": proposal.description,
        "rationale": proposal.rationale,
        "status": proposal.status,
        "source_tracking": entries,
    }
    state_pair = _ebb_collect_source_state(entries, adapter_type)
    if state_pair:
        proposal_dict["source_state"] = state_pair[0]
        proposal_dict["source_type"] = state_pair[1]
    _ebb_apply_raw_metadata(proposal, proposal_dict)
    try:
        if target_entry and target_entry.get("source_id"):
            last_synced = target_entry.get("source_metadata", {}).get("last_synced_status")
            if last_synced != proposal.status:
                adapter.export_artifact("change_status", proposal_dict, bridge_config)
                operations.append(
                    SyncOperation(
                        artifact_key="change_status",
                        feature_id=proposal.name,
                        direction="export",
                        bundle_name=bundle_name,
                    )
                )
                target_entry.setdefault("source_metadata", {})["last_synced_status"] = proposal.status
            if update_existing:
                export_result = adapter.export_artifact("change_proposal_update", proposal_dict, bridge_config)
                operations.append(
                    SyncOperation(
                        artifact_key="change_proposal_update",
                        feature_id=proposal.name,
                        direction="export",
                        bundle_name=bundle_name,
                    )
                )
            else:
                export_result = {}
        else:
            export_result = adapter.export_artifact("change_proposal", proposal_dict, bridge_config)
            operations.append(
                SyncOperation(
                    artifact_key="change_proposal",
                    feature_id=proposal.name,
                    direction="export",
                    bundle_name=bundle_name,
                )
            )
        if isinstance(export_result, dict):
            entry_update = build_backlog_entry_from_result(
                adapter_type,
                target_repo,
                export_result,
                proposal.status,
            )
            if entry_update:
                new_entries = upsert_backlog_entry_list(entries, entry_update)
                proposal.source_tracking.source_metadata["backlog_entries"] = new_entries
    except Exception as e:
        errors.append(f"Failed to export '{proposal.name}' to {adapter_type}: {e}")


def run_export_backlog_from_bundle(
    bridge: Any,
    adapter_type: str,
    bundle_name: str,
    adapter_kwargs: dict[str, Any] | None,
    update_existing: bool,
    change_ids: list[str] | None,
) -> Any:
    from specfact_cli.models.source_tracking import SourceTracking

    from specfact_project.sync_runtime.bridge_sync import SyncOperation, SyncResult

    operations: list[SyncOperation] = []
    errors: list[str] = []
    warnings: list[str] = []
    adapter_kwargs = adapter_kwargs or {}
    adapter = AdapterRegistry.get_adapter(adapter_type, **adapter_kwargs)
    bridge_config = adapter.generate_bridge_config(bridge.repo_path)
    bundle_dir = SpecFactStructure.project_dir(base_path=bridge.repo_path, bundle_name=bundle_name)
    if not bundle_dir.exists():
        errors.append(f"Project bundle not found: {bundle_dir}")
        return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)
    project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)
    change_tracking = project_bundle.change_tracking or project_bundle.manifest.change_tracking
    if not change_tracking or not change_tracking.proposals:
        warnings.append(f"No change proposals found in bundle '{bundle_name}'")
        return SyncResult(success=True, operations=operations, errors=errors, warnings=warnings)
    target_repo = _ebb_resolve_target_repo(adapter, adapter_type)
    for proposal in change_tracking.proposals.values():
        if change_ids and proposal.name not in change_ids:
            continue
        if proposal.source_tracking is None:
            proposal.source_tracking = SourceTracking(tool=adapter_type, source_metadata={})
        entries = get_backlog_entries_list(proposal)
        if isinstance(proposal.source_tracking.source_metadata, dict):
            proposal.source_tracking.source_metadata["backlog_entries"] = entries
        _ebb_export_one_proposal(
            bridge,
            proposal,
            adapter,
            bridge_config,
            adapter_type,
            bundle_name,
            target_repo,
            update_existing,
            entries,
            operations,
            errors,
        )
    if operations:
        save_project_bundle(project_bundle, bundle_dir, atomic=True)
    return SyncResult(
        success=len(errors) == 0,
        operations=operations,
        errors=errors,
        warnings=warnings,
    )
