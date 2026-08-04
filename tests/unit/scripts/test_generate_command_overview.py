"""Regression tests for generated module command overview metadata."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_overview_module():
    script = Path(__file__).resolve().parents[3] / "scripts" / "generate-command-overview.py"
    spec = importlib.util.spec_from_file_location("generate_command_overview", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generated_commands() -> set[str]:
    overview = _load_overview_module()
    return {record["command"] for record in overview.build_records()}


def test_runtime_validated_code_groups_are_marked_as_executing() -> None:
    """Groups that validate a bundle before dispatch are not missing-subcommand errors."""
    overview = _load_overview_module()
    records = {record["command"]: record for record in overview.build_records()}

    assert records["specfact code import"]["bare_invocation"] == "executes"
    assert records["specfact code repro"]["bare_invocation"] == "executes"


def test_code_review_inventory_matches_the_mounted_command_surface() -> None:
    """The public review path has one review segment and all review subcommands."""
    commands = _generated_commands()

    assert "specfact code review run" in commands
    assert "specfact code review review run" not in commands
    assert "specfact code review ledger status" in commands
    assert "specfact code review rules init" in commands


def test_generated_command_inventory_has_no_duplicate_paths() -> None:
    overview = _load_overview_module()
    commands = [record["command"] for record in overview.build_records()]

    assert len(commands) == len(set(commands))


def test_unpublished_manifest_metadata_may_lead_registry() -> None:
    """Allow CI/CD to publish metadata for a manifest version not yet in the registry."""
    overview = _load_overview_module()
    manifest = {
        "version": "1.2.4",
        "tier": "official",
        "publisher": {"name": "nold-ai"},
        "bundle_dependencies": ["nold-ai/specfact-requirements"],
        "description": "Current module metadata.",
        "core_compatibility": ">=0.53.1,<1.0.0",
    }
    registry = {
        "latest_version": "1.2.3",
        "download_url": "modules/example-1.2.3.tar.gz",
        "tier": "official",
        "publisher": {"name": "nold-ai"},
        "bundle_dependencies": [],
        "description": "Previous module metadata.",
        "core_compatibility": ">=0.52.0,<1.0.0",
    }

    assert overview._official_metadata_drift({"nold-ai/example": manifest}, {"nold-ai/example": registry}) == []


def test_published_manifest_metadata_must_match_registry() -> None:
    """Keep registry metadata authoritative once a manifest version is published."""
    overview = _load_overview_module()
    manifest = {
        "version": "1.2.3",
        "tier": "official",
        "publisher": {"name": "nold-ai"},
        "bundle_dependencies": ["nold-ai/specfact-requirements"],
        "description": "Current module metadata.",
        "core_compatibility": ">=0.53.1,<1.0.0",
    }
    registry = {
        "latest_version": "1.2.3",
        "download_url": "modules/example-1.2.3.tar.gz",
        "tier": "official",
        "publisher": {"name": "nold-ai"},
        "bundle_dependencies": [],
        "description": "Current module metadata.",
        "core_compatibility": ">=0.53.1,<1.0.0",
    }

    assert overview._official_metadata_drift({"nold-ai/example": manifest}, {"nold-ai/example": registry}) == [
        "nold-ai/example: manifest.bundle_dependencies != registry.bundle_dependencies"
    ]
