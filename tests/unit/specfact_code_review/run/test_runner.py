from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pytest import MonkeyPatch

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.runner import (
    _coverage_findings,
    _pytest_python_executable,
    _pytest_targets,
    _run_pytest_with_coverage,
    run_review,
    run_tdd_gate,
)


def _finding(
    *,
    tool: str,
    rule: str,
    severity: Literal["error", "warning", "info"] = "warning",
    category: Literal[
        "clean_code",
        "security",
        "type_safety",
        "contracts",
        "testing",
        "style",
        "architecture",
        "tool_error",
        "naming",
        "kiss",
        "yagni",
        "dry",
        "solid",
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: _record("ast"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: _record("basedpyright"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: _record("pylint"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: _record("contracts"))
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (
            _record("testing"),
            {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 95.0},
        ),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert calls == ["ruff", "radon", "semgrep", "ast", "basedpyright", "pylint", "contracts", "testing"]


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
        "specfact_code_review.run.runner.run_ast_clean_code",
        lambda files: [_finding(tool="ast", rule="dry.duplicate-function-shape", category="dry")],
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
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (
            [_finding(tool="pytest", rule="TEST_COVERAGE_LOW", category="testing")],
            {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 65.0},
        ),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert [finding.tool for finding in report.findings] == [
        "ruff",
        "radon",
        "semgrep",
        "ast",
        "basedpyright",
        "pylint",
        "contract_runner",
        "pytest",
    ]


def test_run_tdd_gate_reports_missing_test_file() -> None:
    findings = run_tdd_gate([Path("packages/specfact-code-review/src/specfact_code_review/rules/commands.py")])

    assert len(findings) == 1
    assert findings[0].category == "testing"
    assert findings[0].severity == "error"
    assert findings[0].rule == "TEST_FILE_MISSING"


def test_run_review_skips_tdd_gate_when_no_tests_is_true(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (_ for _ in ()).throw(AssertionError("_evaluate_tdd_gate should not be called")),
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: ([], {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 95.0}),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert report.summary


def test_run_review_suppresses_known_test_noise_by_default(monkeypatch: MonkeyPatch) -> None:
    noisy_findings = [
        ReviewFinding(
            category="contracts",
            severity="warning",
            tool="contract_runner",
            rule="MISSING_ICONTRACT",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=10,
            message="test noise",
            fixable=False,
        ),
        ReviewFinding(
            category="style",
            severity="warning",
            tool="pylint",
            rule="W0212",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=11,
            message="protected helper access",
            fixable=False,
        ),
        ReviewFinding(
            category="style",
            severity="warning",
            tool="ruff",
            rule="F821",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=12,
            message="real test issue",
            fixable=False,
        ),
    ]
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: noisy_findings[2:])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: noisy_findings[1:2])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: noisy_findings[:1])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([Path("tests/unit/specfact_code_review/run/test_commands.py")], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["F821"]


def test_run_review_can_include_known_test_noise(monkeypatch: MonkeyPatch) -> None:
    noisy_findings = [
        ReviewFinding(
            category="contracts",
            severity="warning",
            tool="contract_runner",
            rule="MISSING_ICONTRACT",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=10,
            message="test noise",
            fixable=False,
        ),
        ReviewFinding(
            category="style",
            severity="warning",
            tool="pylint",
            rule="W0212",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=11,
            message="protected helper access",
            fixable=False,
        ),
    ]
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: noisy_findings[1:])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: noisy_findings[:1])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("tests/unit/specfact_code_review/run/test_commands.py")],
        no_tests=True,
        include_noise=True,
    )

    assert [finding.rule for finding in report.findings] == ["W0212", "MISSING_ICONTRACT"]


def test_run_review_emits_advisory_checklist_finding_in_pr_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_MODE", "true")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_TITLE", "Expand code review coverage")
    monkeypatch.setenv(
        "SPECFACT_CODE_REVIEW_PR_BODY", "Adds new review runners without documenting the clean-code rationale."
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["clean-code.pr-checklist-missing-rationale"]
    assert report.findings[0].severity == "info"
    assert report.overall_verdict == "PASS"


def test_run_review_requires_explicit_pr_mode_token_for_clean_code_reasoning(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_MODE", "true")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_TITLE", "Expand code review coverage")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_BODY", "We are renaming helper functions for clarity.")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_PROPOSAL", "")

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["clean-code.pr-checklist-missing-rationale"]


