"""
Bridge-based bidirectional sync implementation.

This module provides adapter-agnostic bidirectional synchronization between
external tool artifacts and SpecFact project bundles using bridge configuration.
The sync layer reads bridge config, resolves paths dynamically, and delegates
to adapter-specific parsers/generators.
"""

# pylint: disable=too-many-lines,import-outside-toplevel,line-too-long,broad-exception-caught,too-many-nested-blocks,too-many-arguments,too-many-locals,reimported,redefined-outer-name,logging-fstring-interpolation,unused-argument,protected-access,too-many-positional-arguments,consider-using-in,unused-import,redefined-argument-from-local,using-constant-test,too-many-boolean-expressions,too-many-return-statements,use-implicit-booleaness-not-comparison,too-many-branches,too-many-statements

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.models.bridge import AdapterType, BridgeConfig
from specfact_cli.runtime import get_configured_console
from specfact_cli.utils.bundle_loader import load_project_bundle, save_project_bundle

from specfact_project.sync_runtime.bridge_probe import BridgeProbe
from specfact_project.sync_runtime.speckit_bridge_backlog import detect_speckit_backlog_mappings


console = get_configured_console()


@dataclass
class SyncOperation:
    """Represents a sync operation (import or export)."""

    artifact_key: str  # Artifact key (e.g., "specification", "plan")
    feature_id: str  # Feature identifier (e.g., "001-auth")
    direction: str  # "import" or "export"
    bundle_name: str  # Project bundle name


@dataclass
class SyncResult:
    """Result of a bridge-based sync operation."""

    success: bool
    operations: list[SyncOperation]
    errors: list[str]
    warnings: list[str]


