"""
Implementation for commands._perform_sync_operation (cyclomatic complexity reduction).
"""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

import typer
from rich.progress import Progress, TaskID
from specfact_cli import runtime
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.models.bridge import AdapterType
from specfact_cli.models.plan import PlanBundle
from specfact_cli.utils.structure import SpecFactStructure
from specfact_cli.utils.terminal import get_progress_config

from specfact_project.sync_runtime.bridge_sync import BridgeSync
from specfact_project.sync_runtime.sync_tool_to_specfact_impl import run_sync_tool_to_specfact


def _pso_detect_adapter(repo: Path, adapter_type: AdapterType, console: Any) -> Any:
    adapter_instance = AdapterRegistry.get_adapter(adapter_type.value)
    if adapter_instance is None:
        console.print(f"[bold red]✗[/bold red] Adapter '{adapter_type.value}' not found in registry")
        console.print("[dim]Available adapters: " + ", ".join(AdapterRegistry.list_adapters()) + "[/dim]")
        raise typer.Exit(1)
    if not adapter_instance.detect(repo, None):
        console.print(f"[bold red]✗[/bold red] Not a {adapter_type.value} repository")
        console.print(f"[dim]Expected: {adapter_type.value} structure[/dim]")
        console.print("[dim]Tip: Use 'specfact sync bridge probe' to auto-detect tool configuration[/dim]")
        raise typer.Exit(1)
    console.print(f"[bold green]✓[/bold green] Detected {adapter_type.value} repository")
    return adapter_instance


def _pso_validate_constitution_required(
    repo: Path, adapter_type: AdapterType, adapter_instance: Any, bridge_config: Any, console: Any
) -> None:
    capabilities = adapter_instance.get_capabilities(repo, bridge_config)
    if adapter_type != AdapterType.SPECKIT:
        return
    if capabilities.has_custom_hooks:
        return
    console.print("[bold red]✗[/bold red] Constitution required")
    console.print("[red]Constitution file not found or is empty[/red]")
    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print("1. Run 'specfact sdd constitution bootstrap --repo .' to auto-generate constitution")
    console.print("2. Or run tool-specific constitution command in your AI assistant")
    console.print("3. Then run 'specfact sync bridge --adapter <adapter>' again")
    raise typer.Exit(1)


def _pso_maybe_bootstrap_constitution(repo: Path, adapter_type: AdapterType, console: Any) -> None:
    if adapter_type != AdapterType.SPECKIT:
        return
    constitution_path = repo / ".specify" / "memory" / "constitution.md"
    if not constitution_path.exists():
        return
    from specfact_cli.utils.bundle_converters import is_constitution_minimal

    if not is_constitution_minimal(constitution_path):
        console.print("[bold green]✓[/bold green] Constitution found and validated")
        return
    is_test_env = os.environ.get("TEST_MODE") == "true" or os.environ.get("PYTEST_CURRENT_TEST") is not None
    if is_test_env:
        from specfact_project.enrichers.constitution_enricher import ConstitutionEnricher

        enricher = ConstitutionEnricher()
        enriched_content = enricher.bootstrap(repo, constitution_path)
        constitution_path.write_text(enriched_content, encoding="utf-8")
        return
    if runtime.is_interactive():
        console.print("[yellow]⚠[/yellow] Constitution is minimal (essentially empty)")
        suggest_bootstrap = typer.confirm(
            "Generate bootstrap constitution from repository analysis?",
            default=True,
        )
        if suggest_bootstrap:
            from specfact_project.enrichers.constitution_enricher import ConstitutionEnricher

            console.print("[dim]Generating bootstrap constitution...[/dim]")
            enricher = ConstitutionEnricher()
            enriched_content = enricher.bootstrap(repo, constitution_path)
            constitution_path.write_text(enriched_content, encoding="utf-8")
            console.print("[bold green]✓[/bold green] Bootstrap constitution generated")
            console.print("[dim]Review and adjust as needed before syncing[/dim]")
        else:
            console.print("[dim]Skipping bootstrap. Run 'specfact sdd constitution bootstrap' manually if needed[/dim]")
        return
    console.print("[yellow]⚠[/yellow] Constitution is minimal (essentially empty)")
    console.print("[dim]Run 'specfact sdd constitution bootstrap --repo .' to generate constitution[/dim]")


