from __future__ import annotations

import importlib
from pathlib import Path

from typer.testing import CliRunner

from specfact_backlog.backlog_core.graph.models import BacklogGraph


runner = CliRunner()


def test_sync_requires_force_for_existing_external_baseline(monkeypatch, tmp_path: Path) -> None:
    backlog_core_main = importlib.import_module("specfact_backlog.backlog_core.main")
    sync_module = importlib.import_module("specfact_backlog.backlog_core.commands.sync")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sync_module,
        "_fetch_current_graph",
        lambda *_args, **_kwargs: BacklogGraph(provider="github", project_key="demo"),
    )
    monkeypatch.setattr(sync_module, "_render_delta_summary", lambda _delta: None)

    baseline_path = tmp_path / "baseline.json"
    original_content = BacklogGraph(provider="github", project_key="existing").to_json()
    baseline_path.write_text(original_content, encoding="utf-8")

    result = runner.invoke(
        backlog_core_main.app,
        [
            "sync",
            "--project-id",
            "nold-ai/specfact-cli",
            "--adapter",
            "github",
            "--output-format",
            "json",
            "--baseline-file",
            str(baseline_path),
        ],
    )

    assert result.exit_code != 0
    assert "--force-baseline-overwrite" in result.output
    assert baseline_path.read_text(encoding="utf-8") == original_content


def test_sync_force_overwrite_external_baseline_creates_backup(monkeypatch, tmp_path: Path) -> None:
    backlog_core_main = importlib.import_module("specfact_backlog.backlog_core.main")
    sync_module = importlib.import_module("specfact_backlog.backlog_core.commands.sync")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sync_module,
        "_fetch_current_graph",
        lambda *_args, **_kwargs: BacklogGraph(provider="github", project_key="demo"),
    )
    monkeypatch.setattr(sync_module, "_render_delta_summary", lambda _delta: None)

    baseline_path = tmp_path / "baseline.json"
    original_content = BacklogGraph(provider="github", project_key="existing").to_json()
    baseline_path.write_text(original_content, encoding="utf-8")

    result = runner.invoke(
        backlog_core_main.app,
        [
            "sync",
            "--project-id",
            "nold-ai/specfact-cli",
            "--adapter",
            "github",
            "--output-format",
            "json",
            "--baseline-file",
            str(baseline_path),
            "--force-baseline-overwrite",
        ],
    )

    assert result.exit_code == 0, result.output
    assert baseline_path.read_text(encoding="utf-8") != original_content
    recovery_dir = tmp_path / ".specfact" / "recovery"
    backups = list(recovery_dir.glob("baseline.json.*.bak"))
    assert backups
    assert backups[0].read_text(encoding="utf-8") == original_content
