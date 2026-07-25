from __future__ import annotations

import importlib
import sys

import typer
from typer.testing import CliRunner


runner = CliRunner()


def test_module_group_without_subcommand_uses_shared_missing_subcommand_contract(monkeypatch) -> None:
    for module_name in tuple(sys.modules):
        if module_name == "specfact_codebase" or module_name.startswith("specfact_codebase."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    app = importlib.import_module("specfact_codebase.code.commands").app

    result = runner.invoke(app, [])

    assert result.exit_code == 2
    output = result.output.lower()
    assert "usage:" in output
    assert "codebase quality" in output
    assert "import" in output
    assert "analyze" in output
    assert "missing subcommand" in output


def test_module_leaf_missing_argument_uses_shared_missing_parameter_contract() -> None:
    app = typer.Typer(name="module-sample")

    def apply_module_change(change_id: str) -> None:
        typer.echo(change_id)

    def list_module_changes() -> None:
        typer.echo("[]")

    app.command("apply")(apply_module_change)
    app.command("list")(list_module_changes)

    result = runner.invoke(app, ["apply"])

    assert result.exit_code == 2
    output = result.stdout.lower()
    assert "usage:" in output
    assert "apply" in output
    assert "missing" in output or "[required]" in output
    assert "change-id" in output or "change_id" in output
