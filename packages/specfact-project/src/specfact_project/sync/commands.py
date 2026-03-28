"""
Sync command - Bidirectional synchronization for external tools and repositories.

This module provides commands for synchronizing changes between external tool artifacts
(e.g., Spec-Kit, Linear, Jira), repository changes, and SpecFact plans using the
bridge architecture.
"""

# pylint: disable=too-many-lines,import-outside-toplevel,line-too-long,broad-exception-caught,too-many-nested-blocks,too-many-arguments,too-many-locals,reimported,redefined-outer-name,logging-fstring-interpolation,unused-argument,protected-access,too-many-positional-arguments,consider-using-in,unused-import,redefined-argument-from-local,using-constant-test,too-many-boolean-expressions,too-many-return-statements,use-implicit-booleaness-not-comparison,too-many-branches,too-many-statements

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from beartype import beartype
from icontract import ensure, require
from specfact_cli.adapters.registry import (
    AdapterRegistry,
)
from specfact_cli.models.bridge import AdapterType
from specfact_cli.models.plan import PlanBundle, Product
from specfact_cli.models.project import BundleManifest, ProjectBundle
from specfact_cli.models.validation import ValidationReport
from specfact_cli.runtime import debug_log_operation, debug_print, get_configured_console, is_debug_mode
from specfact_cli.telemetry import telemetry

from specfact_project.sync_runtime.speckit_change_proposal_sync import detect_sync_profile
from specfact_project.sync_runtime.sync_perform_operation_impl import run_perform_sync_operation
from specfact_project.sync_runtime.sync_tool_to_specfact_impl import run_sync_tool_to_specfact


__all__ = ["AdapterRegistry", "app"]

app = typer.Typer(
    help="Synchronize external tool artifacts and repository changes (Spec-Kit, OpenSpec, GitHub, Linear, Jira, etc.). See 'specfact backlog refine' for template-driven backlog refinement."
)
console = get_configured_console()


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def _detect_sync_profile(repo: Path) -> str:  # pyright: ignore[reportUnusedFunction]
    """Compatibility wrapper for sync profile detection tests."""
    return detect_sync_profile(repo)


@beartype
@require(lambda source: source.exists(), "Source path must exist")
@ensure(lambda result: isinstance(result, ProjectBundle), "Must return ProjectBundle")
def import_to_bundle(source: Path, config: dict[str, Any]) -> ProjectBundle:
    """Convert external source artifacts into a ProjectBundle."""
    if source.is_dir() and (source / "bundle.manifest.yaml").exists():
        return ProjectBundle.load_from_directory(source)
    bundle_name = config.get("bundle_name", source.stem if source.suffix else source.name)
    return ProjectBundle(
        manifest=BundleManifest(schema_metadata=None, project_metadata=None),
        bundle_name=str(bundle_name),
        product=Product(),
    )


@beartype
@require(lambda target: target is not None, "Target path must be provided")
@ensure(lambda target: target.exists(), "Target must exist after export")
def export_from_bundle(bundle: ProjectBundle, target: Path, config: dict[str, Any]) -> None:
    """Export a ProjectBundle to target path."""
    if target.suffix:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        return
    target.mkdir(parents=True, exist_ok=True)
    bundle.save_to_directory(target)


@beartype
@require(lambda external_source: len(external_source.strip()) > 0, "External source must be non-empty")
@ensure(lambda result: isinstance(result, ProjectBundle), "Must return ProjectBundle")
def sync_with_bundle(bundle: ProjectBundle, external_source: str, config: dict[str, Any]) -> ProjectBundle:
    """Synchronize an existing bundle with an external source."""
    source_path = Path(external_source)
    if source_path.exists() and source_path.is_dir() and (source_path / "bundle.manifest.yaml").exists():
        return ProjectBundle.load_from_directory(source_path)
    return bundle


@beartype
@ensure(lambda result: isinstance(result, ValidationReport), "Must return ValidationReport")
def validate_bundle(bundle: ProjectBundle, rules: dict[str, Any]) -> ValidationReport:
    """Validate bundle for module-specific constraints."""
    total_checks = max(len(rules), 1)
    report = ValidationReport(
        status="passed",
        violations=[],
        summary={"total_checks": total_checks, "passed": total_checks, "failed": 0, "warnings": 0},
    )
    if not bundle.bundle_name:
        report.status = "failed"
        report.violations.append(
            {
                "severity": "error",
                "message": "Bundle name is required",
                "location": "ProjectBundle.bundle_name",
            }
        )
        report.summary["failed"] += 1
        report.summary["passed"] = max(report.summary["passed"] - 1, 0)
    return report


