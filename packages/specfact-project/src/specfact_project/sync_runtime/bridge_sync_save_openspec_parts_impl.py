"""Piecewise proposal.md updates for OpenSpec (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_SOURCE_TYPE_CAP = {
    "github": "GitHub",
    "ado": "ADO",
    "linear": "Linear",
    "jira": "Jira",
    "unknown": "Unknown",
}


def soscp_find_openspec_changes_dir(bridge: Any) -> Path | None:
    openspec_dir = bridge.repo_path / "openspec" / "changes"
    if openspec_dir.exists() and openspec_dir.is_dir():
        return openspec_dir
    if bridge.bridge_config and hasattr(bridge.bridge_config, "external_base_path"):
        external_path = getattr(bridge.bridge_config, "external_base_path", None)
        if external_path:
            candidate = Path(external_path) / "openspec" / "changes"
            if candidate.exists():
                return candidate
    return None


def soscp_resolve_proposal_file(openspec_changes_dir: Path, change_id: str) -> Path | None:
    proposal_file = openspec_changes_dir / change_id / "proposal.md"
    if proposal_file.exists():
        return proposal_file
    archive_dir = openspec_changes_dir / "archive"
    if not archive_dir.exists() or not archive_dir.is_dir():
        return None
    for archive_subdir in archive_dir.iterdir():
        if not archive_subdir.is_dir():
            continue
        archive_name = archive_subdir.name
        if "-" not in archive_name:
            continue
        parts = archive_name.split("-", 3)
        if len(parts) >= 4 and parts[3] == change_id:
            candidate = archive_subdir / "proposal.md"
            if candidate.exists():
                return candidate
    return None


def _soscp_append_source_metadata_fields(metadata_lines: list[str], source_metadata: dict[str, Any]) -> None:
    last_synced_status = source_metadata.get("last_synced_status")
    if last_synced_status:
        metadata_lines.append(f"- **Last Synced Status**: {last_synced_status}")
    sanitized = source_metadata.get("sanitized")
    if sanitized is not None:
        metadata_lines.append(f"- **Sanitized**: {str(sanitized).lower()}")
    content_hash = source_metadata.get("content_hash")
    if content_hash:
        metadata_lines.append(f"<!-- content_hash: {content_hash} -->")
    progress_comments = source_metadata.get("progress_comments")
    if progress_comments and isinstance(progress_comments, list) and len(progress_comments) > 0:
        pc_json = json.dumps(progress_comments, separators=(",", ":"))
        metadata_lines.append(f"<!-- progress_comments: {pc_json} -->")
    last_code_change_detected = source_metadata.get("last_code_change_detected")
    if last_code_change_detected:
        metadata_lines.append(f"<!-- last_code_change_detected: {last_code_change_detected} -->")


def _soscp_append_entry_metadata(
    metadata_lines: list[str],
    entry: dict[str, Any],
    i: int,
    n_entries: int,
) -> None:
    source_repo = entry.get("source_repo")
    if source_repo:
        if n_entries > 1 or i > 0:
            metadata_lines.append(f"### Repository: {source_repo}")
            metadata_lines.append("")
        elif n_entries == 1:
            metadata_lines.append(f"<!-- source_repo: {source_repo} -->")
    source_type_raw = entry.get("source_type", "unknown")
    display = _SOURCE_TYPE_CAP.get(source_type_raw.lower(), "Unknown")
    source_id = entry.get("source_id")
    source_url = entry.get("source_url")
    if source_id:
        metadata_lines.append(f"- **{display} Issue**: #{source_id}")
    if source_url:
        metadata_lines.append(f"- **Issue URL**: <{source_url}>")
    sm = entry.get("source_metadata", {})
    if isinstance(sm, dict) and sm:
        _soscp_append_source_metadata_fields(metadata_lines, sm)


def soscp_build_metadata_section(source_tracking_list: list[dict[str, Any]]) -> str:
    metadata_lines = ["", "---", "", "## Source Tracking", ""]
    n = len(source_tracking_list)
    for i, entry in enumerate(source_tracking_list):
        if not isinstance(entry, dict):
            continue
        _soscp_append_entry_metadata(metadata_lines, entry, i, n)
        if i < n - 1:
            metadata_lines.extend(["", "---", ""])
    metadata_lines.append("")
    return "\n".join(metadata_lines)


def soscp_apply_title(content: str, title: str | None) -> str:
    if not title:
        return content
    title_pattern = r"^#\s+Change:\s*.*$"
    if re.search(title_pattern, content, re.MULTILINE):
        return re.sub(title_pattern, f"# Change: {title}", content, flags=re.MULTILINE)
    return f"# Change: {title}\n\n{content}"


def soscp_replace_why_body(content: str, rationale_clean: str) -> str:
    why_pattern = r"(##\s+Why\s*\n)(.*?)(?=\n##\s+(?!Why\s)|(?:\n---\s*\n\s*##\s+Source\s+Tracking)|\Z)"
    if re.search(why_pattern, content, re.DOTALL | re.IGNORECASE):
        return re.sub(why_pattern, r"\1\n" + rationale_clean + r"\n", content, flags=re.DOTALL | re.IGNORECASE)
    why_simple = r"(##\s+Why\s*\n)(.*?)(?=\n##\s+|\Z)"
    return re.sub(why_simple, r"\1\n" + rationale_clean + r"\n", content, flags=re.DOTALL | re.IGNORECASE)


def soscp_insert_why_missing(content: str, rationale_clean: str) -> str:
    insert_before = re.search(r"(##\s+(What Changes|Source Tracking))", content, re.IGNORECASE)
    if insert_before:
        pos = insert_before.start()
        return content[:pos] + f"## Why\n\n{rationale_clean}\n\n" + content[pos:]
    if "## Source Tracking" in content:
        return content.replace("## Source Tracking", f"## Why\n\n{rationale_clean}\n\n## Source Tracking")
    return f"{content}\n\n## Why\n\n{rationale_clean}\n"


def soscp_apply_rationale(content: str, rationale: str) -> str:
    if not rationale:
        return content
    rationale_clean = rationale.strip()
    if "## Why" in content:
        return soscp_replace_why_body(content, rationale_clean)
    return soscp_insert_why_missing(content, rationale_clean)


def soscp_replace_what_body(content: str, description_clean: str) -> str:
    what_pattern = r"(##\s+What\s+Changes\s*\n)(.*?)(?=(?:\n---\s*\n\s*##\s+Source\s+Tracking)|\Z)"
    if re.search(what_pattern, content, re.DOTALL | re.IGNORECASE):
        return re.sub(
            what_pattern,
            r"\1\n" + description_clean + r"\n",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )
    what_simple = r"(##\s+What\s+Changes\s*\n)(.*?)(?=(?:\n---\s*\n\s*##\s+Source\s+Tracking)|\Z)"
    return re.sub(
        what_simple,
        r"\1\n" + description_clean + r"\n",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )


def soscp_insert_what_missing(bridge: Any, content: str, description_clean: str) -> str:
    insert_after_why = re.search(r"(##\s+Why\s*\n.*?\n)(?=##\s+|$)", content, re.DOTALL | re.IGNORECASE)
    if insert_after_why:
        pos = insert_after_why.end()
        return content[:pos] + f"## What Changes\n\n{description_clean}\n\n" + content[pos:]
    if "## Source Tracking" in content:
        return content.replace(
            "## Source Tracking",
            f"## What Changes\n\n{description_clean}\n\n## Source Tracking",
        )
    _ = bridge
    return f"{content}\n\n## What Changes\n\n{description_clean}\n"


def soscp_apply_description(bridge: Any, content: str, description: str) -> str:
    if not description:
        return content
    description_clean = bridge._dedupe_duplicate_sections(description.strip())
    if "## What Changes" in content:
        return soscp_replace_what_body(content, description_clean)
    return soscp_insert_what_missing(bridge, content, description_clean)


def soscp_merge_source_tracking_block(content: str, metadata_section: str) -> str:
    if "## Source Tracking" in content:
        pattern_with_sep = r"\n---\n\n## Source Tracking.*?(?=\n## |\Z)"
        if re.search(pattern_with_sep, content, flags=re.DOTALL):
            return re.sub(pattern_with_sep, "\n" + metadata_section.rstrip(), content, flags=re.DOTALL)
        pattern_no_sep = r"\n## Source Tracking.*?(?=\n## |\Z)"
        return re.sub(pattern_no_sep, "\n" + metadata_section.rstrip(), content, flags=re.DOTALL)
    return content.rstrip() + "\n" + metadata_section