def _pso_ensure_specfact(repo: Path, console: Any) -> bool:
    specfact_exists = (repo / SpecFactStructure.ROOT).exists()
    if not specfact_exists:
        console.print("[yellow]⚠[/yellow] SpecFact structure not found")
        console.print(f"[dim]Initialize with: specfact plan init --scaffold --repo {repo}[/dim]")
        SpecFactStructure.ensure_structure(repo)
        console.print("[bold green]✓[/bold green] Created SpecFact structure")
    else:
        console.print("[bold green]✓[/bold green] Detected SpecFact structure")
    return specfact_exists


def _pso_collect_features(
    adapter_instance: Any, repo: Path, bridge_config: Any, bridge_sync: BridgeSync
) -> list[dict[str, Any]]:
    if adapter_instance and hasattr(adapter_instance, "discover_features"):
        return adapter_instance.discover_features(repo, bridge_config)
    feature_ids = bridge_sync._discover_feature_ids()
    return [{"feature_key": fid} for fid in feature_ids]


def _pso_require_features_for_uni(
    bidirectional: bool, features: list[dict[str, Any]], adapter_type: AdapterType, console: Any
) -> None:
    if bidirectional or len(features) != 0:
        return
    console.print(f"[bold red]✗[/bold red] No {adapter_type.value} features found")
    console.print(
        f"[red]Unidirectional sync ({adapter_type.value} → SpecFact) requires at least one feature specification.[/red]"
    )
    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print(f"1. Create feature specifications in your {adapter_type.value} project")
    console.print(f"2. Then run 'specfact sync bridge --adapter {adapter_type.value}' again")
    console.print(
        f"\n[dim]Note: For bidirectional sync, {adapter_type.value} artifacts are optional if syncing from SpecFact → {adapter_type.value}[/dim]"
    )
    raise typer.Exit(1)


def _pso_merged_when_no_tool_features(
    repo: Path,
    adapter_type: AdapterType,
    adapter_instance: Any,
    bridge_config: Any,
    bridge_sync: BridgeSync,
    progress: Progress,
    task: TaskID,
) -> tuple[PlanBundle | None, int, int]:
    from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle
    from specfact_cli.utils.progress import load_bundle_with_progress
    from specfact_cli.validators.schema import validate_plan_bundle

    plan_path = SpecFactStructure.get_default_plan_path(repo)
    if not plan_path or not plan_path.exists():
        progress.update(task, description=f"[cyan]Creating plan bundle from {adapter_type.value}...[/cyan]")
        return run_sync_tool_to_specfact(repo, adapter_instance, bridge_config, bridge_sync, progress, task)[0], 0, 0

    progress.update(task, description="[cyan]Parsing plan bundle YAML...[/cyan]")
    loaded_plan_bundle: PlanBundle | None = None
    is_valid = False
    if plan_path.is_dir():
        project_bundle = load_bundle_with_progress(
            plan_path,
            validate_hashes=False,
            console_instance=progress.console if hasattr(progress, "console") else None,
        )
        loaded_plan_bundle = convert_project_bundle_to_plan_bundle(project_bundle)
        is_valid = True
    else:
        validation_result = validate_plan_bundle(plan_path)
        if isinstance(validation_result, tuple):
            is_valid, _error, loaded_plan_bundle = validation_result
        else:
            is_valid = False
            loaded_plan_bundle = None

    if is_valid and loaded_plan_bundle:
        progress.update(
            task,
            description=f"[cyan]Validating {len(loaded_plan_bundle.features)} features...[/cyan]",
        )
        progress.update(
            task,
            description=f"[green]✓[/green] Loaded plan bundle ({len(loaded_plan_bundle.features)} features)",
        )
        return loaded_plan_bundle, 0, 0

    progress.update(task, description=f"[cyan]Creating plan bundle from {adapter_type.value}...[/cyan]")
    return run_sync_tool_to_specfact(repo, adapter_instance, bridge_config, bridge_sync, progress, task)[0], 0, 0


