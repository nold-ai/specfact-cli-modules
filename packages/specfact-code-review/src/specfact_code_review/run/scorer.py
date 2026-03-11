"""Scoring helpers for structured review runs."""

from __future__ import annotations

from typing import Literal

from beartype import beartype
from icontract import ensure, require
from pydantic import BaseModel, Field

from specfact_code_review.run.findings import ReviewFinding


PASS = "PASS"
PASS_WITH_ADVISORY = "PASS_WITH_ADVISORY"
FAIL = "FAIL"


class ReviewScore(BaseModel):
    """Computed score summary for a review run."""

    score: int = Field(..., ge=0, le=120, description="Score in the inclusive range 0..120.")
    reward_delta: int = Field(..., description="Reward delta derived from score - 80.")
    overall_verdict: Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"] = Field(..., description="Derived verdict.")
    ci_exit_code: Literal[0, 1] = Field(..., description="CI-compatible exit code.")


def _bonus_points(
    zero_loc_violations: bool,
    zero_complexity_violations: bool,
    all_apis_have_icontract: bool,
    coverage_90_plus: bool,
    no_new_suppressions: bool,
) -> int:
    return 5 * sum(
        [
            zero_loc_violations,
            zero_complexity_violations,
            all_apis_have_icontract,
            coverage_90_plus,
            no_new_suppressions,
        ]
    )


def _deduction_for_finding(finding: ReviewFinding) -> int:
    if finding.severity == "error" and not finding.fixable:
        return 15
    if finding.severity == "error" and finding.fixable:
        return 5
    if finding.severity == "warning":
        return 2
    return 1


def _determine_verdict(
    score: int, findings: list[ReviewFinding]
) -> tuple[Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"], Literal[0, 1]]:
    if any(finding.is_blocking() for finding in findings):
        return FAIL, 1
    if score >= 70:
        return PASS, 0
    if score >= 50:
        return PASS_WITH_ADVISORY, 0
    return FAIL, 1


@beartype
@require(lambda findings: isinstance(findings, list), "findings must be a list")
@ensure(lambda result: 0 <= result.score <= 120)
def score_review(
    findings: list[ReviewFinding],
    *,
    zero_loc_violations: bool = False,
    zero_complexity_violations: bool = False,
    all_apis_have_icontract: bool = False,
    coverage_90_plus: bool = False,
    no_new_suppressions: bool = False,
) -> ReviewScore:
    """Compute the governed review score, reward delta, and verdict."""
    score = 100
    score -= sum(_deduction_for_finding(finding) for finding in findings)
    score += _bonus_points(
        zero_loc_violations=zero_loc_violations,
        zero_complexity_violations=zero_complexity_violations,
        all_apis_have_icontract=all_apis_have_icontract,
        coverage_90_plus=coverage_90_plus,
        no_new_suppressions=no_new_suppressions,
    )
    score = max(0, min(120, score))
    overall_verdict, ci_exit_code = _determine_verdict(score=score, findings=findings)
    return ReviewScore(
        score=score,
        reward_delta=score - 80,
        overall_verdict=overall_verdict,
        ci_exit_code=ci_exit_code,
    )