class BridgeSync:
    """
    Adapter-agnostic bidirectional sync using bridge configuration.

    This class provides generic sync functionality that works with any tool
    adapter by using bridge configuration to resolve paths dynamically.

    Note: All adapter-specific logic (import/export) is handled by adapters
    via the AdapterRegistry. This class does NOT contain hard-coded adapter
    checks. Future adapters (SpecKitAdapter, GenericMarkdownAdapter) should
    be created to move any remaining adapter-specific logic out of this class.
    """

    @beartype
    @require(lambda repo_path: repo_path.exists(), "Repository path must exist")
    @require(lambda repo_path: repo_path.is_dir(), "Repository path must be a directory")
    def __init__(self, repo_path: Path, bridge_config: BridgeConfig | None = None) -> None:
        """
        Initialize bridge sync.

        Args:
            repo_path: Path to repository root
            bridge_config: Bridge configuration (auto-detected if None)
        """
        self.repo_path = Path(repo_path).resolve()
        self.bridge_config = bridge_config

        if self.bridge_config is None:
            # Auto-detect and load bridge config
            self.bridge_config = self._load_or_generate_bridge_config()

    def _find_code_repo_via_cwd(self, repo_name: str) -> Path | None:
        try:
            cwd = Path.cwd()
            if cwd.name == repo_name and (cwd / ".git").exists():
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 and repo_name in result.stdout:
                    return cwd
        except Exception:
            return None
        return None

    def _find_code_repo_via_parent(self, repo_name: str) -> Path | None:
        try:
            cwd = Path.cwd()
            repo_path = cwd.parent / repo_name
            if repo_path.exists() and (repo_path / ".git").exists():
                return repo_path
        except Exception:
            return None
        return None

    def _find_code_repo_via_siblings(self, repo_name: str) -> Path | None:
        try:
            cwd = Path.cwd()
            grandparent = cwd.parent.parent if cwd.parent != Path("/") else None
            if not grandparent:
                return None
            for sibling in grandparent.iterdir():
                if sibling.is_dir() and sibling.name == repo_name and (sibling / ".git").exists():
                    return sibling
        except Exception:
            return None
        return None

    def _find_code_repo_path(self, _repo_owner: str, repo_name: str) -> Path | None:
        """
        Find local path to code repository based on repo_owner and repo_name.

        Args:
            _repo_owner: Repository owner (e.g., "nold-ai") — reserved for future URL matching
            repo_name: Repository name (e.g., "specfact-cli")

        Returns:
            Path to code repository if found, None otherwise
        """
        found = self._find_code_repo_via_cwd(repo_name)
        if found is not None:
            return found
        found = self._find_code_repo_via_parent(repo_name)
        if found is not None:
            return found
        return self._find_code_repo_via_siblings(repo_name)

    @beartype
    @ensure(lambda result: isinstance(result, BridgeConfig), "Must return BridgeConfig")
    def _load_or_generate_bridge_config(self) -> BridgeConfig:
        """
        Load bridge config from file or auto-generate if missing.

        Returns:
            BridgeConfig instance
        """
        from specfact_cli.utils.structure import SpecFactStructure

        bridge_path = self.repo_path / SpecFactStructure.CONFIG / "bridge.yaml"

        if bridge_path.exists():
            return BridgeConfig.load_from_file(bridge_path)

        # Auto-generate bridge config
        probe = BridgeProbe(self.repo_path)
        capabilities = probe.detect()
        bridge_config = probe.auto_generate_bridge(capabilities)
        probe.save_bridge_config(bridge_config, overwrite=False)
        return bridge_config

    @beartype
    @require(lambda self: self.bridge_config is not None, "Bridge config must be set")
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @require(lambda feature_id: isinstance(feature_id, str) and len(feature_id) > 0, "Feature ID must be non-empty")
    @ensure(lambda result: isinstance(result, Path), "Must return Path")
    def resolve_artifact_path(self, artifact_key: str, feature_id: str, bundle_name: str) -> Path:
        """
        Resolve artifact path using bridge configuration.

        Args:
            artifact_key: Artifact key (e.g., "specification", "plan")
            feature_id: Feature identifier (e.g., "001-auth")
            bundle_name: Project bundle name (for context)

        Returns:
            Resolved Path object
        """
        if self.bridge_config is None:
            msg = "Bridge config not initialized"
            raise ValueError(msg)

        base_path = self.repo_path
        if self.bridge_config.external_base_path is not None:
            base_path = self.bridge_config.external_base_path

        if artifact_key == "project_context" and self.bridge_config.adapter == AdapterType.OPENSPEC:
            config_yaml = base_path / "openspec" / "config.yaml"
            project_md = base_path / "openspec" / "project.md"
            if config_yaml.exists():
                return config_yaml
            if project_md.exists():
                return project_md
            return project_md

        context = {
            "feature_id": feature_id,
            "bundle_name": bundle_name,
        }
        return self.bridge_config.resolve_path(artifact_key, context, base_path=self.repo_path)

    @beartype
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @require(lambda feature_id: isinstance(feature_id, str) and len(feature_id) > 0, "Feature ID must be non-empty")
    @ensure(lambda result: isinstance(result, SyncResult), "Must return SyncResult")
    def import_artifact(
        self,
        artifact_key: str,
        feature_id: str,
        bundle_name: str,
        persona: str | None = None,
    ) -> SyncResult:
        """
        Import artifact from tool format to SpecFact project bundle.

        Args:
            artifact_key: Artifact key (e.g., "specification", "plan")
            feature_id: Feature identifier (e.g., "001-auth")
            bundle_name: Project bundle name
            persona: Persona for ownership validation (optional)

        Returns:
            SyncResult with operation details
        """
        operations: list[SyncOperation] = []
        errors: list[str] = []
        warnings: list[str] = []

        if self.bridge_config is None:
            errors.append("Bridge config not initialized")
            return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

        try:
            # Resolve artifact path
            artifact_path = self.resolve_artifact_path(artifact_key, feature_id, bundle_name)

            if not artifact_path.exists():
                errors.append(f"Artifact not found: {artifact_path}")
                return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

            # Conflict detection: warn that bundle will be updated
            warnings.append(
                f"Importing {artifact_key} from {artifact_path}. "
                "This will update the project bundle. Existing bundle content may be modified."
            )

            # Load project bundle
            from specfact_cli.utils.structure import SpecFactStructure

            bundle_dir = self.repo_path / SpecFactStructure.PROJECTS / bundle_name
            if not bundle_dir.exists():
                errors.append(f"Project bundle not found: {bundle_dir}")
                return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

            project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)

            # Get adapter from registry (universal pattern - no hard-coded checks)
            adapter = AdapterRegistry.get_adapter(self.bridge_config.adapter.value)
            adapter.import_artifact(artifact_key, artifact_path, project_bundle, self.bridge_config)

            # Save updated bundle
            save_project_bundle(project_bundle, bundle_dir, atomic=True)

            operations.append(
                SyncOperation(
                    artifact_key=artifact_key,
                    feature_id=feature_id,
                    direction="import",
                    bundle_name=bundle_name,
                )
            )

        except Exception as e:
            errors.append(f"Import failed: {e}")

        return SyncResult(
            success=len(errors) == 0,
            operations=operations,
            errors=errors,
            warnings=warnings,
        )

    @beartype
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @require(lambda feature_id: isinstance(feature_id, str) and len(feature_id) > 0, "Feature ID must be non-empty")
    @ensure(lambda result: isinstance(result, SyncResult), "Must return SyncResult")
    def export_artifact(
        self,
        artifact_key: str,
        feature_id: str,
        bundle_name: str,
        persona: str | None = None,
    ) -> SyncResult:
        """
        Export artifact from SpecFact project bundle to tool format.

        Args:
            artifact_key: Artifact key (e.g., "specification", "plan")
            feature_id: Feature identifier (e.g., "001-auth")
            bundle_name: Project bundle name
            persona: Persona for section filtering (optional)

        Returns:
            SyncResult with operation details
        """
        operations: list[SyncOperation] = []
        errors: list[str] = []
        warnings: list[str] = []

        if self.bridge_config is None:
            errors.append("Bridge config not initialized")
            return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

        try:
            # Load project bundle
            from specfact_cli.utils.structure import SpecFactStructure

            bundle_dir = self.repo_path / SpecFactStructure.PROJECTS / bundle_name
            if not bundle_dir.exists():
                errors.append(f"Project bundle not found: {bundle_dir}")
                return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

            project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)

            # Get adapter from registry (universal pattern - no hard-coded checks)
            adapter = AdapterRegistry.get_adapter(self.bridge_config.adapter.value)

            # Find feature in bundle for export
            feature = None
            for key, feat in project_bundle.features.items():
                if key == feature_id or feature_id in key:
                    feature = feat
                    break

            if feature is None:
                errors.append(f"Feature '{feature_id}' not found in bundle '{bundle_name}'")
                return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

            # Export using adapter (adapter handles path resolution and writing)
            exported_result = adapter.export_artifact(artifact_key, feature, self.bridge_config)

            # Handle export result (Path for file-based, dict for API-based)
            if isinstance(exported_result, Path):
                # File-based export - check if file was created
                if not exported_result.exists():
                    warnings.append(f"Adapter exported to {exported_result} but file does not exist")
                else:
                    # Conflict detection: warn if file was overwritten
                    warnings.append(f"Exported to {exported_result}. Use --overwrite flag to suppress this message.")
            elif isinstance(exported_result, dict):
                # API-based export (e.g., GitHub issues)
                # Adapter handles the export, result contains API response data
                pass

            operations.append(
                SyncOperation(
                    artifact_key=artifact_key,
                    feature_id=feature_id,
                    direction="export",
                    bundle_name=bundle_name,
                )
            )

        except Exception as e:
            errors.append(f"Export failed: {e}")

        return SyncResult(
            success=len(errors) == 0,
            operations=operations,
            errors=errors,
            warnings=warnings,
        )

    @beartype
    @require(lambda self: self.bridge_config is not None, "Bridge config must be set")
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @ensure(lambda result: result is None, "Must return None")
    def generate_alignment_report(self, bundle_name: str, output_file: Path | None = None) -> None:
        """
        Generate alignment report comparing SpecFact features vs OpenSpec specs.

        This method compares features in the SpecFact bundle with specifications
        in OpenSpec to identify gaps and calculate coverage.

        Args:
            bundle_name: Project bundle name
            output_file: Optional file path to save report (if None, only prints to console)
        """
        from specfact_project.sync_runtime.bridge_sync_alignment_helpers import run_generate_alignment_report

        run_generate_alignment_report(self.repo_path, self.bridge_config, bundle_name, output_file)

    @beartype
    @require(lambda self: self.bridge_config is not None, "Bridge config must be set")
    @require(
        lambda adapter_type: isinstance(adapter_type, str) and adapter_type in ("github", "ado", "linear", "jira"),
        "Adapter must be DevOps type",
    )
    @ensure(lambda result: isinstance(result, SyncResult), "Must return SyncResult")
    def export_change_proposals_to_devops(
        self,
        adapter_type: str,
        repo_owner: str | None = None,
        repo_name: str | None = None,
        api_token: str | None = None,
        use_gh_cli: bool = True,
        sanitize: bool | None = None,
        target_repo: str | None = None,
        interactive: bool = False,
        change_ids: list[str] | None = None,
        export_to_tmp: bool = False,
        import_from_tmp: bool = False,
        tmp_file: Path | None = None,
        update_existing: bool = False,
        track_code_changes: bool = False,
        add_progress_comment: bool = False,
        code_repo_path: Path | None = None,
        include_archived: bool = False,
        ado_org: str | None = None,
        ado_project: str | None = None,
        ado_base_url: str | None = None,
        ado_work_item_type: str | None = None,
    ) -> SyncResult:
        """
        Export OpenSpec change proposals to DevOps tools (export-only mode).

        This method reads OpenSpec change proposals and creates/updates DevOps issues
        (GitHub Issues, ADO Work Items, etc.) via the appropriate adapter.

        Args:
            adapter_type: DevOps adapter type (github, ado, linear, jira)
            repo_owner: Repository owner (for GitHub/ADO)
            repo_name: Repository name (for GitHub/ADO)
            api_token: API token (optional, uses env vars, gh CLI, or --github-token if not provided)
            use_gh_cli: If True, try to get token from GitHub CLI (`gh auth token`) for GitHub adapter
            sanitize: If True, sanitize content for public issues. If None, auto-detect based on repo setup.
            target_repo: Target repository for issue creation (format: owner/repo). Default: same as code repo.
            interactive: If True, use interactive mode for AI-assisted sanitization (requires slash command).
            change_ids: Optional list of change proposal IDs to filter. If None, exports all active proposals.
            export_to_tmp: If True, export proposal content to temporary file for LLM review.
            import_from_tmp: If True, import sanitized content from temporary file after LLM review.
            tmp_file: Optional custom temporary file path. Default: <system-temp>/specfact-proposal-<change-id>.md.

        Returns:
            SyncResult with operation details

        Note:
            Requires OpenSpec bridge adapter to be implemented (dependency).
            For now, this is a placeholder that will be fully implemented once
            the OpenSpec adapter is available.
        """
        from specfact_project.sync_runtime.bridge_sync_export_change_proposals_impl import (
            run_export_change_proposals_to_devops,
        )

        return run_export_change_proposals_to_devops(
            self,
            adapter_type,
            repo_owner=repo_owner,
            repo_name=repo_name,
            api_token=api_token,
            use_gh_cli=use_gh_cli,
            sanitize=sanitize,
            target_repo=target_repo,
            interactive=interactive,
            change_ids=change_ids,
            export_to_tmp=export_to_tmp,
            import_from_tmp=import_from_tmp,
            tmp_file=tmp_file,
            update_existing=update_existing,
            track_code_changes=track_code_changes,
            add_progress_comment=add_progress_comment,
            code_repo_path=code_repo_path,
            include_archived=include_archived,
            ado_org=ado_org,
            ado_project=ado_project,
            ado_base_url=ado_base_url,
            ado_work_item_type=ado_work_item_type,
        )

    def _read_openspec_change_proposals(self, include_archived: bool = True) -> list[dict[str, Any]]:
        """
        Read OpenSpec change proposals from openspec/changes/ directory.

        Args:
            include_archived: If True, include archived changes (default: True for backward compatibility)

        Returns:
            List of change proposal dicts with keys: change_id, title, description, rationale, status, source_tracking

        Note:
            This is a basic implementation that reads OpenSpec proposal.md files directly.
            Once the OpenSpec bridge adapter is implemented, this should delegate to it.
        """
        from specfact_project.sync_runtime.bridge_sync_read_openspec_proposals import read_openspec_change_proposals

        return read_openspec_change_proposals(self, include_archived)

    def _find_source_tracking_entry(
        self, source_tracking: list[dict[str, Any]] | dict[str, Any] | None, target_repo: str | None
    ) -> dict[str, Any] | None:
        """
        Find source tracking entry for a specific repository.

        Args:
            source_tracking: Source tracking (list of entries or single dict for backward compatibility)
            target_repo: Target repository identifier (e.g., "nold-ai/specfact-cli")

        Returns:
            Matching entry dict or None if not found
        """
        from specfact_project.sync_runtime.bridge_sync_find_source_tracking_entry import find_source_tracking_entry

        return find_source_tracking_entry(source_tracking, target_repo)

    @beartype
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @ensure(lambda result: isinstance(result, SyncResult), "Must return SyncResult")
    def import_backlog_items_to_bundle(
        self,
        adapter_type: str,
        bundle_name: str,
        backlog_items: list[str],
        adapter_kwargs: dict[str, Any] | None = None,
    ) -> SyncResult:
        """
        Import selected backlog items into a project bundle.

        Args:
            adapter_type: Backlog adapter type (github, ado)
            bundle_name: Project bundle name
            backlog_items: Backlog item identifiers (IDs or URLs)
            adapter_kwargs: Adapter-specific kwargs for initialization

        Returns:
            SyncResult with operation details
        """
        from specfact_project.sync_runtime.bridge_sync_backlog_bundle_impl import run_import_backlog_items_to_bundle

        return run_import_backlog_items_to_bundle(self, adapter_type, bundle_name, backlog_items, adapter_kwargs)

    @beartype
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @ensure(lambda result: isinstance(result, SyncResult), "Must return SyncResult")
    def export_backlog_from_bundle(
        self,
        adapter_type: str,
        bundle_name: str,
        adapter_kwargs: dict[str, Any] | None = None,
        update_existing: bool = False,
        change_ids: list[str] | None = None,
    ) -> SyncResult:
        """
        Export backlog items stored in a project bundle to a backlog adapter.

        Args:
            adapter_type: Backlog adapter type (github, ado)
            bundle_name: Project bundle name
            adapter_kwargs: Adapter-specific kwargs for initialization
            update_existing: If True, update existing backlog items with stored content
            change_ids: Optional list of change IDs to export (filter)

        Returns:
            SyncResult with operation details
        """
        from specfact_project.sync_runtime.bridge_sync_backlog_bundle_impl import run_export_backlog_from_bundle

        return run_export_backlog_from_bundle(
            self,
            adapter_type,
            bundle_name,
            adapter_kwargs,
            update_existing,
            change_ids,
        )

    def _build_backlog_entry_from_result(
        self,
        adapter_type: str,
        target_repo: str | None,
        export_result: dict[str, Any],
        status: str,
    ) -> dict[str, Any] | None:
        """
        Build a backlog entry from adapter export result.

        Args:
            adapter_type: Backlog adapter type
            target_repo: Target repository identifier
            export_result: Adapter export response dict
            status: Proposal status for sync metadata

        Returns:
            Backlog entry dict or None if no IDs were returned
        """
        from specfact_project.sync_runtime.bridge_sync_backlog_helpers import build_backlog_entry_from_result

        return build_backlog_entry_from_result(adapter_type, target_repo, export_result, status)

    def _get_backlog_entries(self, proposal: Any) -> list[dict[str, Any]]:
        """
        Retrieve backlog entries stored on a change proposal.

        Args:
            proposal: ChangeProposal instance

        Returns:
            List of backlog entry dicts
        """
        from specfact_project.sync_runtime.bridge_sync_backlog_helpers import get_backlog_entries_list

        return get_backlog_entries_list(proposal)

    def _upsert_backlog_entry(self, entries: list[dict[str, Any]], new_entry: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Insert or update a backlog entry in the entries list.

        Args:
            entries: Existing backlog entries
            new_entry: New or updated backlog entry

        Returns:
            Updated backlog entries list
        """
        from specfact_project.sync_runtime.bridge_sync_backlog_helpers import upsert_backlog_entry_list

        return upsert_backlog_entry_list(entries, new_entry)

    def _normalize_source_tracking(
        self, source_tracking: list[dict[str, Any]] | dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Normalize source_tracking to a list of entries (for backward compatibility).

        Args:
            source_tracking: Source tracking (list or single dict)

        Returns:
            List of source tracking entries
        """
        if not source_tracking:
            return []
        if isinstance(source_tracking, dict):
            return [source_tracking]
        if isinstance(source_tracking, list):
            return source_tracking
        return []

    def _dedupe_duplicate_sections(self, text: str) -> str:
        """
        Remove duplicated level-2 sections (##) while preserving the first occurrence.

        Args:
            text: Markdown content to de-duplicate

        Returns:
            De-duplicated markdown content
        """
        if not text:
            return text
        parts = re.split(r"(?m)^##\s+([^\n]+)\s*\n", text)
        if len(parts) < 3:
            return text
        preamble = parts[0].rstrip()
        seen: set[str] = set()
        blocks: list[str] = []
        if preamble.strip():
            blocks.append(preamble.rstrip())
        for i in range(1, len(parts), 2):
            header = parts[i].strip()
            body = parts[i + 1].rstrip()
            if header in seen:
                continue
            seen.add(header)
            blocks.append(f"## {header}\n{body}".rstrip())
        return "\n\n".join(blocks).strip()

    def _verify_work_item_exists(
        self,
        issue_number: str | int | None,
        target_entry: dict[str, Any] | None,
        adapter_type: str,
        adapter: Any,
        ado_org: str | None,
        ado_project: str | None,
        proposal: dict[str, Any],
        warnings: list[str],
    ) -> tuple[str | int | None, bool]:
        """
        Verify if work item/issue exists in external tool (handles deleted items).

        Args:
            issue_number: Current issue/work item number
            target_entry: Source tracking entry
            adapter_type: Adapter type (github, ado, etc.)
            adapter: Adapter instance
            ado_org: ADO organization (for ADO adapter)
            ado_project: ADO project (for ADO adapter)
            proposal: Change proposal dict
            warnings: Warnings list to append to

        Returns:
            Tuple of (issue_number, work_item_was_deleted)
        """
        work_item_was_deleted = False

        if issue_number and target_entry:
            entry_type = target_entry.get("source_type", "").lower()

            # For ADO, verify work item exists (it might have been deleted)
            if (
                entry_type == "ado"
                and adapter_type.lower() == "ado"
                and ado_org
                and ado_project
                and hasattr(adapter, "_work_item_exists")
            ):
                try:
                    work_item_exists = adapter._work_item_exists(issue_number, ado_org, ado_project)
                    if not work_item_exists:
                        # Work item was deleted - clear source_id to allow recreation
                        warnings.append(
                            f"Work item #{issue_number} for '{proposal.get('change_id', 'unknown')}' "
                            f"no longer exists in ADO (may have been deleted). "
                            f"Will create a new work item."
                        )
                        # Clear source_id to allow creation of new work item
                        issue_number = None
                        work_item_was_deleted = True
                except Exception as e:
                    # On error checking existence, log warning but allow creation (safer)
                    warnings.append(f"Could not verify work item #{issue_number} existence: {e}. Proceeding with sync.")

        return issue_number, work_item_was_deleted

    def _search_existing_github_issue(
        self,
        change_id: str,
        repo_owner: str,
        repo_name: str,
        target_repo: str | None,
        warnings: list[str],
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Search for existing GitHub issue by change proposal ID.

        Args:
            change_id: Change proposal ID
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            target_repo: Target repository identifier
            warnings: Warnings list to append to

        Returns:
            Tuple of (target_entry, issue_number) if found, (None, None) otherwise
        """
        try:
            import requests
            from specfact_cli.adapters.registry import AdapterRegistry

            adapter_instance = AdapterRegistry.get_adapter("github")
            if adapter_instance and hasattr(adapter_instance, "api_token") and adapter_instance.api_token:
                # Search for issues containing the change proposal ID in the footer
                search_url = f"{adapter_instance.base_url}/search/issues"
                search_query = f'repo:{repo_owner}/{repo_name} "OpenSpec Change Proposal: `{change_id}`" in:body'
                headers = {
                    "Authorization": f"token {adapter_instance.api_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                params = {"q": search_query}
                search_response = requests.get(search_url, headers=headers, params=params, timeout=30)
                if search_response.status_code == 200:
                    search_results = search_response.json()
                    items = search_results.get("items", [])
                    if items:
                        # Found existing issue - use it instead of creating a new one
                        existing_issue = items[0]  # Use the first match
                        existing_issue_number = existing_issue.get("number")
                        existing_issue_url = existing_issue.get("html_url", "")
                        warnings.append(
                            f"Found existing GitHub issue #{existing_issue_number} for change proposal '{change_id}'. "
                            f"Will update it instead of creating a new issue."
                        )
                        # Create source_tracking entry for the found issue
                        target_entry = {
                            "source_type": "github",
                            "source_id": str(existing_issue_number),
                            "source_url": existing_issue_url,
                            "source_repo": target_repo or f"{repo_owner}/{repo_name}",
                            "source_metadata": {},
                        }
                        return target_entry, str(existing_issue_number)
        except Exception as e:
            # If search fails, proceed with creation (safer than blocking)
            warnings.append(
                f"Could not search for existing GitHub issue for '{change_id}': {e}. Proceeding with creation."
            )

        return None, None

    def _update_existing_issue(
        self,
        proposal: dict[str, Any],
        target_entry: dict[str, Any],
        issue_number: str | int,
        adapter: Any,
        adapter_type: str,
        target_repo: str | None,
        source_tracking_list: list[dict[str, Any]],
        source_tracking_raw: dict[str, Any] | list[dict[str, Any]],
        repo_owner: str | None,
        repo_name: str | None,
        ado_org: str | None,
        ado_project: str | None,
        update_existing: bool,
        import_from_tmp: bool,
        tmp_file: Path | None,
        should_sanitize: bool | None,
        track_code_changes: bool,
        add_progress_comment: bool,
        code_repo_path: Path | None,
        operations: list[Any],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Update existing issue/work item with new status, metadata, and content.

        Args:
            proposal: Change proposal dict
            target_entry: Source tracking entry for this repository
            issue_number: Issue/work item number
            adapter: Adapter instance
            adapter_type: Adapter type (github, ado, etc.)
            target_repo: Target repository identifier
            source_tracking_list: Normalized source tracking list
            source_tracking_raw: Original source tracking (dict or list)
            repo_owner: Repository owner (for GitHub)
            repo_name: Repository name (for GitHub)
            ado_org: ADO organization (for ADO)
            ado_project: ADO project (for ADO)
            update_existing: Whether to update content when hash changes
            import_from_tmp: Whether importing from temporary file
            tmp_file: Temporary file path
            should_sanitize: Whether to sanitize content
            operations: Operations list to append to
            errors: Errors list to append to
            warnings: Warnings list to append to
        """
        from specfact_project.sync_runtime.bridge_sync_issue_update_impl import run_update_existing_issue

        run_update_existing_issue(
            self,
            proposal,
            target_entry,
            issue_number,
            adapter,
            adapter_type,
            target_repo,
            source_tracking_list,
            source_tracking_raw,
            repo_owner,
            repo_name,
            ado_org,
            ado_project,
            update_existing,
            import_from_tmp,
            tmp_file,
            should_sanitize,
            track_code_changes,
            add_progress_comment,
            code_repo_path,
            operations,
            errors,
            warnings,
        )

    def _update_issue_content_if_needed(
        self,
        proposal: dict[str, Any],
        target_entry: dict[str, Any],
        issue_number: str | int,
        adapter: Any,
        adapter_type: str,
        target_repo: str | None,
        source_tracking_list: list[dict[str, Any]],
        repo_owner: str | None,
        repo_name: str | None,
        ado_org: str | None,
        ado_project: str | None,
        import_from_tmp: bool,
        tmp_file: Path | None,
        operations: list[Any],
        errors: list[str],
    ) -> None:
        """
        Update issue/work item content if hash changed or title needs update.

        Args:
            proposal: Change proposal dict
            target_entry: Source tracking entry
            issue_number: Issue/work item number
            adapter: Adapter instance
            adapter_type: Adapter type
            target_repo: Target repository identifier
            source_tracking_list: Source tracking list
            repo_owner: Repository owner (for GitHub)
            repo_name: Repository name (for GitHub)
            ado_org: ADO organization (for ADO)
            ado_project: ADO project (for ADO)
            import_from_tmp: Whether importing from temporary file
            tmp_file: Temporary file path
            operations: Operations list to append to
            errors: Errors list to append to
        """
        from specfact_project.sync_runtime.bridge_sync_issue_update_impl import run_update_issue_content_if_needed

        run_update_issue_content_if_needed(
            self,
            proposal,
            target_entry,
            issue_number,
            adapter,
            adapter_type,
            target_repo,
            source_tracking_list,
            repo_owner,
            repo_name,
            ado_org,
            ado_project,
            import_from_tmp,
            tmp_file,
            operations,
            errors,
        )

    def _handle_code_change_tracking(
        self,
        proposal: dict[str, Any],
        target_entry: dict[str, Any] | None,
        target_repo: str | None,
        source_tracking_list: list[dict[str, Any]],
        adapter: Any,
        track_code_changes: bool,
        add_progress_comment: bool,
        code_repo_path: Path | None,
        should_sanitize: bool | None,
        operations: list[Any],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Handle code change tracking and add progress comments if enabled.
        """
        from specfact_project.sync_runtime.bridge_sync_issue_update_impl import run_handle_code_change_tracking

        run_handle_code_change_tracking(
            self,
            proposal,
            target_entry,
            target_repo,
            source_tracking_list,
            adapter,
            track_code_changes,
            add_progress_comment,
            code_repo_path,
            should_sanitize,
            operations,
            errors,
            warnings,
        )

    def _update_source_tracking_entry(
        self,
        source_tracking_list: list[dict[str, Any]],
        target_repo: str,
        entry_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Update or add source tracking entry for a specific repository.

        Args:
            source_tracking_list: List of source tracking entries
            target_repo: Target repository identifier
            entry_data: Entry data to update/add

        Returns:
            Updated list of source tracking entries
        """
        from specfact_project.sync_runtime.bridge_sync_source_tracking_list_impl import run_update_source_tracking_entry

        return run_update_source_tracking_entry(self, source_tracking_list, target_repo, entry_data)

    def _parse_source_tracking_entry(self, entry_content: str, repo_name: str | None) -> dict[str, Any] | None:
        """
        Parse a single source tracking entry from markdown content.

        Args:
            entry_content: Markdown content for this entry
            repo_name: Repository name (if specified in header)

        Returns:
            Source tracking entry dict or None if no valid entry found
        """
        from specfact_project.sync_runtime.bridge_sync_parse_source_tracking_entry_impl import (
            run_parse_source_tracking_entry,
        )

        return run_parse_source_tracking_entry(self, entry_content, repo_name)

    @beartype
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _detect_speckit_backlog_mappings_for_proposal(
        self, proposal_name: str, adapter_type: str
    ) -> list[dict[str, Any]]:
        """Compatibility wrapper for Spec-Kit backlog mapping detection."""
        return detect_speckit_backlog_mappings(
            repo_path=self.repo_path,
            proposal_name=proposal_name,
            adapter_type=adapter_type,
        )

    def _calculate_content_hash(self, proposal: dict[str, Any]) -> str:
        """
        Calculate content hash for change proposal (Why + What Changes sections).

        Args:
            proposal: Change proposal dict with description and rationale

        Returns:
            SHA-256 hash (first 16 characters) of proposal content
        """
        rationale = proposal.get("rationale", "")
        description = proposal.get("description", "")
        # Combine Why + What Changes sections for hash calculation
        content = f"{rationale}\n{description}".strip()
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        # Return first 16 chars for storage efficiency
        return hash_obj.hexdigest()[:16]

    def _save_openspec_change_proposal(self, proposal: dict[str, Any]) -> None:
        """
        Save updated change proposal back to OpenSpec proposal.md file.

        Adds or updates a metadata section at the end of proposal.md with
        source_tracking information (GitHub issue IDs, etc.).

        Args:
            proposal: Change proposal dict with updated source_tracking
        """
        from specfact_project.sync_runtime.bridge_sync_save_openspec_proposal_impl import (
            run_save_openspec_change_proposal,
        )

        run_save_openspec_change_proposal(self, proposal)

    def _format_proposal_for_export(self, proposal: dict[str, Any]) -> str:
        """
        Format proposal as markdown for export to temporary file.

        Args:
            proposal: Change proposal dict

        Returns:
            Markdown-formatted proposal content
        """
        lines = []
        lines.append(f"# Change: {proposal.get('title', 'Untitled')}")
        lines.append("")

        rationale = proposal.get("rationale", "")
        if rationale:
            lines.append("## Why")
            lines.append("")
            lines.append(rationale.strip())
            lines.append("")

        description = proposal.get("description", "")
        if description:
            lines.append("## What Changes")
            lines.append("")
            lines.append(description.strip())
            lines.append("")

        return "\n".join(lines)

    def _parse_sanitized_proposal(self, sanitized_content: str, original_proposal: dict[str, Any]) -> dict[str, Any]:
        """
        Parse sanitized markdown content back into proposal structure.

        Args:
            sanitized_content: Sanitized markdown content from temporary file
            original_proposal: Original proposal dict (for metadata)

        Returns:
            Updated proposal dict with sanitized content
        """

        proposal = original_proposal.copy()

        # Extract Why section
        why_match = re.search(r"##\s*Why\s*\n\n(.*?)(?=\n##|\Z)", sanitized_content, re.DOTALL)
        if why_match:
            proposal["rationale"] = why_match.group(1).strip()

        # Extract What Changes section
        what_match = re.search(r"##\s*What\s+Changes\s*\n\n(.*?)(?=\n##|\Z)", sanitized_content, re.DOTALL)
        if what_match:
            proposal["description"] = what_match.group(1).strip()

        return proposal

    def _get_openspec_changes_dir(self) -> Path | None:
        """
        Get OpenSpec changes directory path.

        Checks repo_path first, then external_base_path if available.

        Returns:
            Path to openspec/changes directory, or None if not found
        """
        # Check if openspec/changes exists in repo
        openspec_dir = self.repo_path / "openspec" / "changes"
        if openspec_dir.exists() and openspec_dir.is_dir():
            return openspec_dir

        # Check for external base path in bridge config
        if self.bridge_config and hasattr(self.bridge_config, "external_base_path"):
            external_path = getattr(self.bridge_config, "external_base_path", None)
            if external_path:
                openspec_changes_dir = Path(external_path) / "openspec" / "changes"
                if openspec_changes_dir.exists():
                    return openspec_changes_dir

        return None

    def _determine_affected_specs(self, proposal: Any) -> list[str]:
        """
        Determine affected specs from proposal content.

        Args:
            proposal: ChangeProposal instance

        Returns:
            List of affected spec IDs (e.g., ["devops-sync", "bridge-adapter"])
        """
        # Search proposal description and rationale for spec references
        content = f"{proposal.description} {proposal.rationale}".lower()

        affected_specs: list[str] = []
        known_specs = ["devops-sync", "bridge-adapter", "auth-management", "backlog-analysis"]

        for spec_id in known_specs:
            if spec_id.replace("-", " ") in content or spec_id in content:
                affected_specs.append(spec_id)

        # Default to devops-sync if no specs found (since most backlog imports affect devops-sync)
        if not affected_specs:
            affected_specs = ["devops-sync"]

        return affected_specs

    def _extract_requirement_from_proposal(self, proposal: Any, spec_id: str) -> str:
        """
        Extract requirement text from proposal content.

        Args:
            proposal: ChangeProposal instance
            spec_id: Spec ID to extract requirement for

        Returns:
            Requirement text in OpenSpec format, or empty string if extraction fails
        """
        from specfact_project.sync_runtime.bridge_sync_extract_requirement_impl import (
            run_extract_requirement_from_proposal,
        )

        return run_extract_requirement_from_proposal(self, proposal, spec_id)

    def _generate_tasks_from_proposal(self, proposal: Any) -> str:
        """
        Generate tasks.md content from proposal.

        Extracts tasks from "Acceptance Criteria" section if present,
        otherwise creates placeholder structure.

        Args:
            proposal: ChangeProposal instance

        Returns:
            Markdown content for tasks.md file
        """
        from specfact_project.sync_runtime.bridge_sync_generate_tasks_impl import run_generate_tasks_from_proposal

        return run_generate_tasks_from_proposal(self, proposal)

    def _format_proposal_title(self, title: str) -> str:
        """
        Format proposal title for OpenSpec (remove [Change] prefix and conventional commit prefixes).

        Args:
            title: Original title

        Returns:
            Formatted title
        """
        # Remove [Change] prefix if present
        if title.startswith("[Change]"):
            title = title.replace("[Change]", "").strip()
        if title.startswith("[Change] "):
            title = title.replace("[Change] ", "").strip()

        # Remove conventional commit prefixes (feat:, fix:, etc.)
        return re.sub(
            r"^(feat|fix|add|update|remove|refactor|docs|test|chore|style|perf|ci|build|revert):\s*",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

    def _format_what_changes_section(self, description: str) -> str:
        """
        Format "What Changes" section with NEW/EXTEND/MODIFY markers per OpenSpec conventions.

        Args:
            description: Original description text

        Returns:
            Formatted description with proper markers
        """
        from specfact_project.sync_runtime.bridge_sync_what_changes_impl import run_format_what_changes_section

        return run_format_what_changes_section(self, description)

    def _extract_what_changes_content(self, description: str) -> str:
        """
        Extract only the "What Changes" content from description, excluding sections
        that should be separate (Acceptance Criteria, Dependencies, etc.).

        Args:
            description: Full proposal description

        Returns:
            Only the "What Changes" portion of the description
        """
        from specfact_project.sync_runtime.bridge_sync_what_changes_impl import run_extract_what_changes_content

        return run_extract_what_changes_content(self, description)

    def _extract_dependencies_section(self, description: str) -> str:
        """
        Extract Dependencies section from proposal description.

        Args:
            description: Proposal description text

        Returns:
            Dependencies section content, or empty string if not found
        """
        if not description:
            return ""

        # Look for Dependencies section (may have leading "- " from bullet conversion)
        # Pattern: "- ## Dependencies" or "## Dependencies"
        deps_match = re.search(
            r"(?i)(?:-\s*)?##\s*Dependencies\s*\n(.*?)(?=\n\s*(?:-\s*)?##|\Z)",
            description,
            re.DOTALL,
        )

        if deps_match:
            deps_content = deps_match.group(1).strip()
            # Remove leading "- " from lines if present (from bullet conversion)
            lines = deps_content.split("\n")
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("- "):
                    cleaned_lines.append(stripped[2:])
                elif stripped.startswith("-"):
                    cleaned_lines.append(stripped[1:].lstrip())
                else:
                    cleaned_lines.append(line)
            return "\n".join(cleaned_lines)

        return ""

    def _write_openspec_change_from_proposal(
        self,
        proposal: Any,
        bridge_config: Any,
        template_id: str | None = None,
        refinement_confidence: float | None = None,
    ) -> list[str]:
        """
        Write OpenSpec change files from imported ChangeProposal.

        Args:
            proposal: ChangeProposal instance
            bridge_config: Bridge configuration
            template_id: Optional template ID used for refinement
            refinement_confidence: Optional refinement confidence score (0.0-1.0)

        Returns:
            List of warnings (empty if successful)
        """
        from specfact_project.sync_runtime.bridge_sync_write_openspec_change_impl import (
            run_write_openspec_change_from_proposal,
        )

        return run_write_openspec_change_from_proposal(
            self, proposal, bridge_config, template_id, refinement_confidence
        )

    @beartype
    @require(lambda bundle_name: isinstance(bundle_name, str) and len(bundle_name) > 0, "Bundle name must be non-empty")
    @ensure(lambda result: isinstance(result, SyncResult), "Must return SyncResult")
    def sync_bidirectional(self, bundle_name: str, feature_ids: list[str] | None = None) -> SyncResult:
        """
        Perform bidirectional sync for all artifacts.

        Args:
            bundle_name: Project bundle name
            feature_ids: List of feature IDs to sync (all if None)

        Returns:
            SyncResult with all operations
        """
        operations: list[SyncOperation] = []
        errors: list[str] = []
        warnings: list[str] = []

        if self.bridge_config is None:
            errors.append("Bridge config not initialized")
            return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

        # Validate bridge config before sync
        probe = BridgeProbe(self.repo_path)
        validation = probe.validate_bridge(self.bridge_config)
        warnings.extend(validation["warnings"])
        errors.extend(validation["errors"])

        if errors:
            return SyncResult(success=False, operations=operations, errors=errors, warnings=warnings)

        # If feature_ids not provided, discover from bridge-resolved paths
        if feature_ids is None:
            feature_ids = self._discover_feature_ids()

        # Sync each feature
        for feature_id in feature_ids:
            # Import from tool → bundle
            for _artifact_key in ["specification", "plan", "tasks"]:
                if _artifact_key in self.bridge_config.artifacts:
                    import_result = self.import_artifact(_artifact_key, feature_id, bundle_name)
                    operations.extend(import_result.operations)
                    errors.extend(import_result.errors)
                    warnings.extend(import_result.warnings)

            # Export from bundle → tool (optional, can be controlled by flag)
            # This would be done separately via export_artifact calls

        return SyncResult(
            success=len(errors) == 0,
            operations=operations,
            errors=errors,
            warnings=warnings,
        )

    @beartype
    @require(lambda self: self.bridge_config is not None, "Bridge config must be set")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _discover_feature_ids(self) -> list[str]:
        """
        Discover feature IDs from bridge-resolved paths.

        Returns:
            List of feature IDs found in repository
        """
        feature_ids: list[str] = []

        if self.bridge_config is None:
            return feature_ids

        # Try to discover from first artifact pattern
        if "specification" in self.bridge_config.artifacts:
            artifact = self.bridge_config.artifacts["specification"]
            # Extract base directory from pattern (e.g., "specs/{feature_id}/spec.md" -> "specs")
            pattern_parts = artifact.path_pattern.split("/")
            if len(pattern_parts) > 0:
                base_dir = self.repo_path / pattern_parts[0]
                if base_dir.exists():
                    # Find all subdirectories (potential feature IDs)
                    for item in base_dir.iterdir():
                        if item.is_dir():
                            # Check if it contains the expected artifact file
                            test_path = self.resolve_artifact_path("specification", item.name, "test")
                            if test_path.exists() or (item / "spec.md").exists():
                                feature_ids.append(item.name)

        return feature_ids
