#!/usr/bin/env python3
"""Validate bundle manifests and registry JSON in specfact-cli-modules."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_KEYS = {"name", "version", "tier", "publisher", "description", "bundle_group_command"}


def _validate_yaml(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    found_keys = {match.group("key") for match in re.finditer(r"(?m)^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:", text)}
    missing = sorted(REQUIRED_KEYS - found_keys)
    if missing:
        errors.append(f"{path}: missing keys: {', '.join(missing)}")
    return errors


def _validate_registry(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]

    if not isinstance(data, dict):
        return [f"{path}: registry root must be an object"]
    if "modules" not in data or not isinstance(data["modules"], list):
        return [f"{path}: expected 'modules' list"]
    return []


def registry_module_ids(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    modules = data.get("modules")
    if not isinstance(modules, list):
        return set()
    return {str(m["id"]).strip() for m in modules if isinstance(m, dict) and str(m.get("id") or "").strip()}


def validate_manifest_bundle_dependency_refs(manifest_path: Path, registry_ids: set[str]) -> list[str]:
    """Ensure each bundle_dependencies entry targets a module id present in registry/index.json."""
    errors: list[str] = []
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return [f"{manifest_path}: cannot parse YAML for bundle_dependencies check ({exc})"]
    if not isinstance(raw, dict):
        return []
    deps = raw.get("bundle_dependencies")
    if deps is None:
        return []
    if not isinstance(deps, list):
        return [f"{manifest_path}: bundle_dependencies must be a list when present"]
    for dep in deps:
        dep_id = str(dep).strip()
        if not dep_id:
            continue
        if dep_id not in registry_ids:
            errors.append(
                f"{manifest_path}: bundle_dependencies references unknown module id {dep_id!r} "
                f"(no matching entry in registry/index.json)"
            )
    return errors


def main() -> int:
    manifest_paths = sorted(ROOT.glob("packages/*/module-package.yaml"))
    errors: list[str] = []

    registry_path = ROOT / "registry" / "index.json"
    errors.extend(_validate_registry(registry_path))

    registry_ids: set[str] | None = None
    if not errors:
        try:
            registry_ids = registry_module_ids(registry_path)
        except (json.JSONDecodeError, OSError, TypeError, KeyError) as exc:
            errors.append(f"{registry_path}: cannot load module ids ({exc})")

    for manifest in manifest_paths:
        errors.extend(_validate_yaml(manifest))
        if registry_ids is not None:
            errors.extend(validate_manifest_bundle_dependency_refs(manifest, registry_ids))

    if errors:
        print("Manifest/registry validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print(f"Validated {len(manifest_paths)} manifests and registry/index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
