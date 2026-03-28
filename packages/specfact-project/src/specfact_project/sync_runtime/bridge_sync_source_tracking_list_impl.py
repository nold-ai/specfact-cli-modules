"""Update source_tracking list entries (cyclomatic complexity reduction)."""

from __future__ import annotations

from typing import Any


def _usl_ado_orgs_match(entry_repo: str, target_repo: str) -> tuple[str | None, str | None] | None:
    entry_org = entry_repo.split("/")[0] if "/" in entry_repo else None
    target_org = target_repo.split("/")[0] if "/" in target_repo else None
    if not entry_org or not target_org or entry_org != target_org:
        return None
    return entry_org, target_org


def _usl_try_ado_merge(
    i: int,
    source_tracking_list: list[dict[str, Any]],
    entry: dict[str, Any],
    entry_data: dict[str, Any],
    target_repo: str,
    entry_type: str,
    entry_type_existing: str,
    entry_repo: str | None,
    new_source_id: Any,
) -> bool:
    if entry_type != "ado" or entry_type_existing != "ado" or not entry_repo or not target_repo:
        return False
    if _usl_ado_orgs_match(entry_repo, target_repo) is None:
        return False
    entry_source_id = entry.get("source_id")
    if entry_source_id and new_source_id and entry_source_id == new_source_id:
        source_tracking_list[i] = {**entry, **entry_data}
        return True
    updated_entry = {**entry, **entry_data}
    updated_entry["source_repo"] = target_repo
    source_tracking_list[i] = updated_entry
    return True


def run_update_source_tracking_entry(
    bridge: Any,
    source_tracking_list: list[dict[str, Any]],
    target_repo: str,
    entry_data: dict[str, Any],
) -> list[dict[str, Any]]:
    _ = bridge
    if "source_repo" not in entry_data:
        entry_data["source_repo"] = target_repo
    entry_type = entry_data.get("source_type", "").lower()
    new_source_id = entry_data.get("source_id")
    for i, entry in enumerate(source_tracking_list):
        if not isinstance(entry, dict):
            continue
        entry_repo = entry.get("source_repo")
        entry_type_existing = entry.get("source_type", "").lower()
        if entry_repo == target_repo:
            source_tracking_list[i] = {**entry, **entry_data}
            return source_tracking_list
        if _usl_try_ado_merge(
            i,
            source_tracking_list,
            entry,
            entry_data,
            target_repo,
            entry_type,
            entry_type_existing,
            entry_repo,
            new_source_id,
        ):
            return source_tracking_list
    source_tracking_list.append(entry_data)
    return source_tracking_list