def _pso_plan_from_named_bundle(bundle: str | None, repo: Path, progress: Progress, console: Any) -> PlanBundle | None:
    if not bundle:
        return None
    from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle
    from specfact_cli.utils.progress import load_bundle_with_progress

    bundle_dir = SpecFactStructure.project_dir(base_path=repo, bundle_name=bundle)
    if not bundle_dir.exists():
        return None
    project_bundle = load_bundle_with_progress(bundle_dir, validate_hashes=False, console_instance=console)
    return convert_project_bundle_to_plan_bundle(project_bundle)


def _pso_plan_from_default_path(repo: Path, progress: Progress, task: TaskID | None) -> PlanBundle | None:
    from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle
    from specfact_cli.utils.progress import load_bundle_with_progress
    from specfact_cli.validators.schema import validate_plan_bundle

    plan_path: Path | None = (
        SpecFactStructure.get_default_plan_path(repo) if hasattr(SpecFactStructure, "get_default_plan_path") else None
    )
    if not plan_path or not plan_path.exists():
        return None
    if task is not None:
        progress.update(task, description="[cyan]Loading plan bundle...[/cyan]")
    if plan_path.is_dir():
        project_bundle = load_bundle_with_progress(
            plan_path,
            validate_hashes=False,
            console_instance=progress.console if hasattr(progress, "console") else None,
        )
        plan_bundle = convert_project_bundle_to_plan_bundle(project_bundle)
        is_valid = True
    else:
        validation_result = validate_plan_bundle(plan_path)
        if isinstance(validation_result, tuple):
            is_valid, _error, plan_bundle = validation_result
        else:
            is_valid = False
            plan_bundle = None
    if is_valid and plan_bundle and len(plan_bundle.features) > 0:
        return plan_bundle
    return None


def _pso_resolve_plan_to_convert(
    merged_bundle: PlanBundle | None,
    bundle: str | None,
    repo: Path,
    progress: Progress,
    task: TaskID | None,
    console: Any,
) -> PlanBundle | None:
    if merged_bundle and len(merged_bundle.features) > 0:
        return merged_bundle
    from_bundle = _pso_plan_from_named_bundle(bundle, repo, progress, console)
    if from_bundle is not None:
        return from_bundle
    return _pso_plan_from_default_path(repo, progress, task)


def _pso_export_bundle_to_tool(
    plan_bundle_to_convert: PlanBundle,
    repo: Path,
    adapter_type: AdapterType,
    adapter_instance: Any,
    bridge_config: Any,
    overwrite: bool,
    progress: Progress,
    task: TaskID,
    console: Any,
) -> int:
    if overwrite:
        progress.update(task, description="[cyan]Removing existing artifacts...[/cyan]")
        specs_dir = repo / "specs"
        if specs_dir.exists():
            console.print(f"[yellow]⚠[/yellow] Overwrite mode: Removing existing {adapter_type.value} artifacts...")
            shutil.rmtree(specs_dir)
            specs_dir.mkdir(parents=True, exist_ok=True)
            console.print("[green]✓[/green] Existing artifacts removed")
    total_features = len(plan_bundle_to_convert.features)
    progress.update(
        task,
        description=f"[cyan]Converting plan bundle to {adapter_type.value} format (0 of {total_features})...[/cyan]",
    )

    def update_progress(current: int, total: int) -> None:
        progress.update(
            task,
            description=f"[cyan]Converting plan bundle to {adapter_type.value} format ({current} of {total})...[/cyan]",
        )

    if not adapter_instance or not hasattr(adapter_instance, "export_bundle"):
        msg = "Bundle export not available for this adapter"
        raise RuntimeError(msg)
    n = adapter_instance.export_bundle(plan_bundle_to_convert, repo, update_progress, bridge_config)
    progress.update(
        task,
        description=f"[green]✓[/green] Converted {n} features to {adapter_type.value}",
    )
    mode_text = "overwritten" if overwrite else "generated"
    console.print(f"[dim]  - {mode_text.capitalize()} spec.md, plan.md, tasks.md for {n} features[/dim]")
    console.print(
        "[yellow]⚠[/yellow] [dim]Note: Constitution Check gates in plan.md are set to PENDING - review and check gates based on your project's actual state[/dim]"
    )
    return n


