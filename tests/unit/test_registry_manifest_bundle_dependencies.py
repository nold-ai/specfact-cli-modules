"""Registry `bundle_dependencies` must match each package `module-package.yaml`."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _registry_modules() -> list[dict[str, object]]:
    data = json.loads((ROOT / "registry" / "index.json").read_text(encoding="utf-8"))
    modules = data.get("modules")
    assert isinstance(modules, list)
    return [m for m in modules if isinstance(m, dict)]


def _manifest_bundle_dependencies(module_id: str) -> list[str] | None:
    """Return bundle_dependencies from packages/<bundle>/module-package.yaml for nold-ai/<bundle>."""
    prefix = "nold-ai/"
    if not module_id.startswith(prefix):
        return None
    bundle = module_id[len(prefix) :]
    manifest = ROOT / "packages" / bundle / "module-package.yaml"
    if not manifest.exists():
        return None
    raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    deps = raw.get("bundle_dependencies")
    if deps is None:
        return None
    assert isinstance(deps, list)
    return [str(x) for x in deps]


def test_registry_bundle_dependencies_match_manifests() -> None:
    for entry in _registry_modules():
        module_id = str(entry.get("id") or "").strip()
        if not module_id:
            continue
        manifest_deps = _manifest_bundle_dependencies(module_id)
        if manifest_deps is None:
            continue
        reg_deps = entry.get("bundle_dependencies")
        assert isinstance(reg_deps, list), f"{module_id}: registry bundle_dependencies must be a list"
        assert [str(x) for x in reg_deps] == manifest_deps, (
            f"{module_id}: registry bundle_dependencies {reg_deps!r} must match module-package.yaml {manifest_deps!r}"
        )


def test_official_bundle_dependency_graph_is_acyclic() -> None:
    """Declared peer dependencies among official modules must not form a cycle."""
    edges: dict[str, list[str]] = {}
    for entry in _registry_modules():
        mid = str(entry.get("id") or "").strip()
        if not mid.startswith("nold-ai/"):
            continue
        deps = entry.get("bundle_dependencies")
        if not isinstance(deps, list):
            continue
        edges[mid] = [str(d) for d in deps if str(d).startswith("nold-ai/")]

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            msg = f"cycle detected involving {node}"
            raise AssertionError(msg)
        visiting.add(node)
        for succ in edges.get(node, []):
            visit(succ)
        visiting.remove(node)
        visited.add(node)

    for n in edges:
        visit(n)
