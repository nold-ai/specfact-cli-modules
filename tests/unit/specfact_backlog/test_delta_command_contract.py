from __future__ import annotations

import importlib
from pathlib import Path

from typer.testing import CliRunner


runner = CliRunner()


def test_delta_command_avoids_private_typer_click_import() -> None:
    source = Path("packages/specfact-backlog/src/specfact_backlog/backlog_core/commands/delta.py").read_text(
        encoding="utf-8"
    )

    assert "typer._click" not in source


def test_delta_status_accepts_adapter_argument_and_configured_project(tmp_path: Path, monkeypatch) -> None:
    delta_module = importlib.import_module("specfact_backlog.backlog_core.commands.delta")
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    fetched: dict[str, str] = {}

    config_dir = tmp_path / ".specfact"
    config_dir.mkdir()
    (config_dir / "backlog-config.yaml").write_text(
        "providers:\n  github:\n    project_id: nold-ai/specfact-cli\n    repo_owner: nold-ai\n    repo_name: specfact-cli\n",
        encoding="utf-8",
    )

    class FakeGraph:
        fetched_at = delta_module.datetime.now()
        items: dict[str, object] = {}

    def fake_fetch_current_graph(project_id: str, adapter: str, template: str):
        fetched["project_id"] = project_id
        fetched["adapter"] = adapter
        fetched["template"] = template
        return FakeGraph()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(delta_module, "_fetch_current_graph", fake_fetch_current_graph)
    monkeypatch.setattr(delta_module, "_load_baseline_graph", lambda baseline_file: FakeGraph())
    monkeypatch.setattr(delta_module, "compute_delta", lambda baseline, current: delta_module._empty_delta())

    result = runner.invoke(backlog_app, ["delta", "status", "github"])

    assert result.exit_code == 0, result.stdout
    assert fetched["adapter"] == "github"
    assert fetched["project_id"] == "nold-ai/specfact-cli"


def test_delta_status_missing_config_names_kebab_case_options(tmp_path: Path, monkeypatch) -> None:
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(backlog_app, ["delta", "status", "github"])

    assert result.exit_code != 0
    output = result.stdout
    assert "--project-id" in output
    assert "--repo-owner" in output
    assert "--repo-name" in output
    assert "repo_owner" not in output
    assert "repo_name" not in output


def test_delta_status_malformed_config_preserves_missing_context_guidance(tmp_path: Path, monkeypatch) -> None:
    backlog_app = importlib.import_module("specfact_backlog.backlog.commands").app
    config_dir = tmp_path / ".specfact"
    config_dir.mkdir()
    (config_dir / "backlog-config.yaml").write_text("providers:\n  github: [unterminated\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(backlog_app, ["delta", "status", "github"])

    assert result.exit_code != 0
    output = result.stdout
    assert "--project-id" in output
    assert "--repo-owner" in output
    assert "--repo-name" in output
    assert "ParserError" not in output
