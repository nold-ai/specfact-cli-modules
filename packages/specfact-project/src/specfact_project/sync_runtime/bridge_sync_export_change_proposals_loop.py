"""Inner loop for export change proposals (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import logging
from typing import Any

from specfact_project.sync_runtime.bridge_sync_export_one_proposal import ecd_export_one_change_proposal


def ecd_iterate_active_proposals(
    bridge: Any,
    active_proposals: list[dict[str, Any]],
    adapter: Any,
    adapter_type: str,
    target_repo: str | None,
    repo_owner: str | None,
    repo_name: str | None,
    ado_org: str | None,
    ado_project: str | None,
    update_existing: bool,
    import_from_tmp: bool,
    tmp_file,
    export_to_tmp: bool,
    should_sanitize: Any,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo_path,
    sanitizer: Any,
    operations,
    errors: list[str],
    warnings: list[str],
) -> None:
    for proposal in active_proposals:
        try:
            ecd_export_one_change_proposal(
                bridge,
                proposal,
                adapter,
                adapter_type,
                target_repo,
                repo_owner,
                repo_name,
                ado_org,
                ado_project,
                update_existing,
                import_from_tmp,
                tmp_file,
                export_to_tmp,
                should_sanitize,
                track_code_changes,
                add_progress_comment,
                code_repo_path,
                sanitizer,
                operations,
                errors,
                warnings,
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.debug(
                "Failed to sync proposal %s: %s",
                proposal.get("change_id", "unknown"),
                e,
                exc_info=True,
            )
            errors.append(f"Failed to sync proposal {proposal.get('change_id', 'unknown')}: {e}")
