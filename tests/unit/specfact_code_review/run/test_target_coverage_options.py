"""Real native coverage controls retain source scope, reports and per-file policy."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from specfact_code_review.run.runner import evaluate_portable_pytest_coverage
from tests.unit.specfact_code_review.run.test_target_coverage import _project, _run


def test_native_cov_reset_restores_configured_source(tmp_path: Path) -> None:
    """Reset a preceding CLI source before bare --cov resolves the native config."""
    source = _project(tmp_path)
    completed, receipt = _run(source, tmp_path, ["--cov=unrelated", "--cov-reset", "--cov", "--cov-fail-under=0"])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert set(receipt["coverage"]["files"]) == {"app.py"}
    assert receipt["coverage_configuration"]["cov_source"] is None
    assert receipt["coverage_configuration"]["run"]["source"] == ["app"]


def test_native_custom_cov_config_preserves_filters_threshold_and_precision(tmp_path: Path) -> None:
    """An explicit Coverage config replaces project defaults without scope expansion."""
    source = _project(tmp_path)
    (source / "custom.coveragerc").write_text(
        "[run]\ninclude = app.py, unrelated.py\nomit = unrelated.py\n[report]\nfail_under = 76.5\nprecision = 3\n"
    )
    completed, receipt = _run(source, tmp_path, ["--cov", "--cov-config=custom.coveragerc", "--cov-report="])
    assert completed.returncode == 1
    assert set(receipt["coverage"]["files"]) == {"app.py"}
    assert receipt["coverage_policy"] == {
        "mode": "native",
        "threshold": 76.5,
        "precision": 3,
        "measured_total": 75.0,
        "native_threshold_failed": True,
    }
    configured = receipt["coverage_configuration"]
    assert configured["cov_config"] == "custom.coveragerc"
    assert configured["run"]["include"] == ["app.py", "unrelated.py"]
    assert configured["run"]["omit"] == ["unrelated.py"]


@pytest.mark.parametrize("native", ["", "--cov --cov-fail-under=0"])
def test_excluded_reviewed_source_remains_missing(tmp_path: Path, monkeypatch, native: str) -> None:
    """Neither native nor reviewer measurement may override a configured source omission."""
    source = _project(tmp_path, native=native)
    config = source / "pyproject.toml"
    config.write_text(config.read_text().replace('source=["app"]', 'source=["."]\nomit=["app.py"]'))
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "app.py" not in receipt["coverage"]["files"]
    monkeypatch.chdir(source)
    findings = evaluate_portable_pytest_coverage([Path("app.py")], {**receipt, "rootpath": str(source)})
    assert len(findings) == 1
    assert "Coverage data missing for app.py" in findings[0].message


def test_customer_lcov_report_matches_direct_native_pytest_bytes(tmp_path: Path) -> None:
    """The private export must leave the requested native report byte-identical."""
    source = _project(tmp_path, native="--cov --cov-fail-under=0 --cov-report=lcov:customer.lcov")
    direct = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "pytest_cov", "tests"],
        cwd=source,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "COVERAGE_FILE": str(tmp_path / "direct.coverage")},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert direct.returncode == 0, direct.stdout + direct.stderr
    report = source / "customer.lcov"
    expected = report.read_bytes()
    report.unlink()
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert report.read_bytes() == expected
    assert receipt["coverage"]["files"]["app.py"]["executed_lines"] == [1, 2, 3]


def _imbalanced_project(tmp_path: Path, selected: str, threshold: int) -> Path:
    """Separate selected-file coverage from a larger independent module's aggregate."""
    source = _project(tmp_path, native=f"--cov --cov-fail-under={threshold} --cov-report=")
    config = source / "pyproject.toml"
    config.write_text(config.read_text().replace('source=["app"]', 'source=["app", "ballast"]'))
    ballast = "\n".join(f"VALUE_{index} = {index}" for index in range(200)) + "\n"
    if selected == "complete":
        (source / "app.py").write_text("VALUE = 1\n")
        ballast = "def untouched():\n" + "\n".join(f"    value_{index} = {index}" for index in range(200)) + "\n"
    elif selected == "ninety":
        (source / "app.py").write_text(
            "\n".join(f"VALUE_{index} = {index}" for index in range(17))
            + "\ndef untouched():\n    value = 1\n    return value\n"
        )
    (source / "ballast.py").write_text(ballast)
    call = "app.covered() == 1" if selected == "seventy_five" else "app is not None"
    (source / "tests/test_app.py").write_text(
        f"import app\nimport ballast\ndef test_app():\n    assert {call}\n    assert ballast is not None\n"
    )
    return source


@pytest.mark.parametrize(("selected", "threshold", "required"), [("seventy_five", 0, 80), ("ninety", 95, 95)])
def test_high_aggregate_does_not_hide_low_selected_file(
    tmp_path: Path, monkeypatch, selected, threshold, required
) -> None:
    """Real aggregate success still enforces max(80, configured threshold) per reviewed file."""
    source = _imbalanced_project(tmp_path, selected, threshold)
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert receipt["coverage"]["totals"]["percent_covered"] > 95
    monkeypatch.chdir(source)
    findings = evaluate_portable_pytest_coverage([Path("app.py")], {**receipt, "rootpath": str(source)})
    assert len(findings) == 1
    assert (findings[0].rule, findings[0].severity) == ("TEST_COVERAGE_LOW", "error")
    assert f"required {required:.1f}%" in findings[0].message


def test_low_native_aggregate_remains_failure_with_fully_covered_selected_file(tmp_path: Path, monkeypatch) -> None:
    """A passing selected-file gate cannot erase the separately observed native aggregate failure."""
    source = _imbalanced_project(tmp_path, "complete", 80)
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 1
    assert receipt["coverage_policy"]["native_threshold_failed"] is True
    assert receipt["coverage"]["files"]["app.py"]["summary"]["percent_covered"] == 100
    assert receipt["coverage"]["totals"]["percent_covered"] < 80
    monkeypatch.chdir(source)
    assert not evaluate_portable_pytest_coverage([Path("app.py")], {**receipt, "rootpath": str(source)})