@beartype
@ensure(lambda result: isinstance(result, bool), "Must return bool")
def _is_test_mode() -> bool:  # pyright: ignore[reportUnusedFunction]
    """Check if running in test mode."""
    from specfact_project.sync_runtime.sync_command_common import is_test_mode

    return is_test_mode()


@beartype
@require(lambda selection: isinstance(selection, str), "Selection must be string")
@ensure(lambda result: isinstance(result, list), "Must return list")
def _parse_backlog_selection(selection: str) -> list[str]:  # pyright: ignore[reportUnusedFunction]
    """Parse backlog selection string into a list of IDs/URLs."""
    from specfact_project.sync_runtime.sync_command_common import parse_backlog_selection

    return parse_backlog_selection(selection)


@beartype
@require(lambda repo: isinstance(repo, Path), "Repo must be Path")
@ensure(lambda result: result is None or isinstance(result, str), "Must return None or string")
def _infer_bundle_name(repo: Path) -> str | None:
    """Infer bundle name from active config or single bundle directory."""
    from specfact_project.sync_runtime.sync_command_common import infer_bundle_name

    return infer_bundle_name(repo)


@beartype
@require(lambda plan: isinstance(plan, Path), "Plan must be Path")
@ensure(lambda result: result is None or isinstance(result, str), "Must return None or string")
def _extract_bundle_name_from_plan_path(plan: Path) -> str | None:
    """Extract a modular bundle name from a plan path when possible."""
    plan_str = str(plan)
    if "/projects/" in plan_str:
        parts = plan_str.split("/projects/", 1)
        if len(parts) > 1:
            bundle_candidate = parts[1].split("/", 1)[0].strip()
            if bundle_candidate:
                return bundle_candidate
    return None


@beartype
@require(lambda repo: isinstance(repo, Path), "Repo must be Path")
@require(lambda bidirectional: isinstance(bidirectional, bool), "Bidirectional must be bool")
@require(lambda plan: plan is None or isinstance(plan, Path), "Plan must be None or Path")
@require(lambda overwrite: isinstance(overwrite, bool), "Overwrite must be bool")
@require(lambda watch: isinstance(watch, bool), "Watch must be bool")
@require(lambda interval: isinstance(interval, int) and interval >= 1, "Interval must be int >= 1")
@ensure(lambda result: result is None, "Must return None")
def sync_spec_kit(
    repo: Path,
    bidirectional: bool = False,
    plan: Path | None = None,
    overwrite: bool = False,
    watch: bool = False,
    interval: int = 5,
) -> None:
    """
    Compatibility helper for callers that previously imported `sync_spec_kit`.

    Delegates to `sync bridge --adapter speckit` with concrete Python defaults,
    avoiding direct invocation of Typer `OptionInfo` defaults.
    """
    bundle = _extract_bundle_name_from_plan_path(plan) if plan is not None else None
    if bundle is None:
        bundle = _infer_bundle_name(repo)

    sync_bridge(
        repo=repo,
        bundle=bundle,
        bidirectional=bidirectional,
        mode=None,
        feature=None,
        all_features=False,
        overwrite=overwrite,
        watch=watch,
        ensure_compliance=False,
        adapter="speckit",
        repo_owner=None,
        repo_name=None,
        external_base_path=None,
        github_token=None,
        use_gh_cli=True,
        ado_org=None,
        ado_project=None,
        ado_base_url=None,
        ado_token=None,
        ado_work_item_type=None,
        sanitize=None,
        target_repo=None,
        interactive=False,
        change_ids=None,
        backlog_ids=None,
        backlog_ids_file=None,
        export_to_tmp=False,
        import_from_tmp=False,
        tmp_file=None,
        update_existing=False,
        track_code_changes=False,
        add_progress_comment=False,
        code_repo=None,
        include_archived=False,
        interval=interval,
    )


@beartype
@require(lambda repo: repo.exists(), "Repository path must exist")
@require(lambda repo: repo.is_dir(), "Repository path must be a directory")
@require(lambda bidirectional: isinstance(bidirectional, bool), "Bidirectional must be bool")
@require(lambda bundle: bundle is None or isinstance(bundle, str), "Bundle must be None or str")
@require(lambda overwrite: isinstance(overwrite, bool), "Overwrite must be bool")
@require(lambda adapter_type: adapter_type is not None, "Adapter type must be set")
@ensure(lambda result: result is None, "Must return None")
def _perform_sync_operation(  # pyright: ignore[reportUnusedFunction]
    repo: Path,
    bidirectional: bool,
    bundle: str | None,
    overwrite: bool,
    adapter_type: AdapterType,
) -> None:
    """
    Perform sync operation without watch mode.

    This is extracted to avoid recursion when called from watch mode callback.

    Args:
        repo: Path to repository
        bidirectional: Enable bidirectional sync
        bundle: Project bundle name
        overwrite: Overwrite existing tool artifacts
        adapter_type: Adapter type to use
    """
    run_perform_sync_operation(repo, bidirectional, bundle, overwrite, adapter_type, console)


