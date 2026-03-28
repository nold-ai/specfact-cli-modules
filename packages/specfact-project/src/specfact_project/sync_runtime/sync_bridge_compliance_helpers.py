"""Plan bundle compliance checks for sync bridge (cyclomatic complexity reduction)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specfact_cli.models.bridge import AdapterType
from specfact_cli.runtime import get_configured_console
from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle
from specfact_cli.utils.progress import load_bundle_with_progress
from specfact_cli.utils.structure import SpecFactStructure
from specfact_cli.validators.schema import validate_plan_bundle


console = get_configured_console()


def _load_plan_bundle_from_bundle_dir(repo: Path, bundle: str) -> Any | None:
    bundle_dir = SpecFactStructure.project_dir(base_path=repo, bundle_name=bundle)
    if not bundle_dir.exists():
        console.print(f"[yellow]⚠ Bundle '{bundle}' not found, skipping compliance check[/yellow]")
        return None
    project_bundle = load_bundle_with_progress(bundle_dir, validate_hashes=False, console_instance=console)
    return convert_project_bundle_to_plan_bundle(project_bundle)


def _load_plan_bundle_from_default_path(repo: Path) -> Any | None:
    if not hasattr(SpecFactStructure, "get_default_plan_path"):
        return None
    plan_path = SpecFactStructure.get_default_plan_path(repo)
    if not plan_path or not plan_path.exists():
        return None
    if plan_path.is_dir():
        project_bundle = load_bundle_with_progress(plan_path, validate_hashes=False, console_instance=console)
        return convert_project_bundle_to_plan_bundle(project_bundle)
    validation_result = validate_plan_bundle(plan_path)
    if isinstance(validation_result, tuple):
        is_valid, _error, plan_bundle = validation_result
        return plan_bundle if is_valid else None
    return None


def load_plan_bundle_for_compliance(repo: Path, bundle: str | None) -> Any | None:
    if bundle:
        return _load_plan_bundle_from_bundle_dir(repo, bundle)
    return _load_plan_bundle_from_default_path(repo)


def _compliance_warn_tech_stack(plan_bundle: Any) -> None:
    has_tech_stack = bool(
        plan_bundle.idea
        and plan_bundle.idea.constraints
        and any(
            "Python" in c or "framework" in c.lower() or "database" in c.lower() for c in plan_bundle.idea.constraints
        )
    )
    if not has_tech_stack:
        console.print("[yellow]⚠ Technology stack not found in constraints[/yellow]")
        console.print("[dim]Technology stack will be extracted from constraints during sync[/dim]")


def _compliance_warn_non_testable_stories(plan_bundle: Any) -> None:
    features_with_non_testable: list[tuple[str, str]] = []
    keywords = ("must", "should", "verify", "validate", "ensure")
    for plan_feature in plan_bundle.features:
        for story in plan_feature.stories:
            testable_count = sum(1 for acc in story.acceptance if any(keyword in acc.lower() for keyword in keywords))
            if testable_count < len(story.acceptance) and len(story.acceptance) > 0:
                features_with_non_testable.append((plan_feature.key, story.key))
    if not features_with_non_testable:
        return
    console.print(
        f"[yellow]⚠ Found {len(features_with_non_testable)} stories with non-testable acceptance criteria[/yellow]"
    )
    console.print("[dim]Acceptance criteria will be enhanced during sync[/dim]")


def run_bridge_compliance_section(
    *,
    ensure_compliance: bool,
    bundle: str | None,
    repo: Path,
    adapter_type: AdapterType | None,
    adapter_value: str,
) -> None:
    if not ensure_compliance:
        return
    adapter_display = adapter_type.value if adapter_type else adapter_value
    console.print(f"\n[cyan]🔍 Validating plan bundle for {adapter_display} compliance...[/cyan]")
    plan_bundle = load_plan_bundle_for_compliance(repo, bundle)
    if not plan_bundle:
        console.print("[yellow]⚠ Plan bundle not found, skipping compliance check[/yellow]")
        return
    _compliance_warn_tech_stack(plan_bundle)
    _compliance_warn_non_testable_stories(plan_bundle)
    console.print("[green]✓ Plan bundle validation complete[/green]")
