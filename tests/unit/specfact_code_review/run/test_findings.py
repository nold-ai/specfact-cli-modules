from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict, Unpack, cast

import pytest
from pydantic import ValidationError

from specfact_code_review.run.findings import ReviewFinding, ReviewReport


class ReviewFindingPayload(TypedDict, total=False):
    category: Literal[
        "clean_code",
        "security",
        "type_safety",
        "contracts",
        "testing",
        "style",
        "architecture",
        "tool_error",
    ]
    severity: Literal["error", "warning", "info"]
    tool: str
    rule: str
    file: str
    line: int
    message: str
    fixable: bool


def _finding_data(**overrides: Unpack[ReviewFindingPayload]) -> ReviewFindingPayload:
    data: ReviewFindingPayload = {
        "category": "security",
        "severity": "warning",
        "tool": "ruff",
        "rule": "S101",
        "file": "src/example.py",
        "line": 12,
        "message": "Avoid assert in production code.",
    }
    data.update(overrides)
    return data


def test_review_finding_accepts_valid_values() -> None:
    finding = ReviewFinding(**_finding_data())

    assert finding.category == "security"
    assert finding.severity == "warning"
    assert finding.fixable is False


@pytest.mark.parametrize("severity", ["error", "warning", "info"])
def test_review_finding_accepts_supported_severity_values(
    severity: Literal["error", "warning", "info"],
) -> None:
    finding = ReviewFinding(**_finding_data(severity=severity))

    assert finding.severity == severity


@pytest.mark.parametrize(
    "category",
    ["clean_code", "security", "type_safety", "contracts", "testing", "style", "architecture", "tool_error"],
)
def test_review_finding_accepts_supported_category_values(category: str) -> None:
    typed_category = cast(
        Literal[
            "clean_code",
            "security",
            "type_safety",
            "contracts",
            "testing",
            "style",
            "architecture",
            "tool_error",
        ],
        category,
    )
    finding = ReviewFinding(**_finding_data(category=typed_category))

    assert finding.category == typed_category


def test_review_finding_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(**_finding_data(severity=cast(Any, "critical")))


def test_review_finding_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(**_finding_data(category=cast(Any, "performance")))


@pytest.mark.parametrize("field_name", ["file", "message"])
def test_review_finding_rejects_empty_required_text(field_name: str) -> None:
    overrides: ReviewFindingPayload = {field_name: "   "}  # type: ignore[typeddict-item]
    with pytest.raises(ValidationError):
        ReviewFinding(**_finding_data(**overrides))


def test_review_report_maps_pass_verdict() -> None:
    report = ReviewReport(
        run_id="run-001",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=85,
        findings=[],
        summary="No blocking review issues.",
    )

    assert report.schema_version == "1.0"
    assert report.overall_verdict == "PASS"
    assert report.ci_exit_code == 0
    assert report.reward_delta == 5


def test_review_report_maps_pass_with_advisory_verdict() -> None:
    report = ReviewReport(
        run_id="run-002",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=60,
        findings=[],
        summary="Warnings remain.",
    )

    assert report.overall_verdict == "PASS_WITH_ADVISORY"
    assert report.ci_exit_code == 0


def test_review_report_maps_fail_verdict_from_score() -> None:
    report = ReviewReport(
        run_id="run-003",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=45,
        findings=[],
        summary="Review score below threshold.",
    )

    assert report.overall_verdict == "FAIL"
    assert report.ci_exit_code == 1


def test_review_report_blocking_error_forces_fail() -> None:
    report = ReviewReport(
        run_id="run-004",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=75,
        findings=[ReviewFinding(**_finding_data(severity="error", fixable=False))],
        summary="Contains a blocking error.",
    )

    assert report.overall_verdict == "FAIL"
    assert report.ci_exit_code == 1