def test_run_review_suppresses_global_duplicate_code_noise_by_default(monkeypatch: MonkeyPatch) -> None:
    duplicate_code_finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0801",
        file="scripts/link_dev_module.py",
        line=1,
        message="Similar lines in 2 files",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [duplicate_code_finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([Path("scripts/link_dev_module.py")], no_tests=True)

    assert report.findings == []


def test_pytest_targets_collapses_only_specific_subdirectories(tmp_path: Path) -> None:
    run_tests = tmp_path / "tests/unit/specfact_code_review/run"
    run_tests.mkdir(parents=True)
    first = run_tests / "test_commands.py"
    second = run_tests / "test_runner.py"
    first.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    second.write_text("def test_two():\n    assert True\n", encoding="utf-8")

    assert _pytest_targets([first.relative_to(tmp_path), second.relative_to(tmp_path)]) == [
        Path("tests/unit/specfact_code_review/run")
    ]


def test_pytest_targets_keeps_files_when_common_root_is_too_broad(tmp_path: Path) -> None:
    run_tests = tmp_path / "tests/unit/specfact_code_review/run"
    review_tests = tmp_path / "tests/unit/specfact_code_review/review"
    run_tests.mkdir(parents=True)
    review_tests.mkdir(parents=True)
    first = run_tests / "test_commands.py"
    second = review_tests / "test_commands.py"
    first.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    second.write_text("def test_two():\n    assert True\n", encoding="utf-8")

    assert _pytest_targets([first.relative_to(tmp_path), second.relative_to(tmp_path)]) == [
        Path("tests/unit/specfact_code_review/run/test_commands.py"),
        Path("tests/unit/specfact_code_review/review/test_commands.py"),
    ]


def test_run_review_can_include_global_duplicate_code_noise(monkeypatch: MonkeyPatch) -> None:
    duplicate_code_finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0801",
        file="scripts/link_dev_module.py",
        line=1,
        message="Similar lines in 2 files",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [duplicate_code_finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([Path("scripts/link_dev_module.py")], no_tests=True, include_noise=True)

    assert [finding.rule for finding in report.findings] == ["R0801"]


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


def test_coverage_findings_skips_package_initializers_without_coverage_data() -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/tools/__init__.py")

    findings, coverage_by_source = _coverage_findings([source_file], {"files": {}})

    assert findings == []
    assert coverage_by_source == {}


def test_run_pytest_with_coverage_disables_global_fail_under(monkeypatch: MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _run_pytest_with_coverage([Path("tests/unit/specfact_code_review/run/test_commands.py")])

    command = recorded["command"]
    assert isinstance(command, list)
    assert command[:3] == [_pytest_python_executable(), "-m", "pytest"]
    assert "--cov-fail-under=0" in command


def test_pytest_python_executable_prefers_local_venv(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    venv_python = tmp_path / ".venv/bin/python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/bin/sh\n", encoding="utf-8")
    venv_python.chmod(0o755)

    assert _pytest_python_executable() == str(venv_python.resolve())


def test_pytest_targets_collapse_multi_file_batch_to_common_test_directory() -> None:
    test_files = [
        Path("tests/unit/specfact_code_review/run/test_commands.py"),
        Path("tests/unit/specfact_code_review/run/test_runner.py"),
    ]

    assert _pytest_targets(test_files) == [Path("tests/unit/specfact_code_review/run")]


def test_run_pytest_with_coverage_propagates_pythonpath(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    recorded: dict[str, object] = {}
    bundle_root = tmp_path / "bundle-src"
    bundle_root.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.chdir(workspace_root)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "existing"))
    monkeypatch.setattr(sys, "path", [str(bundle_root), "", str(tmp_path / "missing")])

    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _run_pytest_with_coverage([Path("tests/unit/specfact_code_review/run/test_commands.py")])

    kwargs = recorded["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["PYTHONPATH"].split(os.pathsep) == [
        str(workspace_root.resolve()),
        str(Path("packages/specfact-code-review/src").resolve()),
        str(tmp_path / "existing"),
        str(bundle_root.resolve()),
    ]
