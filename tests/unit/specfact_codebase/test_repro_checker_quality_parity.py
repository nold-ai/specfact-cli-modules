from __future__ import annotations

import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from specfact_cli.utils.env_manager import EnvManager, EnvManagerInfo

from specfact_codebase.validators.repro_checker import (
    CheckResult,
    CheckStatus,
    ReproChecker,
    ReproReport,
    _extract_basedpyright_findings,
    _module_name_from_path,
)


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (".", None),
        ("__init__.py", None),
        ("pkg/__init__.py", "pkg"),
        ("pkg/module.py", "pkg.module"),
        ("pkg/module.txt", "pkg.module.txt"),
        (".py", None),
        (None, None),
    ],
)
def test_module_name_conversion_keeps_existing_names(
    tmp_path: Path, relative: str | None, expected: str | None
) -> None:
    path = tmp_path / relative if relative is not None else tmp_path.parent / "outside.py"
    assert _module_name_from_path(tmp_path, path) == expected


class TestReproChecker:
    def test_run_check_tool_missing(self, tmp_path: Path):
        checker = ReproChecker(repo_path=tmp_path, budget=30)
        result = checker.run_check(
            name="Test Check",
            tool="nonexistent_tool",
            command=["nonexistent_tool", "check"],
            timeout=10,
            skip_if_missing=True,
        )
        assert result.status == CheckStatus.SKIPPED
        assert "not found" in result.error

    def test_run_check_passed(self, tmp_path: Path):
        checker = ReproChecker(repo_path=tmp_path, budget=30)

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            result = checker.run_check(
                name="Test Check",
                tool="test",
                command=["test", "check"],
                timeout=10,
                skip_if_missing=False,
            )

            assert result.status == CheckStatus.PASSED
            assert result.exit_code == 0
            assert result.output == "Success"
            mock_run.assert_called_once()

    def test_run_check_failed(self, tmp_path: Path):
        checker = ReproChecker(repo_path=tmp_path, budget=30)

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "Error occurred"
            mock_run.return_value = mock_proc

            result = checker.run_check(
                name="Test Check",
                tool="test",
                command=["test", "check"],
                timeout=10,
                skip_if_missing=False,
            )

            assert result.status == CheckStatus.FAILED
            assert result.exit_code == 1
            assert result.error == "Error occurred"

    def test_run_check_timeout(self, tmp_path: Path):
        checker = ReproChecker(repo_path=tmp_path, budget=30)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("test", 10)

            result = checker.run_check(
                name="Test Check",
                tool="test",
                command=["test", "check"],
                timeout=10,
                skip_if_missing=False,
            )

            assert result.status == CheckStatus.TIMEOUT
            assert result.timeout is True
            assert "timed out" in result.error

    def test_run_check_budget_exceeded(self, tmp_path: Path):
        checker = ReproChecker(repo_path=tmp_path, budget=1)
        checker.start_time = time.time() - 2

        result = checker.run_check(
            name="Test Check",
            tool="test",
            command=["test", "check"],
            timeout=10,
            skip_if_missing=False,
        )

        assert result.status == CheckStatus.TIMEOUT
        assert result.timeout is True
        assert checker.report.budget_exceeded is True

    def test_run_check_crosshair_side_effect_includes_target_command(self, tmp_path: Path):
        checker = ReproChecker(repo_path=tmp_path, budget=30)

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 2
            mock_proc.stdout = ""
            mock_proc.stderr = "SideEffectDetected: import side effect"
            mock_run.return_value = mock_proc

            result = checker.run_check(
                name="Contract exploration (CrossHair)",
                tool="crosshair",
                command=["python", "-m", "crosshair", "check", "specfact_codebase.repro.commands"],
                timeout=10,
                skip_if_missing=False,
            )

            assert result.status == CheckStatus.SKIPPED
            assert "Target command:" in result.error
            assert "specfact_codebase.repro.commands" in result.error

    def test_run_all_checks_with_ruff(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30)

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Linting passed"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/ruff"),
            ):
                report = checker.run_all_checks()

            assert report.total_checks >= 1
            ruff_check = next((c for c in report.checks if c.tool == "ruff"), None)
            assert ruff_check is not None
            assert ruff_check.status == CheckStatus.PASSED

    def test_run_all_checks_fail_fast(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30, fail_fast=True)

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "Error"
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/ruff"),
            ):
                report = checker.run_all_checks()

            assert report.failed_checks > 0

    def test_run_all_checks_crosshair_required_converts_skipped_to_failed(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30, crosshair_required=True)
        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        def _fake_run_check(
            name: str,
            tool: str,
            command: list[str],
            timeout: int | None,
            skip_if_missing: bool,
            env: dict[str, str] | None,
        ) -> CheckResult:
            _ = (command, timeout, skip_if_missing, env)
            if tool == "crosshair":
                return CheckResult(
                    name="Contract exploration (CrossHair)",
                    tool="crosshair",
                    status=CheckStatus.SKIPPED,
                    error="CrossHair side-effect detected",
                )
            return CheckResult(name=name, tool=tool, status=CheckStatus.PASSED, duration=0.1)

        with (
            patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
            patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch.object(checker, "run_check", side_effect=_fake_run_check),
        ):
            report = checker.run_all_checks()

        crosshair_check = next(check for check in report.checks if check.tool == "crosshair")
        assert crosshair_check.status == CheckStatus.FAILED
        assert report.crosshair_requirement_violated is True
        assert report.get_exit_code() == 1

    def test_repro_checker_fix_flag(self, tmp_path: Path):
        semgrep_config = tmp_path / "tools" / "semgrep" / "async.yml"
        semgrep_config.parent.mkdir(parents=True, exist_ok=True)
        semgrep_config.write_text("rules:\n  - id: test-rule\n    patterns:\n      - pattern: test\n")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30, fix=True)
        assert checker.fix is True

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = ""
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/semgrep"),
            ):
                checker.run_all_checks()

            semgrep_calls = [call for call in mock_run.call_args_list if "semgrep" in str(call)]
            if semgrep_calls:
                semgrep_call = semgrep_calls[0]
                command = semgrep_call[0][0] if isinstance(semgrep_call[0], tuple) else semgrep_call[0]
                assert "--autofix" in command or any("--autofix" in str(arg) for arg in command)

    def test_repro_checker_fix_flag_disabled(self, tmp_path: Path):
        semgrep_config = tmp_path / "tools" / "semgrep" / "async.yml"
        semgrep_config.parent.mkdir(parents=True, exist_ok=True)
        semgrep_config.write_text("rules:\n  - id: test-rule\n    patterns:\n      - pattern: test\n")

        checker = ReproChecker(repo_path=tmp_path, budget=30, fix=False)
        assert checker.fix is False

    def test_repro_checker_crosshair_per_path_timeout_passed_to_command(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")
        (src_dir / "foo.py").write_text("def bar() -> int:\n    return 1\n")

        checker = ReproChecker(repo_path=tmp_path, budget=30, crosshair_per_path_timeout=60)
        assert checker.crosshair_per_path_timeout == 60

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with (
            patch("specfact_codebase.validators.repro_checker.subprocess.run") as mock_run,
            patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
            patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
            patch("shutil.which", return_value="/usr/bin/crosshair"),
        ):
            mock_run.return_value = mock_proc
            checker.run_all_checks()

            crosshair_calls = [c for c in mock_run.call_args_list if c[0][0] and "crosshair" in str(c[0][0])]
            assert crosshair_calls, "CrossHair should have been invoked"
            cmd = crosshair_calls[0][0][0]
            flat = list(cmd) if not isinstance(cmd, list) else cmd
            assert "--per_path_timeout" in flat
            idx = flat.index("--per_path_timeout")
            assert flat[idx + 1] == "60"

    def test_repro_report_add_check(self):
        report = ReproReport()

        result1 = CheckResult(
            name="Check 1",
            tool="test",
            status=CheckStatus.PASSED,
            duration=1.0,
        )
        report.add_check(result1)
        assert report.total_checks == 1
        assert report.passed_checks == 1
        assert report.total_duration == 1.0

        result2 = CheckResult(
            name="Check 2",
            tool="test",
            status=CheckStatus.FAILED,
            duration=2.0,
        )
        report.add_check(result2)
        assert report.total_checks == 2
        assert report.passed_checks == 1
        assert report.failed_checks == 1
        assert report.total_duration == 3.0

    def test_repro_report_get_exit_code(self):
        report = ReproReport()

        report.add_check(CheckResult(name="Check", tool="test", status=CheckStatus.PASSED))
        assert report.get_exit_code() == 0

        report.add_check(CheckResult(name="Check", tool="test", status=CheckStatus.FAILED))
        assert report.get_exit_code() == 1

        report.budget_exceeded = True
        assert report.get_exit_code() == 2

    def test_repro_report_get_exit_code_timeout(self):
        report = ReproReport()
        report.add_check(CheckResult(name="Check", tool="test", status=CheckStatus.TIMEOUT, timeout=True))
        assert report.get_exit_code() == 2

    def test_repro_report_metadata(self):
        report = ReproReport()
        report.repo_path = "/test/repo"
        report.budget = 120
        report.active_plan_path = ".specfact/plans/main.bundle.yaml"
        report.enforcement_config_path = ".specfact/gates/config/enforcement.yaml"
        report.enforcement_preset = "balanced"
        report.fix_enabled = True
        report.fail_fast = False

        report_dict = report.to_dict()

        assert "metadata" in report_dict
        metadata = report_dict["metadata"]
        assert metadata["repo_path"] == "/test/repo"
        assert metadata["budget"] == 120
        assert metadata["active_plan_path"] == ".specfact/plans/main.bundle.yaml"
        assert metadata["enforcement_config_path"] == ".specfact/gates/config/enforcement.yaml"
        assert metadata["enforcement_preset"] == "balanced"

    def test_extract_basedpyright_findings_parses_pretty_output(self):
        output = (
            "/tmp/a.py\n"
            '  /tmp/a.py:10:4 - warning: Type of "x" is unknown (reportUnknownMemberType)\n'
            "0 errors, 1 warnings, 0 notes\n"
        )
        findings = _extract_basedpyright_findings(output)
        assert findings["total_errors"] == 0
        assert findings["total_warnings"] == 1

    def test_run_all_checks_metadata_uses_absolute_fallback_when_outside_repo(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")
        checker = ReproChecker(repo_path=tmp_path, budget=30)

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        outside_dir = Path("/tmp/not-under-repo")
        outside_dir.mkdir(parents=True, exist_ok=True)
        outside_plan = outside_dir / "main.bundle.yaml"
        outside_enforce = outside_dir / "enforcement.yaml"
        outside_plan.write_text("plan: demo\n", encoding="utf-8")
        outside_enforce.write_text("preset: balanced\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "ok"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/ruff"),
                patch(
                    "specfact_cli.utils.structure.SpecFactStructure.get_default_plan_path", return_value=outside_plan
                ),
                patch(
                    "specfact_cli.utils.structure.SpecFactStructure.get_enforcement_config_path",
                    return_value=outside_enforce,
                ),
                patch("specfact_cli.utils.yaml_utils.load_yaml", return_value=None),
                patch("specfact_codebase.validators.repro_checker.console") as console_mock,
            ):
                report = checker.run_all_checks()

        assert report.active_plan_path == str(outside_plan.resolve())
        assert report.enforcement_config_path == str(outside_enforce.resolve())
        console_calls = "\n".join(str(call) for call in console_mock.print.call_args_list)
        assert "Could not collect metadata" not in console_calls

    def test_repro_report_metadata_minimal(self):
        report = ReproReport()
        report_dict = report.to_dict()

        assert "metadata" in report_dict
        assert "timestamp" in report_dict["metadata"]

    def test_run_all_checks_with_environment_detection_hatch(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.hatch]
version = "1.0.0"
"""
        )
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30)

        env_info = EnvManagerInfo(
            manager=EnvManager.HATCH,
            available=True,
            command_prefix=["hatch", "run"],
            message="Detected hatch",
        )

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/ruff"),
            ):
                checker.run_all_checks()

            ruff_calls = [
                call
                for call in mock_run.call_args_list
                if "ruff" in str(call.args[0] if hasattr(call, "args") else call)
            ]
            if ruff_calls:
                call_args = ruff_calls[0].args[0] if hasattr(ruff_calls[0], "args") else ruff_calls[0][0]
                assert "hatch" in str(call_args) or any("hatch" in str(arg) for arg in call_args)

    def test_run_all_checks_with_environment_detection_poetry(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "test-project"
"""
        )
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30)

        env_info = EnvManagerInfo(
            manager=EnvManager.POETRY,
            available=True,
            command_prefix=["poetry", "run"],
            message="Detected poetry",
        )

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/ruff"),
            ):
                report = checker.run_all_checks()

            assert report.total_checks >= 1

    def test_run_all_checks_tool_not_available(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        checker = ReproChecker(repo_path=tmp_path, budget=30)

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        with (
            patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
            patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(False, "Tool not found")),
        ):
            report = checker.run_all_checks()

            skipped_checks = [c for c in report.checks if c.status == CheckStatus.SKIPPED]
            assert len(skipped_checks) > 0
            assert all("not found" in c.error.lower() or "not available" in c.error.lower() for c in skipped_checks)

    def test_run_all_checks_source_detection(self, tmp_path: Path):
        package_dir = tmp_path / "my_package"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "my-package"
"""
        )

        checker = ReproChecker(repo_path=tmp_path, budget=30)

        env_info = EnvManagerInfo(
            manager=EnvManager.UNKNOWN,
            available=True,
            command_prefix=[],
            message="Test",
        )

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            with (
                patch("specfact_cli.utils.env_manager.detect_env_manager", return_value=env_info),
                patch("specfact_cli.utils.env_manager.check_tool_in_env", return_value=(True, None)),
                patch("shutil.which", return_value="/usr/bin/ruff"),
            ):
                report = checker.run_all_checks()

            assert report.total_checks >= 1
