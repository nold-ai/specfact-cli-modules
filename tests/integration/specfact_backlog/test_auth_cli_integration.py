from __future__ import annotations

import importlib
from pathlib import Path

from typer.testing import CliRunner


runner = CliRunner()


def test_backlog_auth_status_and_pat_roundtrip(monkeypatch, tmp_path: Path) -> None:
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    monkeypatch.setenv("HOME", str(tmp_path))

    before = runner.invoke(backlog_app, ["auth", "status"])
    assert before.exit_code == 0
    assert "No stored authentication tokens found." in before.stdout

    login = runner.invoke(backlog_app, ["auth", "azure-devops", "--pat", "test-token"])
    assert login.exit_code == 0
    assert "Stored token for provider: azure-devops" in login.stdout

    after = runner.invoke(backlog_app, ["auth", "status"])
    assert after.exit_code == 0
    assert "azure-devops" in after.stdout
