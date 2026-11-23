"""Test Repro command options and reporting with deterministic tool responses."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
import tomlkit
import yaml
from specfact_cli.utils import env_manager
from typer.testing import CliRunner

from specfact_codebase.repro import commands
from specfact_codebase.validators import repro_checker
from specfact_codebase.validators.sidecar import orchestrator


@pytest.fixture
def command_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use pip command routing and keep the user's tools outside the test."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
    info = env_manager.EnvManagerInfo(env_manager.EnvManager.PIP, True, [], "Using pip")
    monkeypatch.setattr(env_manager, "detect_env_manager", lambda _repo: info)
    monkeypatch.setattr(commands, "detect_env_manager", lambda _repo: info)
    monkeypatch.setattr(env_manager, "check_tool_in_env", lambda *_args: (False, "not installed"))
    monkeypatch.setattr(commands, "check_tool_in_env", lambda *_args: (False, "not installed"))
    return tmp_path


@pytest.mark.parametrize(
    ("args", "error"),
    [
        (["--budget", "0"], "Budget must be positive"),
        (["--crosshair-per-path-timeout", "0"], "CrossHair per-path timeout must be positive"),
        (["--sidecar"], "--sidecar-bundle is required"),
    ],
)
def test_repro_rejects_invalid_options(command_repo: Path, args: list[str], error: str) -> None:
    result = CliRunner().invoke(commands.app, ["--repo", str(command_repo), *args])
    assert result.exit_code == 2
    assert error in result.output
    assert not (command_repo / ".specfact").exists()


@pytest.mark.parametrize("install", [False, True])
def test_setup_preserves_project_config(command_repo: Path, monkeypatch: pytest.MonkeyPatch, *, install: bool) -> None:
    config = command_repo / "pyproject.toml"
    config.write_text('[project]\nname = "example"\n', encoding="utf-8")
    install_tool = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(subprocess, "run", install_tool)
    args = ["setup", "--repo", str(command_repo)]
    if install:
        args.append("--install-crosshair")
    result = CliRunner().invoke(commands.app, args)
    assert result.exit_code == 0, result.output
    assert "Setup complete!" in result.output
    assert install_tool.call_count == int(install)
    data = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert data.unwrap()["project"]["name"] == "example"
    assert data.unwrap()["tool"]["crosshair"]["per_path_timeout"] == 5


def test_setup_reports_invalid_project_config(command_repo: Path) -> None:
    config = command_repo / "pyproject.toml"
    config.write_text("[broken\n", encoding="utf-8")
    result = CliRunner().invoke(commands.app, ["setup", "--repo", str(command_repo)])
    assert result.exit_code == 1
    assert "Failed to update" in result.output
    assert config.read_text(encoding="utf-8") == "[broken\n"


@pytest.mark.parametrize(
    ("tool", "status", "expected_code", "summary"),
    [
        ("ruff", repro_checker.CheckStatus.FAILED, 1, "Some validations failed"),
        ("crosshair", repro_checker.CheckStatus.FAILED, 0, "CrossHair failed (advisory)"),
        ("pytest", repro_checker.CheckStatus.TIMEOUT, 2, "Budget exceeded"),
    ],
)
def test_repro_reports_check_result_and_exit(
    command_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    status: repro_checker.CheckStatus,
    expected_code: int,
    summary: str,
) -> None:
    checks = repro_checker.ReproReport()
    checks.add_check(
        repro_checker.CheckResult("Example check", tool, status, 1.0, output="Tool output", error="Tool diagnostic")
    )
    monkeypatch.setattr(repro_checker.ReproChecker, "run_all_checks", lambda _checker: checks)
    result = CliRunner().invoke(commands.app, ["--repo", str(command_repo), "--verbose", "--fail-fast"])
    assert result.exit_code == expected_code, result.output
    assert summary in result.output
    assert "Tool diagnostic" in result.output
    reports = list((command_repo / ".specfact").rglob("*.yaml"))
    report = next(item for item in reports if item.name.startswith("report-"))
    data = yaml.safe_load(report.read_text(encoding="utf-8"))
    assert data["checks"][0]["status"] == status.value
    assert data["checks"][0]["tool"] == tool


def test_repro_requires_missing_crosshair_when_requested(command_repo: Path) -> None:
    result = CliRunner().invoke(
        commands.app, ["--repo", str(command_repo), "--crosshair-required", "--crosshair-per-path-timeout", "2", "-v"]
    )
    assert result.exit_code == 1
    assert "CrossHair is required but unavailable" in result.output
    assert "CrossHair per-path timeout: 2s" in result.output


@pytest.mark.parametrize(
    ("outcome", "diagnostic"),
    [
        (subprocess.CompletedProcess([], 1, "", "dependency resolution failed"), "dependency resolution failed"),
        (subprocess.TimeoutExpired("pip", 60), "Installation timed out"),
        (OSError("permission denied"), "permission denied"),
    ],
)
def test_setup_warns_if_optional_install_fails(
    command_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: subprocess.CompletedProcess[str] | Exception,
    diagnostic: str,
) -> None:
    install_tool = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    monkeypatch.setattr(subprocess, "run", install_tool)
    result = CliRunner().invoke(commands.app, ["setup", "--repo", str(command_repo), "--install-crosshair"])
    assert result.exit_code == 0, result.output
    assert diagnostic in result.output
    assert (command_repo / "pyproject.toml").is_file()


@pytest.mark.parametrize("has_unannotated", [False, True])
def test_repro_sidecar_reports_results_for_selected_bundle(
    command_repo: Path, monkeypatch: pytest.MonkeyPatch, *, has_unannotated: bool
) -> None:
    if has_unannotated:
        (command_repo / "src" / "example.py").write_text("def show(value):\n    return value\n", encoding="utf-8")
    sidecar = Mock(return_value={"crosshair_summary": {"confirmed": 2, "not_confirmed": 1, "violations": 0}})
    monkeypatch.setattr(orchestrator, "run_sidecar_validation", sidecar)
    result = CliRunner().invoke(commands.app, ["--repo", str(command_repo), "--sidecar", "--sidecar-bundle", "example"])
    assert result.exit_code == 0, result.output
    assert ("unannotated functions" if has_unannotated else "No unannotated functions detected") in result.output
    assert "Sidecar CrossHair: 2 confirmed, 1 not confirmed, 0 violations" in result.output
    sidecar.assert_called_once()
    assert sidecar.call_args.args[0].bundle_name == "example"
    assert sidecar.call_args.args[0].repo_path == command_repo


def test_repro_writes_report_for_active_bundle(command_repo: Path) -> None:
    config = command_repo / ".specfact" / "config.yaml"
    config.parent.mkdir()
    config.write_text("active_bundle: example\n", encoding="utf-8")
    result = CliRunner().invoke(commands.app, ["--repo", str(command_repo)])
    assert result.exit_code == 0, result.output
    report_dir = command_repo / ".specfact" / "projects" / "example" / "reports" / "enforcement"
    report = next(report_dir.glob("report-*.yaml"))
    assert yaml.safe_load(report.read_text(encoding="utf-8"))["failed_checks"] == 0


def test_setup_uses_existing_crosshair_without_install(command_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "check_tool_in_env", lambda *_args: (True, "available"))
    install_tool = Mock()
    monkeypatch.setattr(subprocess, "run", install_tool)
    result = CliRunner().invoke(commands.app, ["setup", "--repo", str(command_repo), "--install-crosshair"])
    assert result.exit_code == 0, result.output
    assert "crosshair-tool is available" in result.output
    assert "Setup complete!" in result.output
    install_tool.assert_not_called()
