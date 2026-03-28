"""Read OpenSpec change proposals from disk (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from specfact_project.sync_runtime.bridge_sync_openspec_proposal_parse import ProposalSectionParser


def _resolve_openspec_changes_dir(bridge: Any) -> Path | None:
    openspec_dir = bridge.repo_path / "openspec" / "changes"
    if openspec_dir.exists() and openspec_dir.is_dir():
        return openspec_dir
    if bridge.bridge_config and hasattr(bridge.bridge_config, "external_base_path"):
        external_path = getattr(bridge.bridge_config, "external_base_path", None)
        if external_path:
            ext_changes = Path(external_path) / "openspec" / "changes"
            if ext_changes.exists():
                return ext_changes
    return None


def _maybe_enrich_entry_source_repo(entry: dict[str, Any]) -> None:
    if entry.get("source_repo"):
        return
    source_url = entry.get("source_url", "")
    if not source_url:
        return
    url_repo_match = re.search(r"github\.com/([^/]+/[^/]+)/", source_url)
    if url_repo_match:
        entry["source_repo"] = url_repo_match.group(1)
        return
    try:
        parsed = urlparse(source_url)
        if parsed.hostname and parsed.hostname.lower() == "dev.azure.com":
            pass
    except Exception:
        pass


def parse_source_tracking_entries(
    proposal_content: str,
    bridge: Any,
    *,
    enrich_single_entry_repo: bool,
) -> list[dict[str, Any]]:
    source_tracking_list: list[dict[str, Any]] = []
    if "## Source Tracking" not in proposal_content:
        return source_tracking_list
    source_tracking_match = re.search(r"## Source Tracking\s*\n(.*?)(?=\n## |\Z)", proposal_content, re.DOTALL)
    if not source_tracking_match:
        return source_tracking_list
    tracking_content = source_tracking_match.group(1)
    repo_sections = re.split(r"###\s+Repository:\s*([^\n]+)\s*\n", tracking_content)
    if len(repo_sections) > 1:
        for i in range(1, len(repo_sections), 2):
            if i + 1 >= len(repo_sections):
                continue
            repo_name = repo_sections[i].strip()
            entry_content = repo_sections[i + 1]
            entry = bridge._parse_source_tracking_entry(entry_content, repo_name)
            if entry:
                source_tracking_list.append(entry)
        return source_tracking_list
    entry = bridge._parse_source_tracking_entry(tracking_content, None)
    if not entry:
        return source_tracking_list
    if enrich_single_entry_repo:
        _maybe_enrich_entry_source_repo(entry)
    source_tracking_list.append(entry)
    return source_tracking_list


def _finalize_source_tracking(source_tracking_list: list[dict[str, Any]]) -> list[dict[str, Any]] | dict[str, Any]:
    if not source_tracking_list:
        return {}
    if len(source_tracking_list) == 1:
        return source_tracking_list[0]
    return source_tracking_list


def _parse_active_change_dir(bridge: Any, change_dir: Path, proposals: list[dict[str, Any]]) -> None:
    proposal_file = change_dir / "proposal.md"
    if not proposal_file.exists():
        return
    try:
        proposal_content = proposal_file.read_text(encoding="utf-8")
        lines = proposal_content.split("\n")
        parser = ProposalSectionParser(lines)
        parser.parse()
        st = parser.st
        status = "proposed"
        source_tracking_list = parse_source_tracking_entries(proposal_content, bridge, enrich_single_entry_repo=True)
        description_clean = bridge._dedupe_duplicate_sections(st.description.strip()) if st.description else ""
        impact_clean = st.impact.strip() if st.impact else ""
        rationale_clean = st.rationale.strip() if st.rationale else ""
        proposal = {
            "change_id": change_dir.name,
            "title": st.title or change_dir.name,
            "description": description_clean or "No description provided.",
            "rationale": rationale_clean or "No rationale provided.",
            "impact": impact_clean,
            "status": status,
            "source_tracking": _finalize_source_tracking(source_tracking_list),
        }
        proposals.append(proposal)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to parse proposal from %s: %s", proposal_file, e)


def _archive_change_id(archive_subdir: Path) -> str:
    archive_name = archive_subdir.name
    if "-" in archive_name:
        parts = archive_name.split("-", 3)
        return parts[3] if len(parts) >= 4 else archive_subdir.name
    return archive_subdir.name


def _parse_archived_change_dir(bridge: Any, archive_subdir: Path, proposals: list[dict[str, Any]]) -> None:
    proposal_file = archive_subdir / "proposal.md"
    if not proposal_file.exists():
        return
    try:
        proposal_content = proposal_file.read_text(encoding="utf-8")
        lines = proposal_content.split("\n")
        parser = ProposalSectionParser(lines)
        parser.parse()
        st = parser.st
        status = "applied"
        change_id = _archive_change_id(archive_subdir)
        source_tracking_list = parse_source_tracking_entries(proposal_content, bridge, enrich_single_entry_repo=False)
        description_clean = bridge._dedupe_duplicate_sections(st.description.strip()) if st.description else ""
        impact_clean = st.impact.strip() if st.impact else ""
        rationale_clean = st.rationale.strip() if st.rationale else ""
        proposal = {
            "change_id": change_id,
            "title": st.title or change_id,
            "description": description_clean or "No description provided.",
            "rationale": rationale_clean or "No rationale provided.",
            "impact": impact_clean,
            "status": status,
            "source_tracking": _finalize_source_tracking(source_tracking_list),
        }
        proposals.append(proposal)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to parse archived proposal from %s: %s", proposal_file, e)


def read_openspec_change_proposals(bridge: Any, include_archived: bool = True) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    openspec_changes_dir = _resolve_openspec_changes_dir(bridge)
    if not openspec_changes_dir or not openspec_changes_dir.exists():
        return proposals
    for change_dir in openspec_changes_dir.iterdir():
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        _parse_active_change_dir(bridge, change_dir, proposals)
    if not include_archived:
        return proposals
    archive_dir = openspec_changes_dir / "archive"
    if not archive_dir.exists() or not archive_dir.is_dir():
        return proposals
    for archive_subdir in archive_dir.iterdir():
        if not archive_subdir.is_dir():
            continue
        _parse_archived_change_dir(bridge, archive_subdir, proposals)
    return proposals
