"""Backlog entry helpers extracted from BridgeSync (cyclomatic complexity reduction)."""

from __future__ import annotations

from typing import Any


def build_backlog_entry_from_result(
    adapter_type: str,
    target_repo: str | None,
    export_result: dict[str, Any],
    status: str,
) -> dict[str, Any] | None:
    if adapter_type == "github":
        source_id = export_result.get("issue_number")
        source_url = export_result.get("issue_url")
    elif adapter_type == "ado":
        source_id = export_result.get("work_item_id")
        source_url = export_result.get("work_item_url")
    else:
        return None
    if source_id is None:
        return None
    return {
        "source_id": str(source_id),
        "source_url": source_url or "",
        "source_type": adapter_type,
        "source_repo": target_repo or "",
        "source_metadata": {"last_synced_status": status},
    }


def get_backlog_entries_list(proposal: Any) -> list[dict[str, Any]]:
    if not hasattr(proposal, "source_tracking") or not proposal.source_tracking:
        return []
    source_metadata = proposal.source_tracking.source_metadata
    if not isinstance(source_metadata, dict):
        return []
    entries = source_metadata.get("backlog_entries")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    return _backlog_entries_from_fallback_metadata(proposal, source_metadata)


def _backlog_entries_from_fallback_metadata(proposal: Any, source_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    fallback_id = source_metadata.get("source_id")
    fallback_url = source_metadata.get("source_url")
    fallback_repo = source_metadata.get("source_repo", "")
    fallback_type = source_metadata.get("source_type") or getattr(proposal.source_tracking, "tool", None)
    if not fallback_id and not fallback_url:
        return []
    return [
        {
            "source_id": str(fallback_id) if fallback_id is not None else None,
            "source_url": fallback_url or "",
            "source_type": fallback_type or "",
            "source_repo": fallback_repo,
            "source_metadata": {},
        }
    ]


def upsert_backlog_entry_list(entries: list[dict[str, Any]], new_entry: dict[str, Any]) -> list[dict[str, Any]]:
    new_repo = new_entry.get("source_repo")
    new_type = new_entry.get("source_type")
    new_id = new_entry.get("source_id")
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        if new_repo and entry.get("source_repo") == new_repo and entry.get("source_type") == new_type:
            entries[idx] = {**entry, **new_entry}
            return entries
        if new_id and entry.get("source_id") == new_id and entry.get("source_type") == new_type:
            entries[idx] = {**entry, **new_entry}
            return entries
    entries.append(new_entry)
    return entries
