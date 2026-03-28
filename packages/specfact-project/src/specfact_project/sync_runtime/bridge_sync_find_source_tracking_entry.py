"""Find source tracking entry for a target repository (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def _fst_ado_tertiary_project_unknown(
    entry_repo: str,
    target_repo: str,
    source_url: str,
) -> bool:
    entry_project = entry_repo.split("/", 1)[1] if "/" in entry_repo else None
    target_project = target_repo.split("/", 1)[1] if "/" in target_repo else None
    entry_has_guid = source_url and re.search(r"dev\.azure\.com/[^/]+/[0-9a-f-]{36}", source_url, re.IGNORECASE)
    return bool(
        not entry_project
        or not target_project
        or entry_has_guid
        or (entry_project and len(entry_project) == 36 and "-" in entry_project)
        or (target_project and len(target_project) == 36 and "-" in target_project)
    )


def _fst_dict_try_source_urls(
    source_tracking: dict[str, Any], target_repo: str, entry_type: str
) -> dict[str, Any] | None:
    source_url = source_tracking.get("source_url", "")
    if not source_url:
        return None
    url_repo_match = re.search(r"github\.com/([^/]+/[^/]+)/", source_url)
    if url_repo_match and url_repo_match.group(1) == target_repo:
        return source_tracking
    if "/" not in target_repo:
        return None
    try:
        parsed = urlparse(source_url)
        if not parsed.hostname or parsed.hostname.lower() != "dev.azure.com":
            return None
        target_org = target_repo.split("/")[0]
        ado_org_match = re.search(r"dev\.azure\.com/([^/]+)/", source_url)
        if ado_org_match and ado_org_match.group(1) == target_org and (entry_type == "ado" or entry_type == ""):
            return source_tracking
    except Exception:
        return None
    return None


def _fst_dict_try_ado_tertiary(
    source_tracking: dict[str, Any], target_repo: str, entry_type: str, entry_repo: str
) -> dict[str, Any] | None:
    if not (entry_repo and target_repo and entry_type == "ado"):
        return None
    entry_org = entry_repo.split("/")[0] if "/" in entry_repo else None
    target_org = target_repo.split("/")[0] if "/" in target_repo else None
    source_url2 = source_tracking.get("source_url", "")
    project_unknown = _fst_ado_tertiary_project_unknown(entry_repo, target_repo, source_url2)
    if entry_org and target_org and entry_org == target_org and source_tracking.get("source_id") and project_unknown:
        return source_tracking
    return None


def _fst_match_single_dict(source_tracking: dict[str, Any], target_repo: str | None) -> dict[str, Any] | None:
    entry_type = source_tracking.get("source_type", "").lower()
    entry_repo = source_tracking.get("source_repo")
    if entry_repo == target_repo:
        return source_tracking
    if target_repo:
        matched = _fst_dict_try_source_urls(source_tracking, target_repo, entry_type)
        if matched is not None:
            return matched
        if entry_repo:
            matched2 = _fst_dict_try_ado_tertiary(source_tracking, target_repo, entry_type, entry_repo)
            if matched2 is not None:
                return matched2
    if not target_repo:
        return source_tracking
    return None


def _fst_list_try_secondary_urls(entry: dict[str, Any], target_repo: str, entry_type: str) -> dict[str, Any] | None:
    source_url = entry.get("source_url", "")
    if not source_url:
        return None
    url_repo_match = re.search(r"github\.com/([^/]+/[^/]+)/", source_url)
    if url_repo_match and url_repo_match.group(1) == target_repo:
        return entry
    if "/" not in target_repo:
        return None
    try:
        parsed = urlparse(source_url)
        if not parsed.hostname or parsed.hostname.lower() != "dev.azure.com":
            return None
        target_org = target_repo.split("/")[0]
        ado_org_match = re.search(r"dev\.azure\.com/([^/]+)/", source_url)
        if ado_org_match and ado_org_match.group(1) == target_org and (entry_type == "ado" or entry_type == ""):
            return entry
    except Exception:
        return None
    return None


def _fst_list_try_ado_tertiary(
    entry: dict[str, Any], target_repo: str, entry_type: str, entry_repo: str
) -> dict[str, Any] | None:
    if not (entry_repo and target_repo and entry_type == "ado"):
        return None
    entry_org = entry_repo.split("/")[0] if "/" in entry_repo else None
    target_org = target_repo.split("/")[0] if "/" in target_repo else None
    source_url = entry.get("source_url", "")
    project_unknown = _fst_ado_tertiary_project_unknown(entry_repo, target_repo, source_url)
    if entry_org and target_org and entry_org == target_org and entry.get("source_id") and project_unknown:
        return entry
    return None


def _fst_match_one_list_entry(entry: dict[str, Any], target_repo: str | None) -> dict[str, Any] | None:
    entry_repo = entry.get("source_repo")
    entry_type = entry.get("source_type", "").lower()
    if entry_repo == target_repo:
        return entry
    if not entry_repo and target_repo:
        matched = _fst_list_try_secondary_urls(entry, target_repo, entry_type)
        if matched is not None:
            return matched
    if entry_repo and target_repo:
        matched2 = _fst_list_try_ado_tertiary(entry, target_repo, entry_type, entry_repo)
        if matched2 is not None:
            return matched2
    return None


def _fst_match_entry_list(source_tracking: list[dict[str, Any]], target_repo: str | None) -> dict[str, Any] | None:
    for entry in source_tracking:
        if not isinstance(entry, dict):
            continue
        matched = _fst_match_one_list_entry(entry, target_repo)
        if matched is not None:
            return matched
    return None


def find_source_tracking_entry(
    source_tracking: list[dict[str, Any]] | dict[str, Any] | None, target_repo: str | None
) -> dict[str, Any] | None:
    if not source_tracking:
        return None
    if isinstance(source_tracking, dict):
        return _fst_match_single_dict(source_tracking, target_repo)
    if isinstance(source_tracking, list):
        return _fst_match_entry_list(source_tracking, target_repo)
    return None