@beartype
@require(lambda repo: repo.exists(), "Repository path must exist")
@require(lambda repo: repo.is_dir(), "Repository path must be a directory")
@require(lambda adapter_instance: adapter_instance is not None, "Adapter instance must not be None")
@require(lambda bridge_config: bridge_config is not None, "Bridge config must not be None")
@require(lambda bridge_sync: bridge_sync is not None, "Bridge sync must not be None")
@require(lambda progress: progress is not None, "Progress must not be None")
@require(lambda task: task is None or (isinstance(task, int) and task >= 0), "Task must be None or non-negative int")
@ensure(lambda result: isinstance(result, tuple) and len(result) == 3, "Must return tuple of 3 elements")
@ensure(lambda result: isinstance(result[0], PlanBundle), "First element must be PlanBundle")
@ensure(lambda result: isinstance(result[1], int) and result[1] >= 0, "Second element must be non-negative int")
@ensure(lambda result: isinstance(result[2], int) and result[2] >= 0, "Third element must be non-negative int")
def _sync_tool_to_specfact(  # pyright: ignore[reportUnusedFunction]
    repo: Path,
    adapter_instance: Any,
    bridge_config: Any,
    bridge_sync: Any,
    progress: Any,
    task: int | None = None,
) -> tuple[PlanBundle, int, int]:
    """
    Sync tool artifacts to SpecFact format using adapter registry pattern.

    This is an adapter-agnostic replacement for _sync_speckit_to_specfact that uses
    the adapter registry instead of hard-coded converter/scanner instances.

    Args:
        repo: Repository path
        adapter_instance: Adapter instance from registry
        bridge_config: Bridge configuration
        bridge_sync: BridgeSync instance
        progress: Rich Progress instance
        task: Optional progress task ID to update

    Returns:
        Tuple of (merged_bundle, features_updated, features_added)
    """
    return run_sync_tool_to_specfact(repo, adapter_instance, bridge_config, bridge_sync, progress, task)


