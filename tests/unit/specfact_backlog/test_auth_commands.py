from __future__ import annotations

import importlib
from typing import Any

from typer.testing import CliRunner


runner = CliRunner()


def test_auth_azure_devops_pat_stores_provider_token(monkeypatch) -> None:
    auth_commands = importlib.import_module("specfact_backlog.backlog.auth_commands")
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    captured: dict[str, Any] = {}

    def fake_set_token(provider: str, token_data: dict[str, Any]) -> None:
        captured["provider"] = provider
        captured["token_data"] = token_data

    monkeypatch.setattr(auth_commands, "set_token", fake_set_token)

    result = runner.invoke(backlog_app, ["auth", "azure-devops", "--pat", "test-token"])

    assert result.exit_code == 0
    assert captured["provider"] == "azure-devops"
    token_data = captured["token_data"]
    assert token_data["access_token"] == "test-token"
    assert token_data["token_type"] == "basic"


def test_auth_status_uses_get_token_with_expected_provider_ids(monkeypatch) -> None:
    auth_commands = importlib.import_module("specfact_backlog.backlog.auth_commands")
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    calls: list[tuple[str, bool]] = []

    def fake_get_token(provider: str, allow_expired: bool = False) -> dict[str, Any] | None:
        calls.append((provider, allow_expired))
        if provider == "github" and not allow_expired:
            return {"access_token": "gh-token", "token_type": "bearer"}
        return None

    monkeypatch.setattr(auth_commands, "get_token", fake_get_token)

    result = runner.invoke(backlog_app, ["auth", "status"])

    assert result.exit_code == 0
    assert ("github", False) in calls
    assert ("azure-devops", False) in calls
    assert "github" in result.stdout


def test_auth_clear_with_provider_calls_clear_token(monkeypatch) -> None:
    auth_commands = importlib.import_module("specfact_backlog.backlog.auth_commands")
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    captured: dict[str, str] = {}

    def fake_clear_token(provider: str) -> None:
        captured["provider"] = provider

    monkeypatch.setattr(auth_commands, "clear_token", fake_clear_token)

    result = runner.invoke(backlog_app, ["auth", "clear", "--provider", "github"])

    assert result.exit_code == 0
    assert captured["provider"] == "github"
