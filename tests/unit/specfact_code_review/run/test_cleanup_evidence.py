from __future__ import annotations

from pathlib import Path

import pytest

from specfact_code_review.run.cleanup_evidence import (
    with_mutation_evidence,
    with_previewed_simplification_findings,
    with_refreshed_cleanup_forecast,
)
from specfact_code_review.run.findings import RemediationPacket, ReviewFinding, ReviewReport


def _finding(file_path: Path) -> ReviewFinding:
    return ReviewFinding(
        category="ai_bloat",
        severity="info",
        tool="ast",
        rule="ai-bloat.redundant-intermediate",
        file=str(file_path),
        line=2,
        message="Simplify local code.",
        fixable=True,
        confidence="high",
        rewrite_hint="Inline the temporary.",
        canonical_pattern="one-use-temporary",
        estimated_deletion_lines=1,
        guidance_kind="safe_mechanical",
        recommended_action="inline",
        clean_code_principle="kiss",
        rationale="The local variable is assigned once and returned.",
        safety_checks=["same expression is returned"],
        action_status="recommended",
    )


def _report(finding: ReviewFinding) -> ReviewReport:
    return ReviewReport(run_id="review", score=90, findings=[finding], summary="Simplify")


def test_with_previewed_simplification_findings_refreshes_forecast_without_fixable_findings(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
    finding = _finding(source).model_copy(update={"guidance_kind": "preserve", "preserve_reason": "public_api"})

    refreshed = with_previewed_simplification_findings(_report(finding), [source], lambda report: [])

    assert refreshed.cleanup_forecast is not None
    assert refreshed.findings[0].guidance_kind == "preserve"


def test_with_refreshed_cleanup_forecast_preserves_shadow_ci_exit(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
    report = ReviewReport(
        run_id="review",
        score=90,
        findings=[
            ReviewFinding(
                category="tool_error",
                severity="error",
                tool="ast",
                rule="tool_error",
                file=str(source),
                line=1,
                message="Unable to parse Python source.",
                fixable=False,
            )
        ],
        summary="Shadow mode.",
    ).model_copy(update={"ci_exit_code": 0})

    refreshed = with_refreshed_cleanup_forecast(report, [source])

    assert refreshed.ci_exit_code == 0
    assert refreshed.cleanup_forecast is not None


def test_with_previewed_simplification_findings_records_patch_ref(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n", encoding="utf-8"
    )
    finding = _finding(source)

    def _apply(report: ReviewReport) -> list[ReviewFinding]:
        preview_path = Path(report.findings[0].file)
        preview_path.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
        return [report.findings[0]]

    previewed = with_previewed_simplification_findings(_report(finding), [source], _apply)

    assert previewed.findings[0].remediation_packet is not None
    assert previewed.findings[0].remediation_packet.patch_forecast_refs == [f"preview:{source}:2"]
    assert source.read_text(encoding="utf-8").count("result") == 2


def test_with_previewed_simplification_findings_keeps_existing_packet_refs(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n", encoding="utf-8"
    )
    packet = RemediationPacket(
        issue="Simplify local code.",
        recommended_action="inline",
        safety_checks=["compare expression"],
        validation_plan=["run targeted tests"],
        safe_to_autofix=True,
        patch_forecast_refs=["preview:previous.py:1"],
    )
    finding = _finding(source).model_copy(update={"remediation_packet": packet})

    def _apply(report: ReviewReport) -> list[ReviewFinding]:
        preview_path = Path(report.findings[0].file)
        preview_path.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
        return [report.findings[0]]

    previewed = with_previewed_simplification_findings(_report(finding), [source], _apply)

    assert previewed.findings[0].remediation_packet is not None
    assert previewed.findings[0].remediation_packet.patch_forecast_refs == [
        "preview:previous.py:1",
        f"preview:{source}:2",
    ]


def test_with_mutation_evidence_keeps_non_safe_findings_without_signal(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
    finding = _finding(source).model_copy(update={"guidance_kind": "needs_tests"})

    report = with_mutation_evidence(_report(finding), [source])

    assert report.findings[0].signal_trace is None


def test_with_mutation_evidence_records_inconclusive_signal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
    monkeypatch.setattr("specfact_code_review.run.cleanup_evidence._mutation_tool_available", lambda: False)

    report = with_mutation_evidence(_report(_finding(source)), [source])

    assert report.findings[0].signal_trace is not None
    assert report.findings[0].signal_trace[-1].source == "mutation"
    assert report.findings[0].signal_trace[-1].value == "inconclusive: mutmut unavailable"


def test_with_mutation_evidence_records_scaffolding_signal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
    monkeypatch.setattr("specfact_code_review.run.cleanup_evidence._mutation_tool_available", lambda: True)

    report = with_mutation_evidence(_report(_finding(source)), [source])

    assert report.findings[0].signal_trace is not None
    assert report.findings[0].signal_trace[-1].value == "inconclusive: mutation scaffolding only"
