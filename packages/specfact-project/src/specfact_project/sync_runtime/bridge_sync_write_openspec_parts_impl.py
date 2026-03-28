"""Helpers for writing OpenSpec change files from a proposal (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specfact_cli.runtime import get_configured_console


console = get_configured_console()
_ST_CAP = {"github": "GitHub", "ado": "ADO", "linear": "Linear", "jira": "Jira", "unknown": "Unknown"}


def woc_resolve_change_id(bridge: Any, proposal: Any) -> str:
    change_id = proposal.name
    if change_id == "unknown" or not change_id:
        title_clean = bridge._format_proposal_title(proposal.title)
        change_id = re.sub(r"[^a-z0-9]+", "-", title_clean.lower()).strip("-")
        if not change_id:
            change_id = "imported-change"
    return change_id


def woc_resolve_change_directory(openspec_changes_dir: Path, change_id: str) -> tuple[str, Path]:
    change_dir = openspec_changes_dir / change_id
    if change_dir.exists() and change_dir.is_dir() and (change_dir / "proposal.md").exists():
        return change_id, change_dir
    counter = 1
    original_change_id = change_id
    while change_dir.exists() and change_dir.is_dir():
        change_id = f"{original_change_id}-{counter}"
        change_dir = openspec_changes_dir / change_id
        counter += 1
    return change_id, change_dir


def woc_apply_refinement_metadata(proposal: Any, template_id: str | None, refinement_confidence: float | None) -> None:
    if not proposal.source_tracking or (template_id is None and refinement_confidence is None):
        return
    if template_id is not None:
        proposal.source_tracking.template_id = template_id
    if refinement_confidence is not None:
        proposal.source_tracking.refinement_confidence = refinement_confidence
        proposal.source_tracking.refinement_timestamp = datetime.now(UTC)


def _woc_append_backlog_entry_lines(proposal_lines: list[str], entry: dict[str, Any], proposal_status: str) -> None:
    source_repo = entry.get("source_repo", "")
    source_id = entry.get("source_id", "")
    source_url = entry.get("source_url", "")
    source_type = entry.get("source_type", "unknown")
    if source_repo:
        proposal_lines.append(f"<!-- source_repo: {source_repo} -->")
    display = _ST_CAP.get(source_type.lower(), "Unknown")
    if source_id:
        proposal_lines.append(f"- **{display} Issue**: #{source_id}")
    if source_url:
        proposal_lines.append(f"- **Issue URL**: <{source_url}>")
    proposal_lines.append(f"- **Last Synced Status**: {proposal_status}")
    proposal_lines.append("")


def _woc_append_refinement_lines(proposal_lines: list[str], st: Any) -> None:
    if st.template_id:
        proposal_lines.append(f"- **Template ID**: {st.template_id}")
    if st.refinement_confidence is not None:
        proposal_lines.append(f"- **Refinement Confidence**: {st.refinement_confidence:.2f}")
    if st.refinement_timestamp:
        proposal_lines.append(f"- **Refinement Timestamp**: {st.refinement_timestamp.isoformat()}")
    if st.refinement_ai_model:
        proposal_lines.append(f"- **Refinement AI Model**: {st.refinement_ai_model}")
    if st.template_id or st.refinement_confidence is not None:
        proposal_lines.append("")


def woc_append_source_tracking_section(proposal_lines: list[str], proposal: Any) -> None:
    if not proposal.source_tracking:
        return
    proposal_lines.extend(["---", "", "## Source Tracking", ""])
    st = proposal.source_tracking
    _woc_append_refinement_lines(proposal_lines, st)
    source_metadata = st.source_metadata if st.source_metadata else {}
    if not isinstance(source_metadata, dict):
        return
    backlog_entries = source_metadata.get("backlog_entries", [])
    if not backlog_entries:
        return
    for entry in backlog_entries:
        if isinstance(entry, dict):
            _woc_append_backlog_entry_lines(proposal_lines, entry, proposal.status)


def woc_build_proposal_body_lines(bridge: Any, proposal: Any) -> tuple[list[str], list[str]]:
    proposal_lines: list[str] = []
    proposal_lines.append(f"# Change: {bridge._format_proposal_title(proposal.title)}")
    proposal_lines.extend(["", "## Why", "", proposal.rationale or "No rationale provided.", "", "## What Changes", ""])
    description = proposal.description or "No description provided."
    what_changes_content = bridge._extract_what_changes_content(description)
    formatted_description = bridge._format_what_changes_section(what_changes_content)
    proposal_lines.extend([formatted_description, ""])
    affected_specs = bridge._determine_affected_specs(proposal)
    proposal_lines.extend(
        [
            "## Impact",
            "",
            f"- **Affected specs**: {', '.join(f'`{s}`' for s in affected_specs)}",
            "- **Affected code**: See implementation tasks",
            "- **Integration points**: See spec deltas",
            "",
        ]
    )
    dependencies_section = bridge._extract_dependencies_section(proposal.description or "")
    if dependencies_section:
        proposal_lines.extend(["---", "", "## Dependencies", "", dependencies_section, ""])
    return proposal_lines, affected_specs


def woc_guess_spec_change_type(description_lower: str) -> str:
    has_new = any(k in description_lower for k in ["new", "add", "introduce", "create", "implement"])
    has_mod = any(k in description_lower for k in ["extend", "modify", "update", "fix", "improve"])
    if has_new and not has_mod:
        return "ADDED"
    return "MODIFIED"


def woc_build_spec_lines(bridge: Any, proposal: Any, spec_id: str) -> list[str]:
    spec_lines = [
        f"# {spec_id} Specification",
        "",
        "## Purpose",
        "",
        "TBD - created by importing backlog item",
        "",
        "## Requirements",
        "",
    ]
    requirement_text = bridge._extract_requirement_from_proposal(proposal, spec_id)
    desc_lower = (proposal.description or "").lower()
    if requirement_text:
        change_type = woc_guess_spec_change_type(desc_lower)
        spec_lines.extend([f"## {change_type} Requirements", "", requirement_text])
    else:
        spec_lines.extend(
            [
                "## MODIFIED Requirements",
                "",
                "### Requirement: [Requirement name from proposal]",
                "",
                "The system SHALL [requirement description]",
                "",
                "#### Scenario: [Scenario name]",
                "",
                "- **WHEN** [condition]",
                "- **THEN** [expected result]",
                "",
            ]
        )
    return spec_lines


def woc_warn_openspec_missing(warnings: list[str]) -> None:
    logger = logging.getLogger(__name__)
    warning = "OpenSpec changes directory not found. Skipping file creation."
    warnings.append(warning)
    logger.warning(warning)
    console.print(f"[yellow]⚠[/yellow] {warning}")


def woc_write_tasks_md(
    bridge: Any,
    proposal: Any,
    change_dir: Path,
    change_id: str,
    warnings: list[str],
) -> None:
    logger = logging.getLogger(__name__)
    tasks_file = change_dir / "tasks.md"
    if tasks_file.exists():
        warning = f"tasks.md already exists for change '{change_id}', leaving it untouched."
        warnings.append(warning)
        logger.info(warning)
        return
    tasks_content = bridge._generate_tasks_from_proposal(proposal)
    tasks_file.write_text(tasks_content, encoding="utf-8")
    logger.info("Created tasks.md: %s", tasks_file)


def woc_write_spec_deltas(
    bridge: Any,
    proposal: Any,
    change_dir: Path,
    change_id: str,
    affected_specs: list[str],
    warnings: list[str],
) -> None:
    logger = logging.getLogger(__name__)
    specs_dir = change_dir / "specs"
    specs_dir.mkdir(exist_ok=True)
    for spec_id in affected_specs:
        spec_dir = specs_dir / spec_id
        spec_dir.mkdir(exist_ok=True)
        spec_lines = woc_build_spec_lines(bridge, proposal, spec_id)
        spec_file = spec_dir / "spec.md"
        if spec_file.exists():
            warning = f"Spec delta already exists for change '{change_id}' ({spec_id}), leaving it untouched."
            warnings.append(warning)
            logger.info(warning)
        else:
            spec_file.write_text("\n".join(spec_lines), encoding="utf-8")
            logger.info("Created spec delta: %s", spec_file)
