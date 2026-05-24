from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

import pytest
from pytest import MonkeyPatch

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.runner import (
    _coverage_findings,
    _preserve_reasons_for_finding,
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
        "ai_bloat",
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


def _simplification_finding(
    *,
    category: Literal["ai_bloat", "dry", "kiss"] = "ai_bloat",
    confidence: Literal["low", "medium", "high"] = "high",
    guidance_kind: Literal["safe_mechanical", "needs_tests", "design_judgment", "preserve"] | None = None,
) -> ReviewFinding:
    guided_fields = (
        {
            "recommended_action": "keep" if guidance_kind == "preserve" else "collapse",
            "clean_code_principle": "kiss",
            "rationale": "The repeated loop shape can be expressed directly.",
            "safety_checks": ["targeted tests cover the surrounding behavior"],
            "action_status": "recommended",
            "preserve_reason": "The wrapper is a compatibility boundary." if guidance_kind == "preserve" else None,
        }
        if guidance_kind is not None
        else {}
    )
    return ReviewFinding(
        category=category,
        severity="info",
        tool="ast",
        rule="ai-bloat.manual-accumulator-loop",
        file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
        line=10,
        message="Manual accumulator loop can be collapsed.",
        fixable=False,
        confidence=confidence,
        rewrite_hint="Replace the append loop with a list comprehension.",
        canonical_pattern="manual-accumulator-loop",
        intent_key="score-review",
        estimated_deletion_lines=3,
        guidance_kind=guidance_kind,
        **guided_fields,
    )


def test_run_review_calls_runners_in_order(monkeypatch: MonkeyPatch) -> None:
    calls: list[str] = []

    def _record(name: str) -> list[ReviewFinding]:
        calls.append(name)
        return []

    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: _record("ruff"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: _record("radon"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: _record("semgrep"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: _record("semgrep_bugs"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: _record("ai_bloat"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: _record("ast"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: _record("basedpyright"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: _record("pylint"))
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: _record("contracts"),
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (
            _record("testing"),
            {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 95.0},
        ),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert calls == [
        "ruff",
        "radon",
        "semgrep",
        "semgrep_bugs",
        "ai_bloat",
        "ast",
        "basedpyright",
        "pylint",
        "contracts",
        "testing",
    ]


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
        "specfact_code_review.run.runner.run_semgrep_bugs",
        lambda files: [_finding(tool="semgrep", rule="specfact-bugs-eval-exec", category="security")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            _finding(tool="ast", rule="ai-bloat.redundant-intermediate", category="ai_bloat", severity="info")
        ],
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
        lambda files, **_: [_finding(tool="contract_runner", rule="MISSING_ICONTRACT", category="contracts")],
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
        "semgrep",
        "ast",
        "ast",
        "basedpyright",
        "pylint",
        "contract_runner",
        "pytest",
    ]


def test_run_review_simplify_focus_keeps_only_simplification_queue(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [_finding(tool="ruff", rule="E501")])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [_simplification_finding(category="ai_bloat")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ast_clean_code",
        lambda files: [
            _simplification_finding(category="dry"),
            _simplification_finding(category="kiss", confidence="medium"),
            _finding(tool="ast", rule="solid.mixed-dependency-role", category="solid"),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
    )

    assert [(finding.category, finding.confidence) for finding in report.findings] == [
        ("ai_bloat", "high"),
        ("dry", "high"),
    ]
    assert report.schema_version == "1.3"
    assert report.overall_verdict == "PASS"


def test_run_review_simplify_enforce_fails_only_safe_mechanical_recommendations(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical"),
            _simplification_finding(category="ai_bloat", guidance_kind="needs_tests"),
            _simplification_finding(category="ai_bloat", guidance_kind="preserve"),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
        review_mode="enforce",
    )

    assert report.schema_version == "1.3"
    assert report.overall_verdict == "FAIL"
    assert report.ci_exit_code == 1
    assert report.simplification_summary is not None
    assert report.simplification_summary.blocking_simplification_count == 1
    assert report.cleanup_forecast is not None
    assert report.cleanup_forecast.by_guidance_kind["safe_mechanical"].count == 1
    assert report.cleanup_forecast.by_guidance_kind["needs_tests"].count == 1
    assert report.cleanup_forecast.by_guidance_kind["preserve"].count == 1
    assert report.cleanup_forecast.ai_bloat_index.weighted_bloat_points_per_kloc >= 0.0


def test_run_review_simplify_forecast_counts_loc_and_weighted_bloat(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "src/example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def one() -> int:\n"
        "    value = 1\n"
        "    return value\n"
        "\n"
        "# ignored comment\n"
        "def two() -> bool:\n"
        "    if True:\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "tests/test_example.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_example() -> None:\n    assert True\n", encoding="utf-8")
    safe = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical")
    needs_tests = _simplification_finding(category="ai_bloat", guidance_kind="needs_tests")
    design = _simplification_finding(category="ai_bloat", guidance_kind="design_judgment")
    preserve = _simplification_finding(category="ai_bloat", guidance_kind="preserve")
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [safe, needs_tests])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [design, preserve])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([source, test_file], no_tests=True, focus="simplify")

    assert report.cleanup_forecast is not None
    assert report.cleanup_forecast.reviewed_loc.production == 7
    assert report.cleanup_forecast.reviewed_loc.tests == 2
    assert report.cleanup_forecast.estimated_deletion_lines.low == 3
    assert report.cleanup_forecast.estimated_deletion_lines.expected == 6
    assert report.cleanup_forecast.estimated_deletion_lines.high == 9
    assert report.cleanup_forecast.ai_bloat_index.findings_per_kloc == pytest.approx(444.444, abs=0.001)
    assert report.cleanup_forecast.ai_bloat_index.weighted_bloat_points_per_kloc == pytest.approx(205.556, abs=0.001)
    assert report.cleanup_forecast.ai_bloat_index.cleanup_yield_loc_per_kloc == pytest.approx(666.667, abs=0.001)


def test_run_review_simplify_enforce_passes_design_and_preserve_guidance(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            _simplification_finding(category="ai_bloat", guidance_kind="design_judgment"),
            _simplification_finding(category="ai_bloat", guidance_kind="preserve"),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
        review_mode="enforce",
    )

    assert report.overall_verdict == "PASS"
    assert report.simplification_summary is not None
    assert report.simplification_summary.blocking_simplification_count == 0


def test_preserve_detection_covers_contract_public_protocol_cli_compat_and_load_bearing(tmp_path: Path) -> None:
    source = tmp_path / "api.py"
    source_text = (
        "from typing import Protocol\n"
        "import typer\n"
        "from abc import ABC, abstractmethod\n"
        "\n"
        "__all__ = ['exported']\n"
        "app = typer.Typer()\n"
        "\n"
        "@icontract.require(lambda value: value > 0)\n"
        "def contracted(value: int) -> int:\n"
        "    return value\n"
        "\n"
        "def exported() -> None:\n"
        "    return None\n"
        "\n"
        "class Handler(Protocol):\n"
        "    def handle(self, payload: str) -> str: ...\n"
        "\n"
        "class BaseHandler(ABC):\n"
        "    @abstractmethod\n"
        "    def abstract_handle(self, payload: str) -> str:\n"
        "        raise NotImplementedError\n"
        "\n"
        "    def concrete_helper(self, payload: str) -> str:\n"
        "        result = payload.strip()\n"
        "        return result\n"
        "\n"
        "@app.command()\n"
        "def cli_main() -> None:\n"
        "    return None\n"
        "\n"
        "# specfact: preserve(compat)\n"
        "def shim() -> None:\n"
        "    return None\n"
    )
    source.write_text(source_text, encoding="utf-8")

    def line_containing(text: str) -> int:
        return next(index for index, line in enumerate(source_text.splitlines(), start=1) if text in line)

    finding_lines = {
        "contract_lambda": line_containing("return value"),
        "public_api": line_containing("return None"),
        "protocol_member": line_containing("def handle"),
        "cli_callback": line_containing("def cli_main"),
        "compat_shim": line_containing("def shim"),
    }

    for expected_reason, line in finding_lines.items():
        finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
            update={"file": str(source), "line": line}
        )
        reasons = _preserve_reasons_for_finding(finding, load_bearing=False)
        assert expected_reason in {reason.reason for reason in reasons}

    abstract_finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": line_containing("raise NotImplementedError")}
    )
    abstract_reasons = _preserve_reasons_for_finding(abstract_finding, load_bearing=False)
    assert "protocol_member" in {reason.reason for reason in abstract_reasons}

    concrete_finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": line_containing("return result")}
    )
    concrete_reasons = _preserve_reasons_for_finding(concrete_finding, load_bearing=False)
    assert "protocol_member" not in {reason.reason for reason in concrete_reasons}

    load_bearing_finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": line_containing("def exported")}
    )
    reasons = _preserve_reasons_for_finding(load_bearing_finding, load_bearing=True)
    assert "load_bearing" in {reason.reason for reason in reasons}


def test_preserve_detection_treats_docstring_only_protocol_method_as_stub(tmp_path: Path) -> None:
    source = tmp_path / "api.py"
    source_text = (
        "from typing import Protocol\n"
        "\n"
        "class Handler(Protocol):\n"
        "    def handle(self, payload: str) -> str:\n"
        '        """Handle the payload."""\n'
    )
    source.write_text(source_text, encoding="utf-8")

    finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": 4}
    )
    reasons = _preserve_reasons_for_finding(finding, load_bearing=False)

    assert "protocol_member" in {reason.reason for reason in reasons}


def test_run_review_simplify_focus_preserves_tool_errors(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            ReviewFinding(
                category="tool_error",
                severity="error",
                tool="ast",
                rule="tool_error",
                file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
                line=1,
                message="Unable to parse Python source.",
                fixable=False,
            ),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
    )

    assert [finding.category for finding in report.findings] == ["tool_error"]
    assert report.overall_verdict == "FAIL"


def test_run_review_simplify_focus_excludes_partial_metadata_clean_code_findings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ast_clean_code",
        lambda files: [
            ReviewFinding(
                category="dry",
                severity="warning",
                tool="ast",
                rule="dry.duplicate-intent",
                file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
                line=10,
                message="Partial metadata must not enter simplify focus.",
                fixable=False,
                confidence="high",
            ),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
    )

    assert report.findings == []


def test_run_review_suppresses_cli_wrapper_noise_for_windows_style_paths(monkeypatch: MonkeyPatch) -> None:
    finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0914",
        file="packages\\specfact-code-review\\src\\specfact_code_review\\review\\commands.py",
        line=95,
        message="Too many local variables (24/20)",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/review/commands.py")], no_tests=True
    )

    assert report.findings == []


