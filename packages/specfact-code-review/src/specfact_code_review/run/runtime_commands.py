"""Customer-facing inspection and preparation of portable Python runtimes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from icontract import require

from specfact_code_review.run import native_backend
from specfact_code_review.run.runtime_builder import prepare_runtime
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_interpreter import select_environment
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


app = typer.Typer(help="Inspect and prepare an isolated runtime for this Python project.", no_args_is_help=True)


@app.command("inspect")
@require(lambda project_config: project_config is None or isinstance(project_config, Path))
def inspect_runtime(
    project_config: Annotated[Path | None, typer.Option("--project-config")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Discover dependencies and configuration without installing or executing code."""
    try:
        plan = discover_project(Path.cwd(), config_path=project_config)
    except ProjectRuntimeError as exc:
        if json_output:
            typer.echo(
                json.dumps(
                    {
                        "status": "incomplete",
                        "diagnostic": exc.diagnostic,
                        "message": str(exc),
                        "candidates": list(exc.candidates),
                        "required_fields": list(exc.required_fields),
                    },
                    indent=2,
                )
            )
            raise typer.Exit(code=2) from exc
        raise typer.BadParameter(str(exc)) from exc
    data = {**plan.document(), "identity": plan.identity}
    typer.echo(
        json.dumps(data, indent=2)
        if json_output
        else f"Project manager: {plan.manager}\nInput identity: {plan.identity}"
    )


def _prepare_plan(plan: ProjectPlan, *, offline: bool, acquisition_url: str | None) -> dict[str, Any]:
    """Seal one selected project using its verified capsule interpreter."""
    from specfact_code_review.run.runner import (
        _capsule_environment_id,
        _cleanup_capsule_runtime,
        _prepare_capsule_runtime,
    )

    runtime = None
    try:
        controller = native_backend.select_runtime_backend()
        current = controller.environment_id if controller.kind == "darwin-arm64" else _capsule_environment_id()
        selected = select_environment(plan, current=current)
        runtime, reason = _prepare_capsule_runtime(environment_id=selected)
        if runtime is None:
            raise ProjectRuntimeError(reason)
        prepared = prepare_runtime(plan, runtime=runtime, offline=offline, acquisition_url=acquisition_url)
        return {
            "descriptor": str(prepared.descriptor_path),
            "identity": prepared.identity,
            "project": plan.document(),
            "authority": "local_build",
        }
    finally:
        if runtime is not None:
            _cleanup_capsule_runtime(runtime)


def _prepare_index(project_config: Path | None, *, offline: bool, acquisition_url: str | None) -> dict[str, Any]:
    """Prepare exactly the immutable snapshots used by local index review."""
    from specfact_code_review.run.portable_snapshot import discover_snapshot
    from specfact_code_review.run.scope import ScopeRequest, cleanup_scope_resolution, resolve_scope

    resolution = resolve_scope(ScopeRequest(repository=Path.cwd(), scope="index", portable_project_runtime=True))
    try:
        if resolution.status == "NOT_APPLICABLE":
            return {
                "scope": "index",
                "status": "NOT_APPLICABLE",
                "diagnostic": resolution.reason,
                "authority": "local_build",
                "protected_pr_eligible": False,
                "runtimes": {},
            }
        if resolution.status != "PASS" or resolution.base_snapshot is None or resolution.head_snapshot is None:
            raise ProjectRuntimeError(f"project_index_preparation_unavailable:{resolution.reason}")
        runtimes = {}
        for side, snapshot in (("base", resolution.base_snapshot), ("head", resolution.head_snapshot)):
            plan = discover_snapshot(snapshot.root, config_path=project_config, source_snapshot=snapshot)
            runtimes[side] = _prepare_plan(plan, offline=offline, acquisition_url=acquisition_url)
        return {"scope": "index", "authority": "local_build", "protected_pr_eligible": False, "runtimes": runtimes}
    finally:
        cleanup_scope_resolution(resolution)


@app.command("prepare")
@require(lambda project_config: project_config is None or isinstance(project_config, Path))
def prepare_project(
    project_config: Annotated[Path | None, typer.Option("--project-config")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    offline: Annotated[bool, typer.Option("--offline")] = False,
    acquisition_url: Annotated[str | None, typer.Option("--acquisition-url")] = None,
    scope: Annotated[Literal["project", "index"], typer.Option("--scope")] = "project",
) -> None:
    """Prepare or verify cached project or immutable index runtimes."""
    try:
        result = (
            _prepare_index(project_config, offline=offline, acquisition_url=acquisition_url)
            if scope == "index"
            else _prepare_plan(
                discover_project(Path.cwd(), config_path=project_config),
                offline=offline,
                acquisition_url=acquisition_url,
            )
        )
        typer.echo(json.dumps(result, indent=2) if json_output or scope == "index" else str(result["descriptor"]))
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
