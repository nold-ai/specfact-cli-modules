"""Native package-manager operations executed only inside the disposable builder."""

from __future__ import annotations

from icontract import require

from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


MANAGER_REQUIREMENTS = {
    "pip": ("pip==26.2.1",),
    "uv": ("uv==0.12.13",),
    "hatch": ("hatch==1.18.0",),
    "poetry": ("poetry==2.4.3",),
}


@require(lambda manager: len(manager) > 0)
def validate_adapter_inputs(manager: str, requirements: tuple[str, ...], constraints: tuple[str, ...]) -> None:
    """Reject inputs that the native adapter cannot consume without changing semantics."""
    unsupported = [name for name, values in (("requirements", requirements), ("constraints", constraints)) if values]
    if manager != "pip" and unsupported:
        raise ProjectRuntimeError(
            f"project_manager_inputs_unsupported:{manager}:{','.join(unsupported)}; "
            "declare dependencies in the selected manager configuration or select manager=pip in --project-config"
        )


def _pip_commands(plan: ProjectPlan, python: str) -> tuple[tuple[str, ...], ...]:
    arguments = [python, "-m", "pip", "install", "--disable-pip-version-check"]
    for option, values in (("--group", plan.groups), ("-r", plan.requirements), ("-c", plan.constraints)):
        for value in values:
            arguments.extend((option, value))
    if any((plan.root / name).exists() for name in ("pyproject.toml", "setup.py", "setup.cfg")):
        arguments.append("." + ("[" + ",".join(plan.extras) + "]" if plan.extras else ""))
    return (tuple(arguments),) if len(arguments) > 5 else ()


def _uv_commands(plan: ProjectPlan, python: str) -> tuple[tuple[str, ...], ...]:
    arguments = [python, "-m", "uv", "sync", "--active", "--no-editable"]
    if "uv.lock" in plan.inputs:
        arguments.append("--locked")
    if plan.groups:
        arguments.append("--no-default-groups")
    for option, values in (("--group", plan.groups), ("--extra", plan.extras)):
        for value in values:
            arguments.extend((option, value))
    return (tuple(arguments),)


def _poetry_commands(plan: ProjectPlan, python: str) -> tuple[tuple[str, ...], ...]:
    arguments = [python, "-m", "poetry", "install", "--no-interaction"]
    if plan.groups:
        arguments.extend(("--only", "main," + ",".join(plan.groups)))
    for extra in plan.extras:
        arguments.extend(("--extras", extra))
    return (tuple(arguments),)


def _hatch_commands(plan: ProjectPlan, python: str) -> tuple[tuple[str, ...], ...]:
    if plan.groups or plan.extras:
        raise ProjectRuntimeError(
            "project_hatch_environment_required: select an environment declaring the requested groups/extras"
        )
    return ((python, "-m", "hatch", "env", "create", plan.environment),)


@require(lambda python: len(python) > 0)
def install_commands(plan: ProjectPlan, *, python: str) -> tuple[tuple[str, ...], ...]:
    """Preserve the selected manager's resolution semantics and existing lock."""
    adapters = {"pip": _pip_commands, "uv": _uv_commands, "poetry": _poetry_commands, "hatch": _hatch_commands}
    adapter = adapters.get(plan.manager)
    if adapter is None:
        raise ProjectRuntimeError(f"project_manager_unsupported:{plan.manager}")
    validate_adapter_inputs(plan.manager, plan.requirements, plan.constraints)
    return adapter(plan, python)