def _pso_bidirectional_flow(
    repo: Path,
    bundle: str | None,
    overwrite: bool,
    adapter_type: AdapterType,
    adapter_instance: Any,
    bridge_config: Any,
    bridge_sync: BridgeSync,
    features: list[dict[str, Any]],
    progress: Progress,
    console: Any,
) -> tuple[int, int, int, list[dict[str, Any]]]:
    features_converted_speckit = 0
    conflicts: list[dict[str, Any]] = []
    merged_bundle: PlanBundle | None = None
    features_updated = 0
    features_added = 0

    if len(features) == 0:
        task = progress.add_task(f"[cyan]📝[/cyan] Converting {adapter_type.value} → SpecFact...", total=None)
        progress.update(
            task,
            description=f"[green]✓[/green] Skipped (no {adapter_type.value} features found)",
        )
        console.print(f"[dim]  - Skipped {adapter_type.value} → SpecFact (no features found)[/dim]")
        merged_bundle, features_updated, features_added = _pso_merged_when_no_tool_features(
            repo, adapter_type, adapter_instance, bridge_config, bridge_sync, progress, task
        )
    else:
        task = progress.add_task(f"[cyan]Converting {adapter_type.value} → SpecFact...[/cyan]", total=None)
        progress.update(task, description=f"[cyan]Converting {adapter_type.value} → SpecFact...[/cyan]")
        merged_bundle, features_updated, features_added = run_sync_tool_to_specfact(
            repo, adapter_instance, bridge_config, bridge_sync, progress
        )

    if merged_bundle:
        if features_updated > 0 or features_added > 0:
            progress.update(
                task,
                description=f"[green]✓[/green] Updated {features_updated}, Added {features_added} features",
            )
            console.print(f"[dim]  - Updated {features_updated} features[/dim]")
            console.print(f"[dim]  - Added {features_added} new features[/dim]")
        else:
            progress.update(
                task,
                description=f"[green]✓[/green] Created plan with {len(merged_bundle.features)} features",
            )

    task = progress.add_task(f"[cyan]Converting SpecFact → {adapter_type.value}...[/cyan]", total=None)
    progress.update(task, description="[cyan]Detecting SpecFact changes...[/cyan]")
    plan_bundle_to_convert = _pso_resolve_plan_to_convert(merged_bundle, bundle, repo, progress, task, console)

    if plan_bundle_to_convert and len(plan_bundle_to_convert.features) > 0:
        features_converted_speckit = _pso_export_bundle_to_tool(
            plan_bundle_to_convert,
            repo,
            adapter_type,
            adapter_instance,
            bridge_config,
            overwrite,
            progress,
            task,
            console,
        )
    else:
        progress.update(task, description=f"[green]✓[/green] No features to convert to {adapter_type.value}")

    if (
        adapter_instance
        and hasattr(adapter_instance, "detect_changes")
        and hasattr(adapter_instance, "detect_conflicts")
    ):
        changes_result = adapter_instance.detect_changes(repo, direction="both", bridge_config=bridge_config)
        speckit_changes = changes_result.get("speckit_changes", {})
        specfact_changes = changes_result.get("specfact_changes", {})
        conflicts = adapter_instance.detect_conflicts(speckit_changes, specfact_changes)
    if conflicts:
        console.print(f"[yellow]⚠[/yellow] Found {len(conflicts)} conflicts")
        console.print(
            f"[dim]Conflicts resolved using priority rules (SpecFact > {adapter_type.value} for artifacts)[/dim]"
        )
    else:
        console.print("[bold green]✓[/bold green] No conflicts detected")

    return features_updated, features_added, features_converted_speckit, conflicts


