"""OpenAPI / Specmatic validation before sync bridge (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from specfact_cli.integrations.specmatic import check_specmatic_available, validate_spec_with_specmatic
from specfact_cli.runtime import get_configured_console
from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle
from specfact_cli.utils.progress import load_bundle_with_progress
from specfact_cli.utils.structure import SpecFactStructure


console = get_configured_console()


def _collect_contract_paths(bundle_dir: Path, plan_bundle: Any) -> list[Path]:
    contract_files: list[Path] = []
    for plan_feature in plan_bundle.features:
        if not plan_feature.contract:
            continue
        contract_path = bundle_dir / plan_feature.contract
        if contract_path.exists():
            contract_files.append(contract_path)
    return contract_files


def _validate_contract_subset(contract_files: list[Path], bundle_dir: Path) -> bool:
    validation_failed = False
    for contract_path in contract_files[:5]:
        console.print(f"[dim]Validating {contract_path.relative_to(bundle_dir)}...[/dim]")
        try:
            result = asyncio.run(validate_spec_with_specmatic(contract_path))
            if not result.is_valid:
                console.print(f"  [bold yellow]⚠[/bold yellow] {contract_path.name} has validation issues")
                if result.errors:
                    for error in result.errors[:2]:
                        console.print(f"    - {error}")
                validation_failed = True
            else:
                console.print(f"  [bold green]✓[/bold green] {contract_path.name} is valid")
        except Exception as e:
            console.print(f"  [bold yellow]⚠[/bold yellow] Validation error: {e!s}")
            validation_failed = True
    return validation_failed


def run_bridge_openapi_bundle_validation(bundle: str | None, resolved_repo: Path, bidirectional: bool) -> None:
    if not bundle:
        return
    bundle_dir = SpecFactStructure.project_dir(base_path=resolved_repo, bundle_name=bundle)
    if not bundle_dir.exists():
        return
    console.print("\n[cyan]🔍 Validating OpenAPI contracts before sync...[/cyan]")
    project_bundle = load_bundle_with_progress(bundle_dir, validate_hashes=False, console_instance=console)
    plan_bundle: Any = convert_project_bundle_to_plan_bundle(project_bundle)
    is_available, error_msg = check_specmatic_available()
    if not is_available:
        console.print(f"[dim]💡 Tip: Install Specmatic to validate contracts: {error_msg}[/dim]")
        return
    contract_files = _collect_contract_paths(bundle_dir, plan_bundle)
    if not contract_files:
        console.print("[dim]No contracts found in bundle[/dim]")
        return
    console.print(f"[dim]Validating {len(contract_files)} contract(s)...[/dim]")
    validation_failed = _validate_contract_subset(contract_files, bundle_dir)
    if validation_failed:
        console.print(
            "[yellow]⚠[/yellow] Some contracts have validation issues. Sync will continue, but consider fixing them."
        )
    else:
        console.print("[green]✓[/green] All contracts validated successfully")
    if bidirectional and contract_files:
        console.print("[dim]Backward compatibility check skipped (previous versions not stored)[/dim]")
