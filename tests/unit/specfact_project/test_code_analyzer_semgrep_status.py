from __future__ import annotations

from pathlib import Path

from specfact_cli.utils.env_manager import EnvManager, EnvManagerInfo

from specfact_project.analyzers.code_analyzer import CodeAnalyzer


def test_semgrep_plugin_status_preserves_environment_probe_message(tmp_path: Path, monkeypatch) -> None:
    message = "Tool 'semgrep' not available in uv environment"

    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr(
        "specfact_cli.utils.env_manager.detect_env_manager",
        lambda repo_path: EnvManagerInfo(manager=EnvManager.UV, available=True, command_prefix=["uv", "run"]),
    )
    monkeypatch.setattr(
        "specfact_cli.utils.env_manager.check_tool_in_env",
        lambda repo_path, tool_name, env_info=None: (False, message),
    )

    analyzer = CodeAnalyzer(tmp_path)
    semgrep_status = next(
        plugin for plugin in analyzer.get_plugin_status() if plugin["name"] == "Semgrep Pattern Detection"
    )

    assert semgrep_status["enabled"] is False
    assert semgrep_status["reason"] == message
