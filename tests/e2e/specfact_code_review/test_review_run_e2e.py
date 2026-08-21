from __future__ import annotations

import importlib.metadata
import importlib.resources
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run.findings import ReviewReport


runner = CliRunner()
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "review"
REQUIRED_TOOLS = ("ruff", "radon", "basedpyright", "pylint", "semgrep")


def _consumer_matrix() -> dict[str, Any]:
    resource = importlib.resources.files("specfact_code_review").joinpath(
        "resources", "contracts", "review-report-schema-1.6-consumer-matrix.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


@pytest.mark.e2e
def test_core_0_55_1_runtime_loads_schema_1_6_consumer_matrix() -> None:
    from specfact_code_review.run import findings

    assert importlib.metadata.version("specfact-cli") == "0.55.1"
    matrix = _consumer_matrix()

    result = findings.validate_consumer_matrix(matrix)

    assert result.status == "PASS"
    assert result.exercised_statuses == ("FAIL", "NOT_APPLICABLE", "PASS", "UNKNOWN")


@pytest.mark.e2e
def test_consumer_matrix_rejects_suppression_catalog_identity_mismatch() -> None:
    from specfact_code_review.run import findings

    matrix = _consumer_matrix()
    matrix["accepted_pr_range_envelope"]["suppression_catalog_digest"] = "sha256:" + "f" * 64

    result = findings.validate_consumer_matrix(matrix)

    assert result.status == "UNKNOWN"
    assert result.reason == "suppression_catalog_identity_mismatch"


def _skip_if_tools_missing() -> None:
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Missing required review tools: {', '.join(missing)}")


@pytest.mark.e2e
def test_review_run_clean_fixture_passes(tmp_path: Path) -> None:
    _skip_if_tools_missing()
    out = tmp_path / "review-report.json"

    result = runner.invoke(
        app,
        ["review", "run", "--json", "--out", str(out), str(FIXTURE_ROOT / "clean_module.py")],
    )

    assert result.exit_code == 0
    report = ReviewReport.model_validate_json(out.read_text(encoding="utf-8"))
    assert report.overall_verdict in {"PASS", "PASS_WITH_ADVISORY"}
    assert report.ci_exit_code == 0


@pytest.mark.e2e
def test_review_run_dirty_fixture_fails(tmp_path: Path) -> None:
    _skip_if_tools_missing()
    out = tmp_path / "review-report.json"

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--enforcement",
            "full",
            "--json",
            "--out",
            str(out),
            str(FIXTURE_ROOT / "dirty_module.py"),
        ],
    )

    assert result.exit_code == 1
    report = ReviewReport.model_validate_json(out.read_text(encoding="utf-8"))
    assert report.overall_verdict == "FAIL"
    assert any(finding.rule in {"CC17", "tool_error"} for finding in report.findings)
