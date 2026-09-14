"""Record the exact dependency closure admitted to each target execution domain."""

from __future__ import annotations

from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Any

from icontract import ensure
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from specfact_code_review.run.runtime_compatibility import MEMBER_DISTRIBUTIONS
from specfact_code_review.run.runtime_models import ProjectRuntimeError


_DOMAIN_ENTRIES = {
    "pylint": ("pylint",),
    "basedpyright": ("basedpyright",),
    "crosshair": ("crosshair-tool",),
    "pytest-observe": ("pytest", "pytest-cov"),
}
_PINNED = frozenset(name for _, names in MEMBER_DISTRIBUTIONS.values() for name in names)


def _top_level_imports(distribution: Distribution) -> set[str]:
    declared = distribution.read_text("top_level.txt")
    if declared:
        return {name for name in declared.splitlines() if name.isidentifier()}
    names = set()
    for entry in distribution.files or ():
        first = entry.parts[0]
        name = first.split(".", maxsplit=1)[0]
        if name.isidentifier() and not first.endswith((".dist-info", ".data")):
            names.add(name)
    return names


def _dependency_names(
    requirements: list[str],
    environment: dict[str, str],
    *,
    domain: str,
    target: dict[str, Any],
    sealed: dict[str, Distribution],
) -> list[str]:
    names = []
    for raw in requirements:
        requirement = Requirement(raw)
        if requirement.marker is None or requirement.marker.evaluate(environment):
            name = str(canonicalize_name(requirement.name))
            selected = _selected_distribution(name, target, sealed)
            if selected is not None and not requirement.specifier.contains(selected[0]["version"], prereleases=True):
                raise ProjectRuntimeError(
                    f"project_analyzer_dependency_incompatible:{domain}:{name}; "
                    f"selected={selected[0]['version']}, required={requirement.specifier}"
                )
            names.append(name)
    return names


def _selected_distribution(
    name: str, target: dict[str, Any], sealed: dict[str, Distribution]
) -> tuple[dict[str, Any], list[str], set[str]] | None:
    if name in target and name not in _PINNED:
        project = target[name]
        return (
            {"name": name, "version": project["version"], "origin": "project"},
            project.get("requires_dist", []) or [],
            set(),
        )
    distribution = sealed.get(name)
    if distribution is None:
        return None
    return (
        {"name": name, "version": distribution.version, "origin": "analyzer"},
        list(distribution.requires or []),
        _top_level_imports(distribution),
    )


def _domain_graph(
    domain: str, target: dict[str, Any], sealed: dict[str, Distribution], environment: dict[str, str]
) -> dict[str, Any]:
    pending = list(_DOMAIN_ENTRIES[domain])
    visited = set()
    rows = []
    imports = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        selected = _selected_distribution(name, target, sealed)
        if selected is None:
            raise ProjectRuntimeError(
                f"project_analyzer_dependency_missing:{domain}:{name}; "
                "rebuild the runtime with its complete declared dependencies"
            )
        row, requirements, admitted_imports = selected
        dependencies = _dependency_names(requirements, environment, domain=domain, target=target, sealed=sealed)
        rows.append({**row, "dependencies": sorted(dependencies)})
        imports.update(admitted_imports)
        pending.extend(dependencies)
    return {"installed": sorted(rows, key=lambda row: row["name"]), "sealed_imports": sorted(imports)}


@ensure(lambda result: set(result) == set(_DOMAIN_ENTRIES))
def member_dependency_graphs(inventory: dict[str, Any], analyzer_root: Path) -> dict[str, Any]:
    """Admit required analyzer packages without exposing unrelated sealed dependencies."""
    target = {
        str(canonicalize_name(row["metadata"]["name"])): row["metadata"] for row in inventory.get("installed", [])
    }
    sealed = {str(canonicalize_name(dist.metadata["Name"])): dist for dist in distributions(path=[str(analyzer_root)])}
    environment = {**default_environment(), **inventory.get("environment", {}), "extra": ""}
    return {domain: _domain_graph(domain, target, sealed, environment) for domain in _DOMAIN_ENTRIES}
