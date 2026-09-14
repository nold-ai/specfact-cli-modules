"""Compare member dependency requirements with the project graph without importing it."""

from __future__ import annotations

from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Any

from icontract import ensure
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


MEMBER_DISTRIBUTIONS = {
    "pylint": ("pylint", frozenset({"pylint", "astroid"})),
    "basedpyright": ("basedpyright", frozenset({"basedpyright", "nodejs-wheel"})),
    "contracts": ("crosshair-tool", frozenset({"crosshair-tool", "z3-solver"})),
}


def _requirements_for(
    name: str, distribution: Distribution, project: dict[str, Any] | None, pinned: frozenset[str]
) -> list[str]:
    if project and name not in pinned:
        return list(project.get("requires_dist", []) or [])
    return list(distribution.requires or [])


def _member_conflicts(
    member: str, target: dict[str, Any], sealed: dict[str, Distribution], environment: dict[str, str]
) -> list[str]:
    entry, pinned = MEMBER_DISTRIBUTIONS[member]
    pending = [entry]
    visited = set()
    reasons = []
    while pending:
        name = pending.pop()
        if name in visited or name not in sealed:
            continue
        visited.add(name)
        distribution = sealed[name]
        project = target.get(name)
        if project and name in pinned and project["version"] != distribution.version:
            reasons.append(f"{name}: target={project['version']}, sealed entry={distribution.version}")
        for raw in _requirements_for(name, distribution, project, pinned):
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            dependency = str(canonicalize_name(requirement.name))
            actual = target.get(dependency)
            if actual and actual["version"] not in requirement.specifier:
                reasons.append(f"{dependency}: target={actual['version']}, required={requirement.specifier} by {name}")
            pending.append(dependency)
    return reasons


@ensure(lambda result: set(result) <= set(MEMBER_DISTRIBUTIONS))
def analyzer_dependency_conflicts(inventory: dict[str, Any], analyzer_root: Path) -> dict[str, str]:
    """Name genuine per-member incompatibilities, allowing compatible target overrides."""
    target = {
        str(canonicalize_name(row["metadata"]["name"])): row["metadata"] for row in inventory.get("installed", [])
    }
    sealed = {str(canonicalize_name(dist.metadata["Name"])): dist for dist in distributions(path=[str(analyzer_root)])}
    environment = {
        **default_environment(),
        "sys_platform": "linux",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        **inventory.get("environment", {}),
        "extra": "",
    }
    conflicts = {}
    for member in MEMBER_DISTRIBUTIONS:
        reasons = _member_conflicts(member, target, sealed, environment)
        if reasons:
            conflicts[member] = "project_analyzer_dependency_incompatible:" + "; ".join(sorted(set(reasons)))
    return conflicts
