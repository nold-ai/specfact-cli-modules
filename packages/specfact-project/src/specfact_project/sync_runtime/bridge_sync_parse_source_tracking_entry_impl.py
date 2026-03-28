"""Parse source tracking markdown entry (cyclomatic complexity reduction)."""

from __future__ import annotations

import json
import re
from typing import Any


def _pst_meta(entry: dict[str, Any]) -> dict[str, Any]:
    if "source_metadata" not in entry:
        entry["source_metadata"] = {}
    return entry["source_metadata"]


def _pst_apply_issue_ref(entry: dict[str, Any], entry_content: str) -> None:
    issue_match = re.search(
        r"\*\*.*Issue\*\*:\s*((?:#\d+)|(?:AB#\d+)|(?:[A-Z][A-Z0-9]+-\d+))",
        entry_content,
    )
    if not issue_match:
        return
    issue_ref = issue_match.group(1)
    entry["source_id"] = issue_ref.lstrip("#")
    entry["source_ref"] = issue_ref


def _pst_apply_issue_url(entry: dict[str, Any], entry_content: str, repo_name: str | None) -> None:
    url_match = re.search(r"\*\*Issue URL\*\*:\s*<?(https://[^\s>]+)>?", entry_content)
    if not url_match:
        return
    entry["source_url"] = url_match.group(1)
    if repo_name:
        return
    url_repo_match = re.search(r"github\.com/([^/]+/[^/]+)/", entry["source_url"])
    if url_repo_match:
        entry["source_repo"] = url_repo_match.group(1)
        return
    ado_repo_match = re.search(r"dev\.azure\.com/([^/]+)/([^/]+)/", entry["source_url"])
    if ado_repo_match:
        entry["source_repo"] = f"{ado_repo_match.group(1)}/{ado_repo_match.group(2)}"


def _pst_apply_source_type(entry: dict[str, Any], entry_content: str) -> None:
    type_match = re.search(r"\*\*(\w+)\s+Issue\*\*:", entry_content)
    if type_match:
        entry["source_type"] = type_match.group(1).lower()


def _pst_apply_last_synced(entry: dict[str, Any], entry_content: str) -> None:
    status_match = re.search(r"\*\*Last Synced Status\*\*:\s*(\w+)", entry_content)
    if status_match:
        _pst_meta(entry)["last_synced_status"] = status_match.group(1)


def _pst_apply_sanitized(entry: dict[str, Any], entry_content: str) -> None:
    sanitized_match = re.search(r"\*\*Sanitized\*\*:\s*(true|false)", entry_content, re.IGNORECASE)
    if sanitized_match:
        _pst_meta(entry)["sanitized"] = sanitized_match.group(1).lower() == "true"


def _pst_apply_content_hash(entry: dict[str, Any], entry_content: str) -> None:
    hash_match = re.search(r"<!--\s*content_hash:\s*([a-f0-9]{16})\s*-->", entry_content)
    if hash_match:
        _pst_meta(entry)["content_hash"] = hash_match.group(1)


def _pst_apply_progress_comments(entry: dict[str, Any], entry_content: str) -> None:
    progress_comments_match = re.search(r"<!--\s*progress_comments:\s*(\[.*?\])\s*-->", entry_content, re.DOTALL)
    if not progress_comments_match:
        return
    try:
        progress_comments = json.loads(progress_comments_match.group(1))
        _pst_meta(entry)["progress_comments"] = progress_comments
    except (json.JSONDecodeError, ValueError):
        # Malformed progress_comments are ignored; they are optional metadata.
        pass


def _pst_apply_last_detection(entry: dict[str, Any], entry_content: str) -> None:
    last_detection_match = re.search(r"<!--\s*last_code_change_detected:\s*([^\s]+)\s*-->", entry_content)
    if last_detection_match:
        _pst_meta(entry)["last_code_change_detected"] = last_detection_match.group(1)


def _pst_apply_source_repo_comment(entry: dict[str, Any], entry_content: str) -> None:
    source_repo_match = re.search(r"<!--\s*source_repo:\s*([^>]+?)\s*-->", entry_content)
    if source_repo_match:
        entry["source_repo"] = source_repo_match.group(1).strip()
        return
    if entry.get("source_repo"):
        return
    source_repo_in_content = re.search(
        r"^\s*source_repo\s*:\s*([^\n]+)",
        entry_content,
        re.IGNORECASE | re.MULTILINE,
    )
    if source_repo_in_content:
        entry["source_repo"] = source_repo_in_content.group(1).strip()


def run_parse_source_tracking_entry(bridge: Any, entry_content: str, repo_name: str | None) -> dict[str, Any] | None:
    _ = bridge
    entry: dict[str, Any] = {}
    if repo_name:
        entry["source_repo"] = repo_name
    _pst_apply_issue_ref(entry, entry_content)
    _pst_apply_issue_url(entry, entry_content, repo_name)
    _pst_apply_source_type(entry, entry_content)
    _pst_apply_last_synced(entry, entry_content)
    _pst_apply_sanitized(entry, entry_content)
    _pst_apply_content_hash(entry, entry_content)
    _pst_apply_progress_comments(entry, entry_content)
    _pst_apply_last_detection(entry, entry_content)
    _pst_apply_source_repo_comment(entry, entry_content)
    if entry.get("source_id") or entry.get("source_url"):
        return entry
    return None