def test_run_review_keeps_r0902_for_non_dataclass_in_mixed_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "mixed.py"
    source.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass\n"
        "class Payload:\n"
        "    value: str\n"
        "\n"
        "class Stateful:\n"
        "    pass\n",
        encoding="utf-8",
    )
    finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0902",
        file=str(source),
        line=7,
        message="Too many instance attributes (9/7)",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([source], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["R0902"]


def test_run_review_suppresses_r0902_for_dataclass_target(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "payload.py"
    source.write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass Payload:\n    value: str\n",
        encoding="utf-8",
    )
    finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0902",
        file=str(source),
        line=4,
        message="Too many instance attributes (9/7)",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([source], no_tests=True)

    assert report.findings == []


def test_run_review_rejects_unknown_override_key() -> None:
    try:
        run_review([], unknown=True)
    except TypeError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("run_review accepted an unknown override")


def test_run_review_rejects_invalid_override_type() -> None:
    try:
        run_review([], no_tests="yes")
    except TypeError as exc:
        assert "no_tests" in str(exc)
    else:
        raise AssertionError("run_review accepted an invalid boolean override")


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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: noisy_findings[1:2])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: noisy_findings[:1],
    )
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: noisy_findings[1:])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: noisy_findings[:1],
    )
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [duplicate_code_finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
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
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [duplicate_code_finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
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
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/review/__init__.py")

    findings, coverage_by_source = _coverage_findings([source_file], {"files": {}})

    assert not findings
    assert coverage_by_source == {}


def test_coverage_findings_skips_package_initializers_omitted_from_coverage_reports() -> None:
    """``packages/**/__init__.py`` is omitted in coverage config; JSON has no per-file summary."""
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/tools/__init__.py")

    findings, coverage_by_source = _coverage_findings([source_file], {"files": {}})

    assert not findings
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
    assert command[0] == _pytest_python_executable()
    assert command[1] == "-c"
    assert "import specfact_code_review" in command[2]
    assert "--import-mode=importlib" in command
    assert "--cov-fail-under=0" in command


def test_pytest_python_executable_uses_current_interpreter() -> None:
    assert _pytest_python_executable() == sys.executable


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
        str(Path("packages/specfact-code-review/src").resolve()),
        str(workspace_root.resolve()),
        str(tmp_path / "existing"),
        str(bundle_root.resolve()),
    ]
