#!/usr/bin/env python3
"""Validate module publish inputs for specfact-cli-modules.

This script enforces monotonic bundle versioning and warns maintainers to
review `core_compatibility` updates whenever a version bump is detected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from packaging.version import InvalidVersion, Version


def _fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def _warn(message: str) -> None:
    print(f"WARNING: {message}")


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be object: {path}")
    return data


def _bundle_dir(repo_root: Path, bundle: str) -> Path:
    bundle_name = bundle.strip()
    if not bundle_name.startswith("specfact-"):
        bundle_name = f"specfact-{bundle_name}"
    path = repo_root / "packages" / bundle_name
    if not path.exists():
        raise FileNotFoundError(f"Bundle directory not found: {path}")
    return path


def _find_registry_entry(registry: dict, module_name: str) -> dict | None:
    modules = registry.get("modules")
    if not isinstance(modules, list):
        return None
    expected_id = f"nold-ai/{module_name}"
    for entry in modules:
        if isinstance(entry, dict) and entry.get("id") == expected_id:
            return entry
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate module publish preconditions")
    parser.add_argument("--bundle", required=True, help="Bundle name, e.g. specfact-backlog or backlog")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    bundle_dir = _bundle_dir(repo_root, args.bundle)
    manifest_path = bundle_dir / "module-package.yaml"
    registry_path = repo_root / "registry" / "index.json"

    if not manifest_path.exists():
        return _fail(f"Missing manifest: {manifest_path}")
    if not registry_path.exists():
        return _fail(f"Missing registry index: {registry_path}")

    manifest = _load_yaml(manifest_path)
    module_name = bundle_dir.name
    manifest_version_raw = manifest.get("version")
    core_compatibility = str(manifest.get("core_compatibility", "")).strip()

    if not manifest_version_raw:
        return _fail("module-package.yaml missing 'version'")

    try:
        manifest_version = Version(str(manifest_version_raw))
    except InvalidVersion as exc:
        return _fail(f"Invalid manifest version '{manifest_version_raw}': {exc}")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = _find_registry_entry(registry, module_name)
    if entry is None:
        _warn(f"No registry entry found for nold-ai/{module_name}; skipping monotonic comparison")
        print("OK: publish validation passed")
        return 0

    latest_raw = entry.get("latest_version")
    if not latest_raw:
        return _fail(f"Registry entry for nold-ai/{module_name} missing latest_version")

    try:
        latest_version = Version(str(latest_raw))
    except InvalidVersion as exc:
        return _fail(f"Invalid registry latest_version '{latest_raw}': {exc}")

    if manifest_version <= latest_version:
        return _fail(
            f"Bundle version must be greater than registry latest_version: "
            f"manifest={manifest_version} latest={latest_version}"
        )

    if not core_compatibility:
        _warn("core_compatibility is empty; verify compatibility range before publish")
    else:
        _warn(
            "Version bump detected; verify core_compatibility was intentionally reviewed/updated "
            f"(current: '{core_compatibility}')"
        )

    print("OK: publish validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
