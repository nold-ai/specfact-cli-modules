from __future__ import annotations

from publish_bundle_selection import resolve_publish_bundles


def test_resolve_publish_bundles_includes_registry_outdated_bundle_not_in_diff() -> None:
    changed_paths = ["packages/specfact-project/src/specfact_project/project/commands.py"]
    manifest_versions = {
        "specfact-project": "0.40.16",
        "specfact-backlog": "0.40.18",
    }
    registry_versions = {
        "specfact-project": "0.40.16",
        "specfact-backlog": "0.40.17",
    }

    selected = resolve_publish_bundles(
        changed_paths=changed_paths,
        manifest_versions=manifest_versions,
        registry_versions=registry_versions,
    )

    assert selected["specfact-project"] == {"changed"}
    assert selected["specfact-backlog"] == {"registry-outdated"}


def test_resolve_publish_bundles_unions_changed_and_registry_outdated_reasons() -> None:
    changed_paths = ["packages/specfact-backlog/src/specfact_backlog/backlog/commands.py"]
    manifest_versions = {"specfact-backlog": "0.40.18"}
    registry_versions = {"specfact-backlog": "0.40.17"}

    selected = resolve_publish_bundles(
        changed_paths=changed_paths,
        manifest_versions=manifest_versions,
        registry_versions=registry_versions,
    )

    assert selected["specfact-backlog"] == {"changed", "registry-outdated"}