@app.command("bridge")
@beartype
@require(lambda repo: repo.exists(), "Repository path must exist")
@require(lambda repo: repo.is_dir(), "Repository path must be a directory")
@require(
    lambda bundle: bundle is None or (isinstance(bundle, str) and len(bundle) > 0),
    "Bundle must be None or non-empty str",
)
@require(lambda bidirectional: isinstance(bidirectional, bool), "Bidirectional must be bool")
@require(
    lambda mode: (
        mode is None
        or mode
        in ("read-only", "export-only", "import-annotation", "bidirectional", "unidirectional", "change-proposal")
    ),
    "Mode must be valid sync mode",
)
@require(lambda overwrite: isinstance(overwrite, bool), "Overwrite must be bool")
@require(
    lambda adapter: adapter is None or (isinstance(adapter, str) and len(adapter) > 0),
    "Adapter must be None or non-empty str",
)
@ensure(lambda result: result is None, "Must return None")
def sync_bridge(
    # Target/Input
    repo: Path = typer.Option(
        Path("."),
        "--repo",
        help="Path to repository",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    bundle: str | None = typer.Option(
        None,
        "--bundle",
        help="Project bundle name for SpecFact → tool conversion (default: auto-detect). Required for cross-adapter sync to preserve lossless content.",
    ),
    # Behavior/Options
    bidirectional: bool = typer.Option(
        False,
        "--bidirectional",
        help="Enable bidirectional sync (tool ↔ SpecFact)",
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Sync mode: 'read-only' (OpenSpec → SpecFact), 'export-only' (SpecFact → DevOps), 'bidirectional' (tool ↔ SpecFact), or 'change-proposal' (Spec-Kit feature → OpenSpec change). Default: bidirectional if --bidirectional, else unidirectional. For backlog adapters (github/ado), use 'export-only' with --bundle for cross-adapter sync.",
    ),
    feature: str | None = typer.Option(
        None,
        "--feature",
        help="Specific Spec-Kit feature directory to convert when using --mode change-proposal.",
    ),
    all_features: bool = typer.Option(
        False,
        "--all",
        help="Convert all untracked Spec-Kit features when using --mode change-proposal.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing tool artifacts (delete all existing before sync)",
    ),
    watch: bool = typer.Option(
        False,
        "--watch",
        help="Watch mode for continuous sync",
    ),
    ensure_compliance: bool = typer.Option(
        False,
        "--ensure-compliance",
        help="Validate and auto-enrich plan bundle for tool compliance before sync",
    ),
    # Advanced/Configuration
    adapter: str = typer.Option(
        "speckit",
        "--adapter",
        help="Adapter type: speckit, openspec, generic-markdown, github (available), ado (available), linear, jira, notion (future). Default: auto-detect. Use 'github' or 'ado' for backlog sync with cross-adapter capabilities (requires --bundle for lossless sync).",
        hidden=True,  # Hidden by default, shown with --help-advanced
    ),
    repo_owner: str | None = typer.Option(
        None,
        "--repo-owner",
        help="GitHub repository owner (for GitHub adapter). Required for GitHub backlog sync.",
        hidden=True,
    ),
    repo_name: str | None = typer.Option(
        None,
        "--repo-name",
        help="GitHub repository name (for GitHub adapter). Required for GitHub backlog sync.",
        hidden=True,
    ),
    external_base_path: Path | None = typer.Option(
        None,
        "--external-base-path",
        help="Base path for external tool repository (for cross-repo integrations, e.g., OpenSpec in different repo)",
        file_okay=False,
        dir_okay=True,
    ),
    github_token: str | None = typer.Option(
        None,
        "--github-token",
        help="GitHub API token (optional, uses GITHUB_TOKEN env var or gh CLI if not provided)",
        hidden=True,
    ),
    use_gh_cli: bool = typer.Option(
        True,
        "--use-gh-cli/--no-gh-cli",
        help="Use GitHub CLI (`gh auth token`) to get token automatically (default: True). Useful in enterprise environments where PAT creation is restricted.",
        hidden=True,
    ),
    ado_org: str | None = typer.Option(
        None,
        "--ado-org",
        help="Azure DevOps organization (for ADO adapter). Required for ADO backlog sync.",
        hidden=True,
    ),
    ado_project: str | None = typer.Option(
        None,
        "--ado-project",
        help="Azure DevOps project (for ADO adapter). Required for ADO backlog sync.",
        hidden=True,
    ),
    ado_base_url: str | None = typer.Option(
        None,
        "--ado-base-url",
        help="Azure DevOps base URL (for ADO adapter, defaults to https://dev.azure.com). Use for Azure DevOps Server (on-prem).",
        hidden=True,
    ),
    ado_token: str | None = typer.Option(
        None,
        "--ado-token",
        help="Azure DevOps PAT (optional, uses AZURE_DEVOPS_TOKEN env var if not provided). Requires Work Items (Read & Write) permissions.",
        hidden=True,
    ),
    ado_work_item_type: str | None = typer.Option(
        None,
        "--ado-work-item-type",
        help="Azure DevOps work item type (for ADO adapter, derived from process template if not provided). Examples: 'User Story', 'Product Backlog Item', 'Bug'.",
        hidden=True,
    ),
    sanitize: bool | None = typer.Option(
        None,
        "--sanitize/--no-sanitize",
        help="Sanitize proposal content for public issues (default: auto-detect based on repo setup). Removes competitive analysis, internal strategy, implementation details.",
        hidden=True,
    ),
    target_repo: str | None = typer.Option(
        None,
        "--target-repo",
        help="Target repository for issue creation (format: owner/repo). Default: same as code repository.",
        hidden=True,
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Interactive mode for AI-assisted sanitization (requires slash command).",
        hidden=True,
    ),
    change_ids: str | None = typer.Option(
        None,
        "--change-ids",
        help="Comma-separated list of change proposal IDs to export (default: all active proposals). Use with --bundle for cross-adapter export. Example: 'add-feature-x,update-api'. Find change IDs in import output or bundle directory.",
    ),
    backlog_ids: str | None = typer.Option(
        None,
        "--backlog-ids",
        help="Comma-separated list of backlog item IDs or URLs to import (GitHub/ADO). Use with --bundle to store lossless content for cross-adapter sync. Example: '123,456' or 'https://github.com/org/repo/issues/123'",
    ),
    backlog_ids_file: Path | None = typer.Option(
        None,
        "--backlog-ids-file",
        help="Path to file containing backlog item IDs/URLs (one per line or comma-separated).",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    export_to_tmp: bool = typer.Option(
        False,
        "--export-to-tmp",
        help="Export proposal content to temporary file for LLM review (default: <system-temp>/specfact-proposal-<change-id>.md).",
        hidden=True,
    ),
    import_from_tmp: bool = typer.Option(
        False,
        "--import-from-tmp",
        help="Import sanitized content from temporary file after LLM review (default: <system-temp>/specfact-proposal-<change-id>-sanitized.md).",
        hidden=True,
    ),
    tmp_file: Path | None = typer.Option(
        None,
        "--tmp-file",
        help="Custom temporary file path (default: <system-temp>/specfact-proposal-<change-id>.md).",
        hidden=True,
    ),
    update_existing: bool = typer.Option(
        False,
        "--update-existing/--no-update-existing",
        help="Update existing issue bodies when proposal content changes (default: False for safety). Uses content hash to detect changes.",
        hidden=True,
    ),
    track_code_changes: bool = typer.Option(
        False,
        "--track-code-changes/--no-track-code-changes",
        help="Detect code changes (git commits, file modifications) and add progress comments to existing issues (default: False).",
        hidden=True,
    ),
    add_progress_comment: bool = typer.Option(
        False,
        "--add-progress-comment/--no-add-progress-comment",
        help="Add manual progress comment to existing issues without code change detection (default: False).",
        hidden=True,
    ),
    code_repo: Path | None = typer.Option(
        None,
        "--code-repo",
        help="Path to source code repository for code change detection (default: same as --repo). Required when OpenSpec repository differs from source code repository.",
        hidden=True,
    ),
    include_archived: bool = typer.Option(
        False,
        "--include-archived/--no-include-archived",
        help="Include archived change proposals in sync (default: False). Useful for updating existing issues with new comment logic or branch detection improvements.",
        hidden=True,
    ),
    interval: int = typer.Option(
        5,
        "--interval",
        help="Watch interval in seconds (default: 5)",
        min=1,
        hidden=True,  # Hidden by default, shown with --help-advanced
    ),
) -> None:
    """
    Sync changes between external tool artifacts and SpecFact using bridge architecture.

    Synchronizes artifacts from external tools (Spec-Kit, OpenSpec, GitHub, ADO, Linear, Jira, etc.) with
    SpecFact project bundles using configurable bridge mappings.

    **Related**: Use `specfact backlog refine` to standardize backlog items with template-driven refinement
    before syncing to OpenSpec bundles. See backlog refinement guide for details.

    Supported adapters:

    - speckit: Spec-Kit projects (specs/, .specify/) - import & sync
    - generic-markdown: Generic markdown-based specifications - import & sync
    - openspec: OpenSpec integration (openspec/) - read-only sync (Phase 1)
    - github: GitHub Issues - bidirectional sync (import issues as change proposals, export proposals as issues)
    - ado: Azure DevOps Work Items - bidirectional sync (import work items as change proposals, export proposals as work items)
    - linear: Linear Issues (future) - planned
    - jira: Jira Issues (future) - planned
    - notion: Notion pages (future) - planned

    **Sync Modes:**

    - read-only: OpenSpec → SpecFact (read specs, no writes) - OpenSpec adapter only
    - bidirectional: Full two-way sync (tool ↔ SpecFact) - Spec-Kit, GitHub, and ADO adapters
      - GitHub: Import issues as change proposals, export proposals as issues
      - ADO: Import work items as change proposals, export proposals as work items
      - Spec-Kit: Full bidirectional sync of specs and plans
    - export-only: SpecFact → DevOps (create/update issues/work items, no import) - GitHub and ADO adapters
    - import-annotation: DevOps → SpecFact (import issues, annotate with findings) - future

    **🚀 Cross-Adapter Sync (Advanced Feature):**

    Enable lossless round-trip synchronization between different backlog adapters (GitHub ↔ ADO):
    - Use --bundle to preserve lossless content during cross-adapter syncs
    - Import from one adapter (e.g., GitHub) into a bundle, then export to another (e.g., ADO)
    - Content is preserved exactly as imported, enabling 100% fidelity migrations
    - Example: Import GitHub issue → bundle → export to ADO (no content loss)

    **Parameter Groups:**

    - **Target/Input**: --repo, --bundle
    - **Behavior/Options**: --bidirectional, --mode, --overwrite, --watch, --ensure-compliance
    - **Advanced/Configuration**: --adapter, --interval, --repo-owner, --repo-name, --github-token
    - **GitHub Options**: --repo-owner, --repo-name, --github-token, --use-gh-cli, --sanitize
    - **ADO Options**: --ado-org, --ado-project, --ado-base-url, --ado-token, --ado-work-item-type

    **Basic Examples:**

        specfact sync bridge --adapter speckit --repo . --bidirectional
        specfact sync bridge --adapter openspec --repo . --mode read-only  # OpenSpec → SpecFact (read-only)
        specfact sync bridge --adapter openspec --repo . --external-base-path ../other-repo  # Cross-repo OpenSpec
        specfact sync bridge --repo . --bidirectional  # Auto-detect adapter
        specfact sync bridge --repo . --watch --interval 10

    **GitHub Examples:**

        specfact sync bridge --adapter github --bidirectional --repo-owner owner --repo-name repo  # Bidirectional sync
        specfact sync bridge --adapter github --mode export-only --repo-owner owner --repo-name repo  # Export only
        specfact sync bridge --adapter github --update-existing  # Update existing issues when content changes
        specfact sync bridge --adapter github --track-code-changes  # Detect code changes and add progress comments
        specfact sync bridge --adapter github --add-progress-comment  # Add manual progress comment

    **Azure DevOps Examples:**

        specfact sync bridge --adapter ado --bidirectional --ado-org myorg --ado-project myproject  # Bidirectional sync
        specfact sync bridge --adapter ado --mode export-only --ado-org myorg --ado-project myproject  # Export only
        specfact sync bridge --adapter ado --mode export-only --ado-org myorg --ado-project myproject --bundle main  # Bundle export

    **Cross-Adapter Sync Examples:**

        # GitHub → ADO Migration (lossless round-trip)
        specfact sync bridge --adapter github --mode bidirectional --bundle migration --backlog-ids 123
        # Output shows: "✓ Imported GitHub issue #123 as change proposal: add-feature-x"
        specfact sync bridge --adapter ado --mode export-only --bundle migration --change-ids add-feature-x

        # Multi-Tool Workflow (public GitHub + internal ADO)
        specfact sync bridge --adapter github --mode export-only --sanitize  # Export to public GitHub
        specfact sync bridge --adapter github --mode bidirectional --bundle internal --backlog-ids 123  # Import to bundle
        specfact sync bridge --adapter ado --mode export-only --bundle internal --change-ids <change-id>  # Export to ADO

    **Finding Change IDs:**

    - Change IDs are shown in import output: "✓ Imported as change proposal: <change-id>"
    - Or check bundle directory: ls .specfact/projects/<bundle>/change_tracking/proposals/
    - Or check OpenSpec directory: ls openspec/changes/

    See docs/guides/devops-adapter-integration.md for complete documentation.
    """
    from specfact_project.sync_runtime.sync_bridge_command_impl import run_sync_bridge_command

    run_sync_bridge_command(
        repo=repo,
        bundle=bundle,
        bidirectional=bidirectional,
        mode=mode,
        feature=feature,
        all_features=all_features,
        overwrite=overwrite,
        watch=watch,
        ensure_compliance=ensure_compliance,
        adapter=adapter,
        repo_owner=repo_owner,
        repo_name=repo_name,
        external_base_path=external_base_path,
        github_token=github_token,
        use_gh_cli=use_gh_cli,
        ado_org=ado_org,
        ado_project=ado_project,
        ado_base_url=ado_base_url,
        ado_token=ado_token,
        ado_work_item_type=ado_work_item_type,
        sanitize=sanitize,
        target_repo=target_repo,
        interactive=interactive,
        change_ids=change_ids,
        backlog_ids=backlog_ids,
        backlog_ids_file=backlog_ids_file,
        export_to_tmp=export_to_tmp,
        import_from_tmp=import_from_tmp,
        tmp_file=tmp_file,
        update_existing=update_existing,
        track_code_changes=track_code_changes,
        add_progress_comment=add_progress_comment,
        code_repo=code_repo,
        include_archived=include_archived,
        interval=interval,
    )


@app.command("repository")
@beartype
@require(lambda repo: repo.exists(), "Repository path must exist")
@require(lambda repo: repo.is_dir(), "Repository path must be a directory")
@require(
    lambda target: target is None or (isinstance(target, Path) and target.exists()),
    "Target must be None or existing Path",
)
@require(lambda watch: isinstance(watch, bool), "Watch must be bool")
@require(lambda interval: isinstance(interval, int) and interval >= 1, "Interval must be int >= 1")
@require(
    lambda confidence: isinstance(confidence, float) and 0.0 <= confidence <= 1.0,
    "Confidence must be float in [0.0, 1.0]",
)
@ensure(lambda result: result is None, "Must return None")
def sync_repository(
    repo: Path = typer.Option(
        Path("."),
        "--repo",
        help="Path to repository",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    target: Path | None = typer.Option(
        None,
        "--target",
        help="Target directory for artifacts (default: .specfact)",
    ),
    watch: bool = typer.Option(
        False,
        "--watch",
        help="Watch mode for continuous sync",
    ),
    interval: int = typer.Option(
        5,
        "--interval",
        help="Watch interval in seconds (default: 5)",
        min=1,
        hidden=True,  # Hidden by default, shown with --help-advanced
    ),
    confidence: float = typer.Option(
        0.5,
        "--confidence",
        help="Minimum confidence threshold for feature detection (default: 0.5)",
        min=0.0,
        max=1.0,
        hidden=True,  # Hidden by default, shown with --help-advanced
    ),
) -> None:
    """
    Sync code changes to SpecFact artifacts.

    Monitors repository code changes, updates plan artifacts based on detected
    features/stories, and tracks deviations from manual plans.

    Example:
        specfact sync repository --repo . --confidence 0.5
    """
    if is_debug_mode():
        debug_log_operation(
            "command",
            "sync repository",
            "started",
            extra={"repo": str(repo), "target": str(target) if target else None, "watch": watch},
        )
        debug_print("[dim]sync repository: started[/dim]")

    from specfact_project.sync_runtime.repository_sync import RepositorySync

    telemetry_metadata = {
        "watch": watch,
        "interval": interval,
        "confidence": confidence,
    }

    with telemetry.track_command("sync.repository", telemetry_metadata) as record:
        from specfact_project.sync_runtime.sync_repository_impl import (
            make_repository_watch_callback,
            repository_run_specmatic_validation,
            repository_sync_run_once,
        )
        from specfact_project.sync_runtime.watcher import SyncWatcher

        console.print(f"[bold cyan]Syncing repository changes from:[/bold cyan] {repo}")

        resolved_repo = repo.resolve()
        if not resolved_repo.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {resolved_repo}")
            raise typer.Exit(1)
        if not resolved_repo.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {resolved_repo}")
            raise typer.Exit(1)

        if target is None:
            target = resolved_repo / ".specfact"

        sync = RepositorySync(resolved_repo, target, confidence_threshold=confidence)

        if watch:
            console.print("[bold cyan]Watch mode enabled[/bold cyan]")
            console.print(f"[dim]Watching for changes every {interval} seconds[/dim]\n")
            watcher = SyncWatcher(
                resolved_repo,
                make_repository_watch_callback(sync, resolved_repo, console),
                interval=interval,
            )
            watcher.watch()
            record({"watch_mode": True})
            return

        result = repository_sync_run_once(sync, resolved_repo, console)

        if is_debug_mode():
            debug_log_operation(
                "command",
                "sync repository",
                "success",
                extra={"code_changes": len(result.code_changes)},
            )
            debug_print("[dim]sync repository: success[/dim]")
        record(
            {
                "code_changes": len(result.code_changes),
                "plan_updates": len(result.plan_updates) if result.plan_updates else 0,
                "deviations": len(result.deviations) if result.deviations else 0,
            }
        )

        console.print(f"[bold cyan]Code Changes:[/bold cyan] {len(result.code_changes)}")
        if result.plan_updates:
            console.print(f"[bold cyan]Plan Updates:[/bold cyan] {len(result.plan_updates)}")
        if result.deviations:
            console.print(f"[yellow]⚠[/yellow] Found {len(result.deviations)} deviations from manual plan")
            console.print("[dim]Run 'specfact plan compare' for detailed deviation report[/dim]")
        else:
            console.print("[bold green]✓[/bold green] No deviations detected")
        console.print("[bold green]✓[/bold green] Repository sync complete!")

        repository_run_specmatic_validation(resolved_repo, console)


@app.command("intelligent")
@beartype
@require(
    lambda bundle: bundle is None or (isinstance(bundle, str) and len(bundle) > 0),
    "Bundle name must be None or non-empty string",
)
@require(lambda repo: isinstance(repo, Path), "Repository path must be Path")
@ensure(lambda result: result is None, "Must return None")
def sync_intelligent(
    # Target/Input
    bundle: str | None = typer.Argument(
        None, help="Project bundle name (e.g., legacy-api). Default: active plan from 'specfact plan select'"
    ),
    repo: Path = typer.Option(
        Path("."),
        "--repo",
        help="Path to repository. Default: current directory (.)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    # Behavior/Options
    watch: bool = typer.Option(
        False,
        "--watch",
        help="Watch mode for continuous sync. Default: False",
    ),
    code_to_spec: str = typer.Option(
        "auto",
        "--code-to-spec",
        help="Code-to-spec sync mode: 'auto' (AST-based) or 'off'. Default: auto",
    ),
    spec_to_code: str = typer.Option(
        "llm-prompt",
        "--spec-to-code",
        help="Spec-to-code sync mode: 'llm-prompt' (generate prompts) or 'off'. Default: llm-prompt",
    ),
    tests: str = typer.Option(
        "specmatic",
        "--tests",
        help="Test generation mode: 'specmatic' (contract-based) or 'off'. Default: specmatic",
    ),
) -> None:
    """
    Continuous intelligent bidirectional sync with conflict resolution.

    Detects changes via hashing and syncs intelligently:
    - Code→Spec: AST-based automatic sync (CLI can do)
    - Spec→Code: LLM prompt generation (CLI orchestrates, LLM writes)
    - Spec→Tests: Specmatic flows (contract-based, not LLM guessing)

    **Parameter Groups:**
    - **Target/Input**: bundle (required argument), --repo
    - **Behavior/Options**: --watch, --code-to-spec, --spec-to-code, --tests

    **Examples:**
        specfact sync intelligent legacy-api --repo .
        specfact sync intelligent my-bundle --repo . --watch
        specfact sync intelligent my-bundle --repo . --code-to-spec auto --spec-to-code llm-prompt --tests specmatic
    """
    if is_debug_mode():
        debug_log_operation(
            "command",
            "sync intelligent",
            "started",
            extra={"bundle": bundle, "repo": str(repo), "watch": watch},
        )
        debug_print("[dim]sync intelligent: started[/dim]")

    from specfact_cli.utils.structure import SpecFactStructure

    console = get_configured_console()

    # Use active plan as default if bundle not provided
    if bundle is None:
        bundle = SpecFactStructure.get_active_bundle_name(repo)
        if bundle is None:
            console.print("[bold red]✗[/bold red] Bundle name required")
            console.print("[yellow]→[/yellow] Use --bundle option or run 'specfact plan select' to set active plan")
            raise typer.Exit(1)
        console.print(f"[dim]Using active plan: {bundle}[/dim]")

    from specfact_cli.telemetry import telemetry
    from specfact_cli.utils.progress import load_bundle_with_progress
    from specfact_cli.utils.structure import SpecFactStructure

    from specfact_project.sync_runtime.change_detector import ChangeDetector
    from specfact_project.sync_runtime.code_to_spec import CodeToSpecSync
    from specfact_project.sync_runtime.spec_to_code import SpecToCodeSync
    from specfact_project.sync_runtime.spec_to_tests import SpecToTestsSync

    repo_path = repo.resolve()
    bundle_dir = SpecFactStructure.project_dir(base_path=repo_path, bundle_name=bundle)

    if not bundle_dir.exists():
        console.print(f"[bold red]✗[/bold red] Project bundle not found: {bundle_dir}")
        raise typer.Exit(1)

    telemetry_metadata = {
        "bundle": bundle,
        "watch": watch,
        "code_to_spec": code_to_spec,
        "spec_to_code": spec_to_code,
        "tests": tests,
    }

    with telemetry.track_command("sync.intelligent", telemetry_metadata) as record:
        console.print(f"[bold cyan]Intelligent Sync:[/bold cyan] {bundle}")
        console.print(f"[dim]Repository:[/dim] {repo_path}")

        # Load project bundle with unified progress display
        project_bundle = load_bundle_with_progress(bundle_dir, validate_hashes=False, console_instance=console)

        # Initialize sync components
        change_detector = ChangeDetector(bundle, repo_path)
        code_to_spec_sync = CodeToSpecSync(repo_path)
        spec_to_code_sync = SpecToCodeSync(repo_path)
        spec_to_tests_sync = SpecToTestsSync(bundle, repo_path)

        from specfact_project.sync_runtime.sync_intelligent_impl import make_intelligent_cycle_runner

        one_cycle = make_intelligent_cycle_runner(
            change_detector=change_detector,
            project_bundle=project_bundle,
            code_to_spec=code_to_spec,
            spec_to_code=spec_to_code,
            tests=tests,
            bundle=bundle,
            repo_path=repo_path,
            code_to_spec_sync=code_to_spec_sync,
            spec_to_code_sync=spec_to_code_sync,
            spec_to_tests_sync=spec_to_tests_sync,
            console=console,
        )

        if watch:
            console.print("[bold cyan]Watch mode enabled[/bold cyan]")
            console.print("[dim]Watching for changes...[/dim]")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

            from specfact_project.sync_runtime.watcher import SyncWatcher

            watcher = SyncWatcher(repo_path, lambda _c: one_cycle(), interval=5)
            try:
                watcher.watch()
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping watch mode...[/yellow]")
        else:
            one_cycle()

        if is_debug_mode():
            debug_log_operation("command", "sync intelligent", "success", extra={"bundle": bundle})
            debug_print("[dim]sync intelligent: success[/dim]")
        record({"sync_completed": True})
