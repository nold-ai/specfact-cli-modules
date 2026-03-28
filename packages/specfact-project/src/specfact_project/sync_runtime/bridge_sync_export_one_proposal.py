"""Single change proposal export step (cyclomatic complexity extraction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from specfact_project.sync_runtime.bridge_sync import SyncOperation


class EcdOneProposalExport:
    """Per-proposal export orchestration (keeps cyclomatic complexity low per method)."""

    def __init__(
        self,
        bridge: Any,
        proposal: dict[str, Any],
        adapter: Any,
        adapter_type: str,
        target_repo: str | None,
        repo_owner: str | None,
        repo_name: str | None,
        ado_org: str | None,
        ado_project: str | None,
        update_existing: bool,
        import_from_tmp: bool,
        tmp_file: Path | None,
        export_to_tmp: bool,
        should_sanitize: Any,
        track_code_changes: bool,
        add_progress_comment: bool,
        code_repo_path: Path | None,
        sanitizer: Any,
        operations: list[SyncOperation],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        self.bridge = bridge
        self.proposal = proposal
        self.adapter = adapter
        self.adapter_type = adapter_type
        self.target_repo = target_repo
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.ado_org = ado_org
        self.ado_project = ado_project
        self.update_existing = update_existing
        self.import_from_tmp = import_from_tmp
        self.tmp_file = tmp_file
        self.export_to_tmp = export_to_tmp
        self.should_sanitize = should_sanitize
        self.track_code_changes = track_code_changes
        self.add_progress_comment = add_progress_comment
        self.code_repo_path = code_repo_path
        self.sanitizer = sanitizer
        self.operations = operations
        self.errors = errors
        self.warnings = warnings
        self.source_tracking_raw = proposal.get("source_tracking", {})
        self.target_entry = bridge._find_source_tracking_entry(self.source_tracking_raw, target_repo)
        self.source_tracking_list = bridge._normalize_source_tracking(self.source_tracking_raw)
        self.issue_number = self.target_entry.get("source_id") if self.target_entry else None
        self.work_item_was_deleted = False

    def run(self) -> None:
        self._verify_ado_work_item_if_needed()
        if self._handle_corrupted_entry_without_id():
            return
        if self._update_if_issue_exists():
            return
        change_id = self.proposal.get("change_id", "unknown")
        if self._skip_if_missing_source_id(change_id):
            return
        self._search_github_issue(change_id)
        self._search_ado_work_item(change_id)
        if self._update_if_issue_exists():
            return
        if self._handle_export_to_tmp(change_id):
            return
        proposal_to_export = self._resolve_proposal_to_export(change_id)
        self._export_artifact_and_persist(proposal_to_export)

    def _verify_ado_work_item_if_needed(self) -> None:
        if not (self.issue_number and self.target_entry):
            return
        entry_type = self.target_entry.get("source_type", "").lower()
        if not (
            entry_type == "ado"
            and self.adapter_type.lower() == "ado"
            and self.ado_org
            and self.ado_project
            and hasattr(self.adapter, "_work_item_exists")
        ):
            return
        try:
            work_item_exists = self.adapter._work_item_exists(self.issue_number, self.ado_org, self.ado_project)
            if work_item_exists:
                return
            self.warnings.append(
                f"Work item #{self.issue_number} for '{self.proposal.get('change_id', 'unknown')}' "
                f"no longer exists in ADO (may have been deleted). "
                f"Will create a new work item."
            )
            self.issue_number = None
            self.work_item_was_deleted = True
            self.target_entry = {**self.target_entry, "source_id": None}
        except Exception as e:
            self.warnings.append(
                f"Could not verify work item #{self.issue_number} existence: {e}. Proceeding with sync."
            )

    def _handle_corrupted_entry_without_id(self) -> bool:
        if not (self.target_entry and not self.issue_number and not self.work_item_was_deleted):
            return False
        if self.update_existing:
            if isinstance(self.source_tracking_raw, dict):
                self.proposal["source_tracking"] = {}
                self.target_entry = None
            elif isinstance(self.source_tracking_raw, list):
                self.source_tracking_list = [
                    entry for entry in self.source_tracking_list if entry is not self.target_entry
                ]
                self.proposal["source_tracking"] = self.source_tracking_list
                self.target_entry = None
            return False
        self.warnings.append(
            f"Skipping sync for '{self.proposal.get('change_id', 'unknown')}': "
            f"source_tracking entry exists for '{self.target_repo}' but missing source_id. "
            f"Use --update-existing to force update or manually fix source_tracking."
        )
        return True

    def _call_update_existing_issue(self) -> None:
        self.bridge._update_existing_issue(
            proposal=self.proposal,
            target_entry=self.target_entry,
            issue_number=self.issue_number,
            adapter=self.adapter,
            adapter_type=self.adapter_type,
            target_repo=self.target_repo,
            source_tracking_list=self.source_tracking_list,
            source_tracking_raw=self.source_tracking_raw,
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            ado_org=self.ado_org,
            ado_project=self.ado_project,
            update_existing=self.update_existing,
            import_from_tmp=self.import_from_tmp,
            tmp_file=self.tmp_file,
            should_sanitize=self.should_sanitize,
            track_code_changes=self.track_code_changes,
            add_progress_comment=self.add_progress_comment,
            code_repo_path=self.code_repo_path,
            operations=self.operations,
            errors=self.errors,
            warnings=self.warnings,
        )

    def _update_if_issue_exists(self) -> bool:
        if not (self.issue_number and self.target_entry):
            return False
        self._call_update_existing_issue()
        self.bridge._save_openspec_change_proposal(self.proposal)
        return True

    def _skip_if_missing_source_id(self, change_id: str) -> bool:
        if not (self.target_entry and not self.target_entry.get("source_id") and not self.work_item_was_deleted):
            return False
        self.warnings.append(
            f"Skipping sync for '{change_id}': source_tracking entry exists for "
            f"'{self.target_repo}' but missing source_id. Use --update-existing to force update."
        )
        return True

    def _search_github_issue(self, change_id: str) -> None:
        if self.target_entry or self.adapter_type.lower() != "github" or not self.repo_owner or not self.repo_name:
            return
        found_entry, found_issue_number = self.bridge._search_existing_github_issue(
            change_id, self.repo_owner, self.repo_name, self.target_repo, self.warnings
        )
        if not found_entry or not found_issue_number:
            return
        self.target_entry = found_entry
        self.issue_number = found_issue_number
        self.source_tracking_list.append(self.target_entry)
        self.proposal["source_tracking"] = self.source_tracking_list

    def _search_ado_work_item(self, change_id: str) -> None:
        if (
            self.target_entry
            or self.adapter_type.lower() != "ado"
            or not self.ado_org
            or not self.ado_project
            or not hasattr(self.adapter, "_find_work_item_by_change_id")
        ):
            return
        found_entry = self.adapter._find_work_item_by_change_id(change_id, self.ado_org, self.ado_project)
        if not found_entry:
            return
        self.target_entry = found_entry
        self.issue_number = found_entry.get("source_id")
        self.source_tracking_list.append(found_entry)
        self.proposal["source_tracking"] = self.source_tracking_list

    def _handle_export_to_tmp(self, change_id: str) -> bool:
        if not self.export_to_tmp:
            return False
        tmp_file_path = self.tmp_file or (Path(tempfile.gettempdir()) / f"specfact-proposal-{change_id}.md")
        try:
            proposal_content = self.bridge._format_proposal_for_export(self.proposal)
            tmp_file_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_file_path.write_text(proposal_content, encoding="utf-8")
            self.warnings.append(f"Exported proposal '{change_id}' to {tmp_file_path} for LLM review")
            return True
        except Exception as e:
            self.errors.append(f"Failed to export proposal '{change_id}' to temporary file: {e}")
            return True

    def _resolve_proposal_to_export(self, change_id: str) -> dict[str, Any]:
        if self.import_from_tmp:
            return self._import_from_tmp_path(change_id)
        proposal_to_export = self.proposal.copy()
        if not self.should_sanitize:
            return proposal_to_export
        original_description = self.proposal.get("description", "")
        original_rationale = self.proposal.get("rationale", "")
        combined_markdown = ""
        if original_rationale:
            combined_markdown += f"## Why\n\n{original_rationale}\n\n"
        if original_description:
            combined_markdown += f"## What Changes\n\n{original_description}\n\n"
        if not combined_markdown:
            return proposal_to_export
        sanitized_markdown = self.sanitizer.sanitize_proposal(combined_markdown)
        why_match = re.search(r"##\s*Why\s*\n\n(.*?)(?=\n##|\Z)", sanitized_markdown, re.DOTALL)
        sanitized_rationale = why_match.group(1).strip() if why_match else ""
        what_match = re.search(r"##\s*What\s+Changes\s*\n\n(.*?)(?=\n##|\Z)", sanitized_markdown, re.DOTALL)
        sanitized_description = what_match.group(1).strip() if what_match else ""
        proposal_to_export["description"] = sanitized_description or original_description
        proposal_to_export["rationale"] = sanitized_rationale or original_rationale
        return proposal_to_export

    def _import_from_tmp_path(self, change_id: str) -> dict[str, Any]:
        sanitized_file_path = self.tmp_file or (
            Path(tempfile.gettempdir()) / f"specfact-proposal-{change_id}-sanitized.md"
        )
        try:
            if not sanitized_file_path.exists():
                self.errors.append(
                    f"Sanitized file not found: {sanitized_file_path}. Please run LLM sanitization first."
                )
                return {}
            sanitized_content = sanitized_file_path.read_text(encoding="utf-8")
            proposal_to_export = self.bridge._parse_sanitized_proposal(sanitized_content, self.proposal)
            try:
                original_tmp = Path(tempfile.gettempdir()) / f"specfact-proposal-{change_id}.md"
                if original_tmp.exists():
                    original_tmp.unlink()
                if sanitized_file_path.exists():
                    sanitized_file_path.unlink()
            except Exception as cleanup_error:
                self.warnings.append(f"Failed to cleanup temporary files: {cleanup_error}")
            return proposal_to_export
        except Exception as e:
            self.errors.append(f"Failed to import sanitized content for '{change_id}': {e}")
            return {}

    def _export_artifact_and_persist(self, proposal_to_export: dict[str, Any]) -> None:
        if not proposal_to_export and self.import_from_tmp:
            return
        result = self.adapter.export_artifact(
            artifact_key="change_proposal",
            artifact_data=proposal_to_export,
            bridge_config=self.bridge.bridge_config,
        )
        if isinstance(self.proposal, dict) and isinstance(result, dict):
            self.source_tracking_list = self.bridge._normalize_source_tracking(self.proposal.get("source_tracking", {}))
            if self.adapter_type == "ado" and self.ado_org and self.ado_project:
                repo_identifier = self.target_repo or f"{self.ado_org}/{self.ado_project}"
                source_id = str(result.get("work_item_id", result.get("issue_number", "")))
                source_url = str(result.get("work_item_url", result.get("issue_url", "")))
            else:
                repo_identifier = self.target_repo or f"{self.repo_owner}/{self.repo_name}"
                source_id = str(result.get("issue_number", result.get("work_item_id", "")))
                source_url = str(result.get("issue_url", result.get("work_item_url", "")))
            new_entry = {
                "source_id": source_id,
                "source_url": source_url,
                "source_type": self.adapter_type,
                "source_repo": repo_identifier,
                "source_metadata": {
                    "last_synced_status": self.proposal.get("status"),
                    "sanitized": self.should_sanitize if self.should_sanitize is not None else False,
                },
            }
            self.source_tracking_list = self.bridge._update_source_tracking_entry(
                self.source_tracking_list, repo_identifier, new_entry
            )
            self.proposal["source_tracking"] = self.source_tracking_list
        self.operations.append(
            SyncOperation(
                artifact_key="change_proposal",
                feature_id=self.proposal.get("change_id", "unknown"),
                direction="export",
                bundle_name="openspec",
            )
        )
        self.bridge._save_openspec_change_proposal(self.proposal)


def ecd_export_one_change_proposal(
    bridge: Any,
    proposal: dict[str, Any],
    adapter: Any,
    adapter_type: str,
    target_repo: str | None,
    repo_owner: str | None,
    repo_name: str | None,
    ado_org: str | None,
    ado_project: str | None,
    update_existing: bool,
    import_from_tmp: bool,
    tmp_file: Path | None,
    export_to_tmp: bool,
    should_sanitize: Any,
    track_code_changes: bool,
    add_progress_comment: bool,
    code_repo_path: Path | None,
    sanitizer: Any,
    operations: list[SyncOperation],
    errors: list[str],
    warnings: list[str],
) -> None:
    EcdOneProposalExport(
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
    ).run()
