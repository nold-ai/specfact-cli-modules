"""Create / update OpenSpec change files from a backlog proposal."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
from typing import Any

from specfact_cli.runtime import get_configured_console

from specfact_project.sync_runtime.bridge_sync_write_openspec_parts_impl import (
    woc_append_source_tracking_section,
    woc_apply_refinement_metadata,
    woc_build_proposal_body_lines,
    woc_resolve_change_directory,
    woc_resolve_change_id,
    woc_warn_openspec_missing,
    woc_write_spec_deltas,
    woc_write_tasks_md,
)


console = get_configured_console()


def run_write_openspec_change_from_proposal(
    bridge: Any,
    proposal: Any,
    bridge_config: Any,
    template_id: str | None = None,
    refinement_confidence: float | None = None,
) -> list[str]:
    _ = bridge_config
    warnings: list[str] = []
    logger = logging.getLogger(__name__)
    openspec_changes_dir = bridge._get_openspec_changes_dir()
    if not openspec_changes_dir:
        woc_warn_openspec_missing(warnings)
        return warnings
    change_id = woc_resolve_change_id(bridge, proposal)
    change_id, change_dir = woc_resolve_change_directory(openspec_changes_dir, change_id)
    if change_dir.exists() and change_dir.is_dir() and (change_dir / "proposal.md").exists():
        logger.info("Updating existing OpenSpec change: %s", change_id)
    try:
        change_dir.mkdir(parents=True, exist_ok=True)
        proposal_lines, affected_specs = woc_build_proposal_body_lines(bridge, proposal)
        woc_apply_refinement_metadata(proposal, template_id, refinement_confidence)
        woc_append_source_tracking_section(proposal_lines, proposal)
        proposal_file = change_dir / "proposal.md"
        proposal_file.write_text("\n".join(proposal_lines), encoding="utf-8")
        logger.info("Created proposal.md: %s", proposal_file)
        woc_write_tasks_md(bridge, proposal, change_dir, change_id, warnings)
        woc_write_spec_deltas(bridge, proposal, change_dir, change_id, affected_specs, warnings)
        console.print(f"[green]✓[/green] Created OpenSpec change: {change_id} at {change_dir}")
    except Exception as e:
        warning = f"Failed to create OpenSpec files for change '{change_id}': {e}"
        warnings.append(warning)
        logger.warning(warning, exc_info=True)
    return warnings
