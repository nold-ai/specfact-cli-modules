from __future__ import annotations

import importlib

from typer.testing import CliRunner


runner = CliRunner()


def test_analyze_help_smoke() -> None:
    analyze_app = importlib.import_module("specfact_codebase.analyze.commands").app
    result = runner.invoke(analyze_app, ["--help"])
    assert result.exit_code == 0


def test_import_help_smoke() -> None:
    import_app = importlib.import_module("specfact_codebase.import_cmd.commands").app
    result = runner.invoke(import_app, ["--help"])
    assert result.exit_code == 0
