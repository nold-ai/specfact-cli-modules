from __future__ import annotations

import importlib

from typer.testing import CliRunner


runner = CliRunner()


def test_backlog_help_smoke() -> None:
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    result = runner.invoke(backlog_app, ["--help"])
    assert result.exit_code == 0
