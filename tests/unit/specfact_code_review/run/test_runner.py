from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

from pytest import MonkeyPatch

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.runner import run_review, run_tdd_gate


def _finding(
    *,
    tool: str,
    rule: str,
    severity: Literal["error", "warning", "info"] = "warning",
    category: Literal[
        "clean_code", "security", "type_safety", "contracts", "testing", "style", "architecture", "tool_error"
    ] = "style",
) -> ReviewFinding:
    return ReviewFinding(
        category=category,
        severity=severity,
        tool=tool,
        rule=rule,
        file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
        line=10,
        message=f"{tool} finding",
        fixable=False,
    )


def test_run_review_calls_runners_in_order(monkeypatch: MonkeyPatch) -> None:
    calls: list[str] = []

    def _record(name: str) -> list[ReviewFinding]:
        calls.append(name)
        return []

    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: _record("ruff"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: _record("radon"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: _record("semgrep"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: _record("basedpyright"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: _record("pylint"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: _record("contracts"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_tdd_gate", lambda files: _record("testing"))

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert calls == ["ruff", "radon", "semgrep", "basedpyright", "pylint", "contracts", "testing"]


def test_run_review_merges_findings_from_all_runners(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [_finding(tool="ruff", rule="E501")])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_radon", lambda files: [_finding(tool="radon", rule="CC13")]
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_semgrep",
        lambda files: [_finding(tool="semgrep", rule="cross-layer-call", category="architecture")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_basedpyright",
        lambda files: [_finding(tool="basedpyright", rule="reportArgumentType", category="type_safety")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_pylint",
        lambda files: [_finding(tool="pylint", rule="W0702", category="architecture")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files: [_finding(tool="contract_runner", rule="MISSING_ICONTRACT", category="contracts")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_tdd_gate",
        lambda files: [_finding(tool="pytest", rule="TEST_COVERAGE_LOW", category="testing")],
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert [finding.tool for finding in report.findings] == [
        "ruff",
        "radon",
        "semgrep",
        "basedpyright",
        "pylint",
        "contract_runner",
        "pytest",
    ]


def test_run_tdd_gate_reports_missing_test_file() -> None:
    findings = run_tdd_gate([Path("packages/specfact-code-review/src/specfact_code_review/review/commands.py")])

    assert len(findings) == 1
    assert findings[0].category == "testing"
    assert findings[0].severity == "error"
    assert findings[0].rule == "TEST_FILE_MISSING"


def test_run_review_skips_tdd_gate_when_no_tests_is_true(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_tdd_gate",
        lambda files: (_ for _ in ()).throw(AssertionError("run_tdd_gate should not be called")),
    )

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
    )

    assert report.findings == []


def test_run_review_returns_review_report(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_tdd_gate", lambda files: [])

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert report.summary


def test_run_tdd_gate_warns_when_coverage_is_below_threshold(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")
    coverage_payload = {
        "files": {
            str(source_file): {
                "summary": {
                    "percent_covered": 65.0,
                }
            }
        }
    }

    def _fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        coverage_arg = next(arg for arg in command if arg.startswith("--cov-report=json:"))
        coverage_path = Path(coverage_arg.split(":", 1)[1])
        coverage_path.write_text(json.dumps(coverage_payload), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests/unit/specfact_code_review/run").mkdir(parents=True)
    (tmp_path / "tests/unit/specfact_code_review/run/test_scorer.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )

    findings = run_tdd_gate([source_file])

    assert len(findings) == 1
    assert findings[0].rule == "TEST_COVERAGE_LOW"
    assert findings[0].severity == "warning"


def test_run_tdd_gate_maps_absolute_source_paths(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    source_file = tmp_path / "packages/specfact-code-review/src/specfact_code_review/review/commands.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("def command() -> None:\n    pass\n", encoding="utf-8")

    findings = run_tdd_gate([source_file.resolve()])

    assert len(findings) == 1
    assert findings[0].rule == "TEST_FILE_MISSING"
    assert findings[0].file == str(source_file.resolve())


def test_run_tdd_gate_returns_no_finding_for_passing_tests_with_sufficient_coverage(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")
    coverage_payload = {
        "files": {
            str(source_file): {
                "summary": {
                    "percent_covered": 85.0,
                }
            }
        }
    }

    def _fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        coverage_arg = next(arg for arg in command if arg.startswith("--cov-report=json:"))
        coverage_path = Path(coverage_arg.split(":", 1)[1])
        coverage_path.write_text(json.dumps(coverage_payload), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests/unit/specfact_code_review/run").mkdir(parents=True)
    (tmp_path / "tests/unit/specfact_code_review/run/test_scorer.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )

    findings = run_tdd_gate([source_file])

    assert findings == []
