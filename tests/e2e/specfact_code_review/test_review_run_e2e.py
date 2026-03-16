from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run.findings import ReviewReport


runner = CliRunner()
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "review"
REQUIRED_TOOLS = ("ruff", "radon", "basedpyright", "pylint", "semgrep")


def _skip_if_tools_missing() -> None:
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Missing required review tools: {', '.join(missing)}")


@pytest.mark.e2e
def test_review_run_clean_fixture_passes() -> None:
    _skip_if_tools_missing()

    result = runner.invoke(app, ["review", "run", "--json", str(FIXTURE_ROOT / "clean_module.py")])

    assert result.exit_code == 0
    report = ReviewReport.model_validate_json(result.output)
    assert report.overall_verdict == "PASS"


@pytest.mark.e2e
def test_review_run_dirty_fixture_fails() -> None:
    _skip_if_tools_missing()

    result = runner.invoke(app, ["review", "run", "--json", str(FIXTURE_ROOT / "dirty_module.py")])

    assert result.exit_code == 1
    report = ReviewReport.model_validate_json(result.output)
    assert report.overall_verdict == "FAIL"
    assert any(finding.rule in {"CC16", "MISSING_ICONTRACT", "tool_error"} for finding in report.findings)
