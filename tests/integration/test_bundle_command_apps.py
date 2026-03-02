from __future__ import annotations

import importlib

import pytest


COMMAND_MODULES = [
    "specfact_project.plan.commands",
    "specfact_project.project.commands",
    "specfact_backlog.backlog.commands",
    "specfact_codebase.analyze.commands",
    "specfact_spec.spec.commands",
    "specfact_govern.enforce.commands",
]


@pytest.mark.integration
@pytest.mark.parametrize("module_path", COMMAND_MODULES)
def test_command_module_exposes_typer_app(module_path: str) -> None:
    module = importlib.import_module(module_path)
    app = getattr(module, "app", None)
    assert app is not None, f"{module_path} missing app"
    assert hasattr(app, "registered_commands")
