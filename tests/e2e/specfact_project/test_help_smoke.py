from __future__ import annotations

import importlib

from typer.testing import CliRunner


runner = CliRunner()


def test_plan_help_smoke() -> None:
    plan_app = importlib.import_module("specfact_project.plan.commands").app
    result = runner.invoke(plan_app, ["--help"])
    assert result.exit_code == 0


def test_project_sync_bridge_help_smoke() -> None:
    project_app = importlib.import_module("specfact_project.project.commands").app
    result = runner.invoke(project_app, ["sync", "bridge", "--help"])
    assert result.exit_code == 0
