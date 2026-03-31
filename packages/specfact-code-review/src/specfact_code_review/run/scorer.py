"""Scoring helpers for structured review runs."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ReviewScoreModifiers:
    """Optional bonuses that influence the computed score."""

    zero_loc_violations: bool = False
    zero_complexity_violations: bool = False
    all_apis_have_icontract: bool = False
    coverage_90_plus: bool = False
    no_new_suppressions: bool = False


def _bonus_points(modifiers: ReviewScoreModifiers) -> int:
    return 5 * sum(
        [
            modifiers.zero_loc_violations,
            modifiers.zero_complexity_violations,
            modifiers.all_apis_have_icontract,
            modifiers.coverage_90_plus,
            modifiers.no_new_suppressions,
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
    **kwargs: object,
) -> ReviewScore:
    """Compute the governed review score, reward delta, and verdict."""
    modifiers = ReviewScoreModifiers(
        zero_loc_violations=bool(kwargs.pop("zero_loc_violations", False)),
        zero_complexity_violations=bool(kwargs.pop("zero_complexity_violations", False)),
        all_apis_have_icontract=bool(kwargs.pop("all_apis_have_icontract", False)),
        coverage_90_plus=bool(kwargs.pop("coverage_90_plus", False)),
        no_new_suppressions=bool(kwargs.pop("no_new_suppressions", False)),
    )
    if kwargs:
        unexpected = ", ".join(sorted(kwargs))
        raise ValueError(f"Unexpected keyword arguments: {unexpected}")

    score = 100
    score -= sum(_deduction_for_finding(finding) for finding in findings)
    score += _bonus_points(modifiers)
    score = max(0, min(120, score))
    overall_verdict, ci_exit_code = _determine_verdict(score=score, findings=findings)
    return ReviewScore(
        score=score,
        reward_delta=score - 80,
        overall_verdict=overall_verdict,
        ci_exit_code=ci_exit_code,
    )