def _pso_unidirectional_flow(
    repo: Path,
    adapter_type: AdapterType,
    adapter_instance: Any,
    bridge_config: Any,
    bridge_sync: BridgeSync,
    features: list[dict[str, Any]],
    progress: Progress,
    console: Any,
) -> tuple[int, int, PlanBundle]:
    task = progress.add_task("[cyan]Converting to SpecFact format...[/cyan]", total=None)
    progress.update(task, description="[cyan]Converting to SpecFact format...[/cyan]")
    merged_bundle, features_updated, features_added = run_sync_tool_to_specfact(
        repo, adapter_instance, bridge_config, bridge_sync, progress
    )
    if features_updated > 0 or features_added > 0:
        task = progress.add_task("[cyan]🔀[/cyan] Merging with existing plan...", total=None)
        progress.update(
            task,
            description=f"[green]✓[/green] Updated {features_updated} features, Added {features_added} features",
        )
        console.print(f"[dim]  - Updated {features_updated} features[/dim]")
        console.print(f"[dim]  - Added {features_added} new features[/dim]")
    elif merged_bundle:
        progress.update(task, description=f"[green]✓[/green] Created plan with {len(merged_bundle.features)} features")
        console.print(f"[dim]Created plan with {len(merged_bundle.features)} features[/dim]")
    console.print()
    if features:
        console.print("[bold cyan]Features synced:[/bold cyan]")
        for feature in features:
            feature_key = feature.get("feature_key", "UNKNOWN")
            feature_title = feature.get("title", "Unknown Feature")
            console.print(f"  - [cyan]{feature_key}[/cyan]: {feature_title}")
    return features_updated, features_added, merged_bundle


def _pso_print_summary(
    bidirectional: bool,
    adapter_type: AdapterType,
    features: list[dict[str, Any]],
    features_updated: int,
    features_added: int,
    features_converted_speckit: int,
    conflicts: list[dict[str, Any]],
    console: Any,
) -> None:
    console.print()
    if bidirectional:
        console.print("[bold cyan]Sync Summary (Bidirectional):[/bold cyan]")
        console.print(
            f"  - {adapter_type.value} → SpecFact: Updated {features_updated}, Added {features_added} features"
        )
        if features_converted_speckit > 0:
            console.print(
                f"  - SpecFact → {adapter_type.value}: {features_converted_speckit} features converted to {adapter_type.value} format"
            )
        else:
            console.print(f"  - SpecFact → {adapter_type.value}: No features to convert")
        if conflicts:
            console.print(f"  - Conflicts: {len(conflicts)} detected and resolved")
        else:
            console.print("  - Conflicts: None detected")
        if features_converted_speckit > 0:
            console.print()
            console.print("[bold cyan]Next Steps:[/bold cyan]")
            console.print(f"  Validate {adapter_type.value} artifact consistency and quality")
            console.print("  This will check for ambiguities, duplications, and constitution alignment")
        return
    console.print("[bold cyan]Sync Summary (Unidirectional):[/bold cyan]")
    if features:
        console.print(f"  - Features synced: {len(features)}")
    if features_updated > 0 or features_added > 0:
        console.print(f"  - Updated: {features_updated} features")
        console.print(f"  - Added: {features_added} new features")
    console.print(f"  - Direction: {adapter_type.value} → SpecFact")
    console.print()
    console.print("[bold cyan]Next Steps:[/bold cyan]")
    console.print(f"  Validate {adapter_type.value} artifact consistency and quality")
    console.print("  This will check for ambiguities, duplications, and constitution alignment")


