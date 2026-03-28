"""Persist change proposal back to OpenSpec proposal.md."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
from typing import Any

from specfact_project.sync_runtime.bridge_sync_save_openspec_parts_impl import (
    soscp_apply_description,
    soscp_apply_rationale,
    soscp_apply_title,
    soscp_build_metadata_section,
    soscp_find_openspec_changes_dir,
    soscp_merge_source_tracking_block,
    soscp_resolve_proposal_file,
)


logger = logging.getLogger(__name__)


def run_save_openspec_change_proposal(bridge: Any, proposal: dict[str, Any]) -> None:
    change_id = proposal.get("change_id")
    if not change_id:
        return
    openspec_changes_dir = soscp_find_openspec_changes_dir(bridge)
    if not openspec_changes_dir:
        return
    proposal_file = soscp_resolve_proposal_file(openspec_changes_dir, change_id)
    if not proposal_file or not proposal_file.exists():
        return
    try:
        content = proposal_file.read_text(encoding="utf-8")
        source_tracking_raw = proposal.get("source_tracking", {})
        source_tracking_list = bridge._normalize_source_tracking(source_tracking_raw)
        if not source_tracking_list:
            return
        metadata_section = soscp_build_metadata_section(source_tracking_list)
        content = soscp_apply_title(content, proposal.get("title"))
        content = soscp_apply_rationale(content, proposal.get("rationale", ""))
        content = soscp_apply_description(bridge, content, proposal.get("description", ""))
        content = soscp_merge_source_tracking_block(content, metadata_section)
        proposal_file.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to save source tracking to %s: %s", proposal_file, e)
