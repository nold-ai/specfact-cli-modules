from __future__ import annotations

from typing import Literal

from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.run.scorer import score_review


def _finding(*, severity: Literal["error", "warning", "info"] = "warning", fixable: bool = False) -> ReviewFinding:
    return ReviewFinding(
        category="security",
        severity=severity,
        tool="ruff",
        rule="RULE001",
        file="src/example.py",
        line=10,
        message="Example finding.",
        fixable=fixable,
    )


def test_score_review_clean_run() -> None:
    result = score_review(findings=[])

    assert result.score == 100
    assert result.reward_delta == 20
    assert result.overall_verdict == "PASS"


def test_score_review_single_blocking_error() -> None:
    result = score_review(findings=[_finding(severity="error", fixable=False)])

    assert result.score == 85
    assert result.reward_delta == 5
    assert result.overall_verdict == "FAIL"


def test_score_review_single_fixable_error() -> None:
    result = score_review(findings=[_finding(severity="error", fixable=True)])

    assert result.score == 95
    assert result.reward_delta == 15
    assert result.overall_verdict == "PASS"


def test_score_review_warning_deductions() -> None:
    result = score_review(findings=[_finding(), _finding(), _finding()])

    assert result.score == 94
    assert result.reward_delta == 14


def test_score_review_verdict_thresholds() -> None:
    pass_result = score_review(findings=[_finding() for _ in range(7)])
    advisory_result = score_review(findings=[_finding() for _ in range(20)])
    fail_result = score_review(findings=[_finding() for _ in range(28)])

    assert pass_result.score == 86
    assert pass_result.overall_verdict == "PASS"
    assert advisory_result.score == 60
    assert advisory_result.overall_verdict == "PASS_WITH_ADVISORY"
    assert fail_result.score == 44
    assert fail_result.overall_verdict == "FAIL"


def test_score_review_applies_all_bonus_conditions() -> None:
    result = score_review(
        findings=[],
        zero_loc_violations=True,
        zero_complexity_violations=True,
        all_apis_have_icontract=True,
        coverage_90_plus=True,
        no_new_suppressions=True,
    )

    assert result.score == 120
    assert result.reward_delta == 40


def test_score_review_blocking_error_overrides_bonus_score() -> None:
    result = score_review(
        findings=[_finding(severity="error", fixable=False)],
        zero_loc_violations=True,
        zero_complexity_violations=True,
        all_apis_have_icontract=True,
        coverage_90_plus=True,
        no_new_suppressions=True,
    )

    assert result.score == 110
    assert result.overall_verdict == "FAIL"
    assert result.ci_exit_code == 1


def test_score_review_caps_score_at_120() -> None:
    result = score_review(
        findings=[],
        zero_loc_violations=True,
        zero_complexity_violations=True,
        all_apis_have_icontract=True,
        coverage_90_plus=True,
        no_new_suppressions=True,
    )

    assert result.score == 120
