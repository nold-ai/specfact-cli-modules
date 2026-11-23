"""Exercise the Codebase Repro command with the real core async scanner."""

from pathlib import Path

import pytest
import specfact_cli
import yaml
from specfact_cli.utils import env_manager
from typer.testing import CliRunner

from specfact_codebase.code.commands import app


BLOCKING = "import time\n\nasync def run():\n    time.sleep(1)\n"
SAFE = "import asyncio\n\nasync def run():\n    await asyncio.sleep(1)\n"
POLICY_PATH = Path("tools/semgrep/async.yml")


@pytest.fixture(name="repo")
def repro_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a target repository with no optional third-party analyzers."""

    def unavailable(_repo: Path, tool: str, _env: object) -> tuple[bool, str]:
        assert tool != "semgrep", "Repro requested the retired analyzer"
        return False, f"{tool} is unavailable"

    monkeypatch.setattr(env_manager, "check_tool_in_env", unavailable)
    return tmp_path


def run_repro(repo: Path, source: str, *flags: str):
    repo.joinpath("source.py").write_text(source, encoding="utf-8")
    report_path = repo / "report.yaml"
    report_path.touch()
    result = CliRunner().invoke(app, ["repro", "--repo", str(repo), "--out", str(report_path), *flags])
    assert repo.joinpath("source.py").read_text(encoding="utf-8") == source
    assert report_path.read_text(encoding="utf-8"), result.output
    return result, yaml.safe_load(report_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("source", "status"), [(SAFE, "passed"), (BLOCKING, "failed")], ids=["safe", "blocking"])
def test_explicit_async_check_reports_safe_and_blocking_cases(repo: Path, source: str, status: str) -> None:
    result, report = run_repro(repo, source, "--async-checks")
    check = next(check for check in report["checks"] if check["tool"] == "async-checks")
    assert check["status"] == status
    assert result.exit_code == int(status == "failed")
    findings = check["findings"]
    assert findings["engine"] == "python-ast"
    assert findings["targets_scanned"] == 1
    assert [finding["rule_id"] for finding in findings["findings"] if finding["severity"] == "error"] == (
        ["blocking-sleep-in-async"] if status == "failed" else []
    )


def test_custom_legacy_policy_fails_with_migration_guidance(repo: Path) -> None:
    policy = repo / POLICY_PATH
    policy.parent.mkdir(parents=True)
    policy.write_text("rules: []\n", encoding="utf-8")
    result, report = run_repro(repo, SAFE)
    check = next(check for check in report["checks"] if check["tool"] == "async-checks")
    assert check["exit_code"] == 2
    assert check["status"] == "failed"
    assert "Custom Semgrep async rules require migration" in result.output
    assert policy.read_text(encoding="utf-8") == "rules: []\n"


def test_async_fix_reports_manual_remediation(repo: Path) -> None:
    result, report = run_repro(repo, BLOCKING, "--async-checks", "--fix")
    check = next(check for check in report["checks"] if check["tool"] == "async-checks")
    assert check["exit_code"] == 2
    assert "Apply manual fixes" in result.output


def test_missing_core_scanner_fails_with_upgrade_guidance(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(specfact_cli, "__file__", str(repo / "old-core" / "__init__.py"))
    result, report = run_repro(repo, SAFE, "--async-checks")
    check = next(check for check in report["checks"] if check["tool"] == "async-checks")
    assert result.exit_code == 1
    assert check["status"] == "failed"
    assert "Upgrade SpecFact CLI" in result.output


def test_repro_keeps_async_checks_optional(repo: Path) -> None:
    result, report = run_repro(repo, BLOCKING)
    assert result.exit_code == 0
    assert all(check["tool"] not in {"semgrep", "async-checks"} for check in report["checks"])
