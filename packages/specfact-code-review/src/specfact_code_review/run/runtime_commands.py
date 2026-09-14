"""Customer-facing inspection and preparation of portable Python runtimes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from icontract import require

from specfact_code_review.run.runtime_builder import prepare_runtime
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_interpreter import select_environment
from specfact_code_review.run.runtime_models import ProjectRuntimeError


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
        raise typer.BadParameter(str(exc)) from exc
    data = {**plan.document(), "identity": plan.identity}
    typer.echo(
        json.dumps(data, indent=2)
        if json_output
        else f"Project manager: {plan.manager}\nInput identity: {plan.identity}"
    )


@app.command("prepare")
@require(lambda project_config: project_config is None or isinstance(project_config, Path))
def prepare_project(
    project_config: Annotated[Path | None, typer.Option("--project-config")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    offline: Annotated[bool, typer.Option("--offline")] = False,
) -> None:
    """Prepare or verify a cached runtime using the signed capsule interpreter."""
    from specfact_code_review.run.runner import (
        _capsule_environment_id,
        _cleanup_capsule_runtime,
        _prepare_capsule_runtime,
    )

    runtime = None
    try:
        plan = discover_project(Path.cwd(), config_path=project_config)
        selected = select_environment(plan, current=_capsule_environment_id())
        runtime, reason = _prepare_capsule_runtime(environment_id=selected)
        if runtime is None:
            raise ProjectRuntimeError(reason)
        prepared = prepare_runtime(plan, runtime=runtime, offline=offline)
        result = {
            "descriptor": str(prepared.descriptor_path),
            "identity": prepared.identity,
            "project": plan.document(),
            "authority": "local_build",
        }
        typer.echo(json.dumps(result, indent=2) if json_output else str(prepared.descriptor_path))
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    finally:
        if runtime is not None:
            _cleanup_capsule_runtime(runtime)
