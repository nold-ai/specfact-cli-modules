#!/usr/bin/env python3
"""Validate bundle manifests and registry JSON in specfact-cli-modules."""

from __future__ import annotations

import json
import re
from pathlib import Path


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


def main() -> int:
    manifest_paths = sorted(ROOT.glob("packages/*/module-package.yaml"))
    errors: list[str] = []

    for manifest in manifest_paths:
        errors.extend(_validate_yaml(manifest))

    errors.extend(_validate_registry(ROOT / "registry" / "index.json"))

    if errors:
        print("Manifest/registry validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print(f"Validated {len(manifest_paths)} manifests and registry/index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
