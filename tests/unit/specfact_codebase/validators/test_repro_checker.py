"""Verify reproducibility checks, process outcomes, and backward-compatible reports."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from specfact_cli.utils import env_manager

from specfact_codebase.validators.repro_checker import CheckResult, CheckStatus, ReproChecker


@pytest.mark.parametrize(
    ("tool", "output", "error", "counts"),
    [
        (
            "ruff",
            "W293 [*] Blank line contains whitespace\n --> src/a.py:10:1\n | help\n"
            "src/b.py:12:2: F401 Unused import\n2 files checked\n",
            "",
            {"total_violations": 2, "files_checked": 2},
        ),
        (
            "semgrep",
            "",
            "Findings: 2\nRules run: 3\nTargets scanned: 7\n",
            {"total_findings": 2, "rules_run": 3, "targets_scanned": 7},
        ),
        (
            "basedpyright",
            "a.py:2:3: error: Wrong type\nb.py:4:8 - warning: Unused\n",
            "",
            {"total_errors": 1, "total_warnings": 1},
        ),
        ("basedpyright", "2 errors, 3 warnings", "", {"total_errors": 2, "total_warnings": 3}),
        ("crosshair", "a.py:3: Counterexample found", "", {"total_counterexamples": 1}),
        (
            "pytest",
            "1 passed, 2 failed, 3 skipped",
            "",
            {"tests_run": 6, "tests_passed": 1, "tests_failed": 2, "tests_skipped": 3},
        ),
    ],
)
def test_report_parses_tool_output(tool: str, output: str, error: str, counts: dict[str, int]) -> None:
    result = CheckResult("Check", tool, CheckStatus.FAILED, output=output, error=error).to_dict()
    assert {key: result["findings"][key] for key in counts} == counts


@pytest.mark.parametrize(("limit", "truncated"), [(2, True), (50, False)])
def test_malformed_analyzer_output_keeps_raw_diagnostic(limit: int, *, truncated: bool) -> None:
    result = CheckResult("Async", "async-checks", CheckStatus.FAILED, output="invalid", error="diagnostic")
    report = result.to_dict(max_output_length=limit)
    assert report["output"] == "invalid"[:limit]
    assert report["error"] == "diagnostic"[:limit]
    assert report.get("output_truncated", False) is truncated
    assert report.get("error_truncated", False) is truncated


@pytest.mark.parametrize(
    ("tool", "code", "error", "status", "message"),
    [
        ("ruff", 0, "", CheckStatus.PASSED, ""),
        ("ruff", 1, "invalid", CheckStatus.FAILED, "invalid"),
        ("crosshair", 1, "wrong parameter order", CheckStatus.SKIPPED, "signature analysis limitation"),
        ("crosshair", 1, "SideEffectDetected", CheckStatus.SKIPPED, "side-effect detected"),
        ("crosshair", 1, "a counterexample", CheckStatus.FAILED, "a counterexample"),
        ("async-checks", 2, "", CheckStatus.FAILED, "did not complete"),
    ],
)
def test_run_check_classifies_tool_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: str, code: int, error: str, status: CheckStatus, message: str
) -> None:
    command = [tool]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=subprocess.CompletedProcess(command, code, "", error)))
    result = ReproChecker(tmp_path).run_check("Example", tool, command, skip_if_missing=False)
    assert result.status == status
    assert result.exit_code == code
    assert message in result.error


@pytest.mark.parametrize(
    ("exception", "status", "message"),
    [
        (subprocess.TimeoutExpired("check", 5), CheckStatus.TIMEOUT, "timed out"),
        (OSError("permission denied"), CheckStatus.FAILED, "permission denied"),
    ],
)
def test_run_check_reports_subprocess_exceptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exception: Exception, status: CheckStatus, message: str
) -> None:
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=exception))
    result = ReproChecker(tmp_path).run_check("Example", "ruff", ["ruff"], timeout=5, skip_if_missing=False)
    assert result.status == status
    assert message in result.error


def test_run_check_does_not_start_missing_or_overbudget_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_tool = Mock()
    monkeypatch.setattr(subprocess, "run", run_tool)
    checker = ReproChecker(tmp_path, budget=10)
    result = checker.run_check("Missing", "ruff", ["specfact-test-missing-binary"])
    assert result.status is CheckStatus.SKIPPED
    checker.start_time = time.time() - 11
    result = checker.run_check("Slow", "ruff", ["specfact-test-missing-binary"], skip_if_missing=False)
    assert result.status is CheckStatus.TIMEOUT
    assert checker.report.get_exit_code() == 2
    run_tool.assert_not_called()


@pytest.mark.parametrize("marked", [True, False])
def test_run_all_checks_executes_selected_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, marked: bool
) -> None:
    for name in ("src", "tools", "tests/contracts", "tests/smoke"):
        (tmp_path / name).mkdir(parents=True)
    (tmp_path / "src" / "__main__.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    (tmp_path / "src" / "project.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "tools" / "property_checks.py").write_text(
        "# CrossHair property tests\n" if marked else "VALUE = 2\n", encoding="utf-8"
    )
    destination: list[tuple[list[str], dict[str, str] | None]] = []

    def run_check(
        command: list[str], *, env: dict[str, str] | None, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        destination.append((command, env))
        return subprocess.CompletedProcess(command, 0, "", "")

    info = env_manager.EnvManagerInfo(env_manager.EnvManager.PIP, True, [])
    monkeypatch.setattr(env_manager, "detect_env_manager", lambda _repo: info)
    monkeypatch.setattr(env_manager, "check_tool_in_env", lambda *_args: (True, "available"))
    monkeypatch.setattr("shutil.which", lambda tool: tool)
    monkeypatch.setattr(subprocess, "run", run_check)
    monkeypatch.setenv("PYTHONPATH", "existing-path")

    report = ReproChecker(tmp_path, crosshair_per_path_timeout=3).run_all_checks()
    assert report.get_exit_code() == 0
    assert report.passed_checks == 5
    commands = [command for command, _ in destination]
    assert commands[0] == ["ruff", "check", "--output-format=full", "src/", "tests/", "tools/"]
    assert commands[1] == ["basedpyright", "src/", "tests/", "tools/"]
    assert commands[3:] == [["pytest", "tests/contracts/", "-v"], ["pytest", "tests/smoke/", "-v"]]
    crosshair, environment = destination[2]
    targets = ["tools.property_checks"] if marked else ["project", "tools.property_checks"]
    assert crosshair == ["python", "-m", "crosshair", "check", *targets, "--per_path_timeout", "3"]
    assert environment is not None
    assert environment["PYTHONPATH"].split(os.pathsep)[-1] == "existing-path"
