"""Helpers for BridgeSync.generate_alignment_report (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.progress import Progress
from rich.table import Table
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.models.bridge import BridgeConfig
from specfact_cli.runtime import get_configured_console
from specfact_cli.utils.bundle_loader import load_project_bundle
from specfact_cli.utils.terminal import get_progress_config


console = get_configured_console()


def _alignment_collect_ids(
    adapter: Any,
    base_path: Path,
    bridge_config: BridgeConfig,
    bundle_dir: Path,
) -> tuple[set[str], set[str], float]:
    progress_columns, progress_kwargs = get_progress_config()
    with Progress(*progress_columns, console=console, **progress_kwargs) as progress:
        task = progress.add_task("Generating alignment report...", total=None)
        project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)
        external_features = adapter.discover_features(base_path, bridge_config)
        external_feature_ids: set[str] = set()
        for feature in external_features:
            feature_key = feature.get("feature_key") or feature.get("key", "")
            if feature_key:
                external_feature_ids.add(feature_key)
        specfact_feature_ids: set[str] = set(project_bundle.features.keys()) if project_bundle.features else set()
        aligned = specfact_feature_ids & external_feature_ids
        total_specs = len(external_feature_ids) if external_feature_ids else 1
        coverage = (len(aligned) / total_specs * 100) if total_specs > 0 else 0.0
        progress.update(task, completed=1)
    return external_feature_ids, specfact_feature_ids, coverage


def _alignment_print_gap_table(title: str, feature_ids: set[str]) -> None:
    gaps_table = Table(show_header=True, header_style="bold yellow")
    gaps_table.add_column("Feature ID", style="cyan")
    for feature_id in sorted(feature_ids):
        gaps_table.add_row(feature_id)
    console.print(title)
    console.print(gaps_table)


def alignment_report_render_console(
    *,
    adapter_name: str,
    external_feature_ids: set[str],
    specfact_feature_ids: set[str],
    gaps_in_specfact: set[str],
    gaps_in_external: set[str],
    coverage: float,
) -> None:
    aligned = specfact_feature_ids & external_feature_ids
    console.print(f"\n[bold]Alignment Report: SpecFact vs {adapter_name}[/bold]\n")
    summary_table = Table(title="Alignment Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green", justify="right")
    summary_table.add_row(f"{adapter_name} Specs", str(len(external_feature_ids)))
    summary_table.add_row("SpecFact Features", str(len(specfact_feature_ids)))
    summary_table.add_row("Aligned", str(len(aligned)))
    summary_table.add_row("Gaps in SpecFact", str(len(gaps_in_specfact)))
    summary_table.add_row(f"Gaps in {adapter_name}", str(len(gaps_in_external)))
    summary_table.add_row("Coverage", f"{coverage:.1f}%")
    console.print(summary_table)
    if gaps_in_specfact:
        _alignment_print_gap_table(
            f"\n[bold yellow]⚠ Gaps in SpecFact ({adapter_name} specs not extracted):[/bold yellow]",
            gaps_in_specfact,
        )
    if gaps_in_external:
        _alignment_print_gap_table(
            f"\n[bold yellow]⚠ Gaps in {adapter_name} (SpecFact features not in {adapter_name}):[/bold yellow]",
            gaps_in_external,
        )


def alignment_report_write_file(
    output_file: Path,
    adapter_name: str,
    external_feature_ids: set[str],
    specfact_feature_ids: set[str],
    gaps_in_specfact: set[str],
    gaps_in_external: set[str],
    coverage: float,
) -> None:
    aligned = specfact_feature_ids & external_feature_ids
    report_content = f"""# Alignment Report: SpecFact vs {adapter_name}

## Summary
- {adapter_name} Specs: {len(external_feature_ids)}
- SpecFact Features: {len(specfact_feature_ids)}
- Aligned: {len(aligned)}
- Coverage: {coverage:.1f}%

## Gaps in SpecFact
{chr(10).join(f"- {fid}" for fid in sorted(gaps_in_specfact)) if gaps_in_specfact else "None"}

## Gaps in {adapter_name}
{chr(10).join(f"- {fid}" for fid in sorted(gaps_in_external)) if gaps_in_external else "None"}
"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report_content, encoding="utf-8")
    console.print(f"\n[bold green]✓[/bold green] Report saved to {output_file}")


def run_generate_alignment_report(
    repo_path: Path,
    bridge_config: BridgeConfig | None,
    bundle_name: str,
    output_file: Path | None,
) -> None:
    """Core logic for BridgeSync.generate_alignment_report."""
    from specfact_cli.utils.structure import SpecFactStructure

    if not bridge_config:
        console.print("[yellow]⚠[/yellow] Bridge config not available for alignment report")
        return
    adapter = AdapterRegistry.get_adapter(bridge_config.adapter.value)
    if not adapter:
        console.print(f"[yellow]⚠[/yellow] Adapter '{bridge_config.adapter.value}' not found for alignment report")
        return
    bundle_dir = repo_path / SpecFactStructure.PROJECTS / bundle_name
    if not bundle_dir.exists():
        console.print(f"[bold red]✗[/bold red] Project bundle not found: {bundle_dir}")
        return
    base_path = bridge_config.external_base_path if bridge_config.external_base_path else repo_path
    external_feature_ids, specfact_feature_ids, coverage = _alignment_collect_ids(
        adapter, base_path, bridge_config, bundle_dir
    )
    gaps_in_specfact = external_feature_ids - specfact_feature_ids
    gaps_in_external = specfact_feature_ids - external_feature_ids
    adapter_name = bridge_config.adapter.value.upper()
    alignment_report_render_console(
        adapter_name=adapter_name,
        external_feature_ids=external_feature_ids,
        specfact_feature_ids=specfact_feature_ids,
        gaps_in_specfact=gaps_in_specfact,
        gaps_in_external=gaps_in_external,
        coverage=coverage,
    )
    if output_file:
        alignment_report_write_file(
            output_file,
            adapter_name,
            external_feature_ids,
            specfact_feature_ids,
            gaps_in_specfact,
            gaps_in_external,
            coverage,
        )
