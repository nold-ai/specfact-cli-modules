"""Delta analysis subcommands for backlog-core."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from beartype import beartype
from rich.console import Console
from rich.table import Table
from specfact_cli.adapters.registry import AdapterRegistry

from specfact_backlog.backlog_core.adapters.backlog_protocol import require_backlog_graph_protocol
from specfact_backlog.backlog_core.analyzers.dependency import DependencyAnalyzer
from specfact_backlog.backlog_core.commands.sync import compute_delta
from specfact_backlog.backlog_core.graph.builder import BacklogGraphBuilder
from specfact_backlog.backlog_core.graph.models import BacklogGraph
from specfact_backlog.backlog_core.utils import print_info, print_success, print_warning


console = Console()
delta_app = typer.Typer(name="delta", help="Backlog delta analysis and impact tracking")


@beartype
def _load_baseline_graph(baseline_file: Path) -> BacklogGraph:
    if not baseline_file.exists():
        return BacklogGraph(provider="unknown", project_key="unknown")
    return BacklogGraph.from_json(baseline_file.read_text(encoding="utf-8"))


@beartype
def _fetch_current_graph(project_id: str, adapter: str, template: str) -> BacklogGraph:
    adapter_instance = AdapterRegistry.get_adapter(adapter)
    graph_adapter = require_backlog_graph_protocol(adapter_instance)
    items = graph_adapter.fetch_all_issues(project_id)
    relationships = graph_adapter.fetch_relationships(project_id)
    return (
        BacklogGraphBuilder(provider=adapter, template_name=template, custom_config={"project_key": project_id})
        .add_items(items)
        .add_dependencies(relationships)
        .build()
    )


@beartype
def _empty_delta() -> dict[str, Any]:
    return {
        "added_items": [],
        "removed_items": [],
        "updated_items": [],
        "status_transitions": [],
        "new_dependencies": [],
        "removed_dependencies": [],
    }


def _load_provider_config(adapter: str) -> dict[str, Any]:
    config_path = Path(".specfact") / "backlog-config.yaml"
    if not config_path.exists():
        return {}
    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    providers = loaded.get("providers")
    if isinstance(providers, dict) and isinstance(providers.get(adapter), dict):
        return dict(providers[adapter])
    direct = loaded.get(adapter)
    if isinstance(direct, dict):
        return dict(direct)
    return {}


def _resolve_project_id(
    *,
    adapter: str,
    project_id: str | None,
    repo_owner: str | None,
    repo_name: str | None,
) -> str | None:
    provider_config = _load_provider_config(adapter)
    configured_project = provider_config.get("project_id")
    if project_id:
        return project_id
    if isinstance(configured_project, str) and configured_project.strip():
        return configured_project.strip()
    owner = repo_owner or provider_config.get("repo_owner")
    name = repo_name or provider_config.get("repo_name")
    if adapter == "github" and isinstance(owner, str) and isinstance(name, str) and owner and name:
        return f"{owner}/{name}"
    return None


def _exit_missing_delta_context(ctx: typer.Context) -> None:
    typer.echo(ctx.get_help())
    typer.echo(
        "\nError: Missing backlog context. Provide --project-id, or for GitHub provide "
        "--repo-owner and --repo-name, or configure .specfact/backlog-config.yaml."
    )
    raise typer.Exit(2)


@beartype
def _render_delta_table(delta: dict[str, Any], title: str = "Delta Status") -> None:
    table = Table(title=title)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    table.add_row("Added items", str(len(delta["added_items"])))
    table.add_row("Updated items", str(len(delta["updated_items"])))
    table.add_row("Removed items", str(len(delta["removed_items"])))
    table.add_row("Status transitions", str(len(delta["status_transitions"])))
    table.add_row("New dependencies", str(len(delta["new_dependencies"])))
    table.add_row("Removed dependencies", str(len(delta["removed_dependencies"])))
    console.print(table)


def status(
    ctx: typer.Context,
    adapter_arg: Annotated[str | None, typer.Argument(help="Adapter to use")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id", help="Backlog project identifier")] = None,
    adapter: Annotated[str, typer.Option("--adapter", help="Adapter to use")] = "github",
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="GitHub repository owner")] = None,
    repo_name: Annotated[str | None, typer.Option("--repo-name", help="GitHub repository name")] = None,
    since: Annotated[str | None, typer.Option("--since", help="ISO timestamp filter")] = None,
    baseline_file: Annotated[Path, typer.Option("--baseline-file", help="Path to baseline graph JSON")] = Path(
        ".specfact/backlog-baseline.json"
    ),
    template: Annotated[str, typer.Option("--template", help="Template name for mapping")] = "github_projects",
) -> None:
    """Show backlog delta status compared to baseline."""
    effective_adapter = adapter_arg or adapter
    effective_project_id = _resolve_project_id(
        adapter=effective_adapter,
        project_id=project_id,
        repo_owner=repo_owner,
        repo_name=repo_name,
    )
    if not effective_project_id:
        _exit_missing_delta_context(ctx)
    assert effective_project_id is not None
    baseline_graph = _load_baseline_graph(baseline_file)
    current_graph = _fetch_current_graph(effective_project_id, effective_adapter, template)
    delta = compute_delta(baseline_graph, current_graph)

    if since is not None:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid --since timestamp: {since}") from exc
        if current_graph.fetched_at.replace(tzinfo=None) <= since_dt.replace(tzinfo=None):
            print_warning("No changes after --since timestamp.")
            delta = _empty_delta()

    _render_delta_table(delta, title="Backlog Delta Status")


@beartype
def impact(
    item_id: Annotated[str, typer.Argument(help="Item id to inspect")],
    project_id: Annotated[str, typer.Option("--project-id", help="Backlog project identifier")],
    adapter: Annotated[str, typer.Option("--adapter", help="Adapter to use")] = "github",
    template: Annotated[str, typer.Option("--template", help="Template name for mapping")] = "github_projects",
) -> None:
    """Show downstream dependency impact for an item."""
    graph = _fetch_current_graph(project_id, adapter, template)
    analyzer = DependencyAnalyzer(graph)
    if item_id not in graph.items:
        print_warning(f"Item '{item_id}' not found in graph.")
        raise typer.Exit(code=1)
    result = analyzer.impact_analysis(item_id)
    print_info(f"Direct dependents: {', '.join(result['direct_dependents']) or '(none)'}")
    print_info(f"Transitive dependents: {', '.join(result['transitive_dependents']) or '(none)'}")
    print_success(f"Estimated impact count: {result['estimated_impact_count']}")


@beartype
def cost_estimate(
    project_id: Annotated[str, typer.Option("--project-id", help="Backlog project identifier")],
    adapter: Annotated[str, typer.Option("--adapter", help="Adapter to use")] = "github",
    baseline_file: Annotated[Path, typer.Option("--baseline-file", help="Path to baseline graph JSON")] = Path(
        ".specfact/backlog-baseline.json"
    ),
    template: Annotated[str, typer.Option("--template", help="Template name for mapping")] = "github_projects",
) -> None:
    """Estimate effort based on detected delta volume."""
    baseline_graph = _load_baseline_graph(baseline_file)
    current_graph = _fetch_current_graph(project_id, adapter, template)
    delta = compute_delta(baseline_graph, current_graph)

    points = (
        len(delta["added_items"]) * 3
        + len(delta["updated_items"]) * 2
        + len(delta["removed_items"])
        + len(delta["new_dependencies"])
    )
    print_success(f"Estimated delta effort points: {points}")


@beartype
def rollback_analysis(
    project_id: Annotated[str, typer.Option("--project-id", help="Backlog project identifier")],
    adapter: Annotated[str, typer.Option("--adapter", help="Adapter to use")] = "github",
    baseline_file: Annotated[Path, typer.Option("--baseline-file", help="Path to baseline graph JSON")] = Path(
        ".specfact/backlog-baseline.json"
    ),
    template: Annotated[str, typer.Option("--template", help="Template name for mapping")] = "github_projects",
) -> None:
    """Analyze rollback exposure from current delta."""
    baseline_graph = _load_baseline_graph(baseline_file)
    current_graph = _fetch_current_graph(project_id, adapter, template)
    delta = compute_delta(baseline_graph, current_graph)

    high_risk = len(delta["removed_items"]) > 0 or len(delta["removed_dependencies"]) > 0
    risk = "HIGH" if high_risk else "LOW"
    print_info(f"Rollback risk: {risk}")
    _render_delta_table(delta, title="Rollback Impact")


delta_app.command("status")(status)
delta_app.command("impact")(impact)
delta_app.command("cost-estimate")(cost_estimate)
delta_app.command("rollback-analysis")(rollback_analysis)
