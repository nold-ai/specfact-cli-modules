from __future__ import annotations

from pathlib import Path

from packaging.version import InvalidVersion, Version


def determine_registry_baseline_ref(*, current_branch: str, default_branch: str) -> str:
    normalized_current = current_branch.strip()
    normalized_default = default_branch.strip() or "main"
    if normalized_current in {"dev", "main"}:
        return normalized_current
    return normalized_default


def _bundle_from_path(path: str) -> str | None:
    parts = Path(path).parts
    if len(parts) < 2 or parts[0] != "packages":
        return None
    bundle = parts[1]
    return bundle if bundle.startswith("specfact-") else None


def resolve_publish_bundles(
    *,
    changed_paths: list[str],
    manifest_versions: dict[str, str],
    registry_versions: dict[str, str],
) -> dict[str, set[str]]:
    selected: dict[str, set[str]] = {}

    for path in changed_paths:
        bundle = _bundle_from_path(path)
        if bundle is None:
            continue
        selected.setdefault(bundle, set()).add("changed")

    for bundle, manifest_version_raw in manifest_versions.items():
        registry_version_raw = registry_versions.get(bundle)
        if not registry_version_raw:
            continue
        try:
            manifest_version = Version(str(manifest_version_raw))
            registry_version = Version(str(registry_version_raw))
        except InvalidVersion:
            continue
        if manifest_version > registry_version:
            selected.setdefault(bundle, set()).add("registry-outdated")

    return selected
