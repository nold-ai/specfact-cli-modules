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