def _pso_run_specmatic_tail(repo: Path, console: Any) -> None:
    from specfact_cli.integrations.specmatic import check_specmatic_available, validate_spec_with_specmatic

    spec_files = []
    for pattern in [
        "**/openapi.yaml",
        "**/openapi.yml",
        "**/openapi.json",
        "**/asyncapi.yaml",
        "**/asyncapi.yml",
        "**/asyncapi.json",
    ]:
        spec_files.extend(repo.glob(pattern))
    if not spec_files:
        return
    console.print(f"\n[cyan]🔍 Found {len(spec_files)} API specification file(s)[/cyan]")
    is_available, error_msg = check_specmatic_available()
    if not is_available:
        console.print(f"[dim]💡 Tip: Install Specmatic to validate API specs: {error_msg}[/dim]")
        return
    for spec_file in spec_files[:3]:
        console.print(f"[dim]Validating {spec_file.relative_to(repo)} with Specmatic...[/dim]")
        try:
            result = asyncio.run(validate_spec_with_specmatic(spec_file))
            if result.is_valid:
                console.print(f"  [green]✓[/green] {spec_file.name} is valid")
            else:
                console.print(f"  [yellow]⚠[/yellow] {spec_file.name} has validation issues")
                if result.errors:
                    for error in result.errors[:2]:
                        console.print(f"    - {error}")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Validation error: {e!s}")
    if len(spec_files) > 3:
        console.print(
            f"[dim]... and {len(spec_files) - 3} more spec file(s) (run 'specfact spec validate' to validate all)[/dim]"
        )


def run_perform_sync_operation(
    repo: Path,
    bidirectional: bool,
    bundle: str | None,
    overwrite: bool,
    adapter_type: AdapterType,
    console: Any,
) -> None:
    adapter_instance = _pso_detect_adapter(repo, adapter_type, console)
    bridge_config = adapter_instance.generate_bridge_config(repo)
    _pso_validate_constitution_required(repo, adapter_type, adapter_instance, bridge_config, console)
    _pso_maybe_bootstrap_constitution(repo, adapter_type, console)
    _pso_ensure_specfact(repo, console)
    bridge_sync = BridgeSync(repo, bridge_config=bridge_config)

    progress_columns, progress_kwargs = get_progress_config()
    with Progress(*progress_columns, console=console, **progress_kwargs) as progress:
        task = progress.add_task(f"[cyan]Scanning {adapter_type.value} artifacts...[/cyan]", total=None)
        progress.update(task, description=f"[cyan]Scanning {adapter_type.value} artifacts...[/cyan]")
        features = _pso_collect_features(adapter_instance, repo, bridge_config, bridge_sync)
        progress.update(task, description=f"[green]✓[/green] Found {len(features)} features")
        _pso_require_features_for_uni(bidirectional, features, adapter_type, console)

        features_updated = 0
        features_added = 0
        features_converted_speckit = 0
        conflicts: list[dict[str, Any]] = []

        if bidirectional:
            features_updated, features_added, features_converted_speckit, conflicts = _pso_bidirectional_flow(
                repo,
                bundle,
                overwrite,
                adapter_type,
                adapter_instance,
                bridge_config,
                bridge_sync,
                features,
                progress,
                console,
            )
        else:
            features_updated, features_added, _mb = _pso_unidirectional_flow(
                repo, adapter_type, adapter_instance, bridge_config, bridge_sync, features, progress, console
            )

        _pso_print_summary(
            bidirectional,
            adapter_type,
            features,
            features_updated,
            features_added,
            features_converted_speckit,
            conflicts,
            console,
        )

    console.print()
    console.print("[bold green]✓[/bold green] Sync complete!")
    _pso_run_specmatic_tail(repo, console)
