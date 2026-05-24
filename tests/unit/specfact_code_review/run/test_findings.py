from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict, Unpack, cast

import pytest
from pydantic import ValidationError

from specfact_code_review.run.findings import EvidenceRef, ReviewFinding, ReviewReport


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
        "naming",
        "kiss",
        "yagni",
        "dry",
        "solid",
        "ai_bloat",
    ]
    severity: Literal["error", "warning", "info"]
    tool: str
    rule: str
    file: str
    line: int
    message: str
    fixable: bool
    confidence: Literal["low", "medium", "high"]
    rewrite_hint: str
    canonical_pattern: str
    intent_key: str
    estimated_deletion_lines: int
    related_locations: list[EvidenceRef]
    guidance_kind: Literal["safe_mechanical", "needs_tests", "design_judgment", "preserve"]
    recommended_action: Literal["remove", "inline", "collapse", "deduplicate", "make_required", "keep", "inspect"]
    clean_code_principle: Literal["kiss", "dry", "yagni", "contracts", "api_stability", "readability"]
    rationale: str
    safety_checks: list[str]
    preserve_reason: str
    action_status: Literal["recommended", "applied", "kept", "skipped", "failed"]
    before_ref: EvidenceRef
    after_ref: EvidenceRef
    improvement: str


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


def test_review_finding_accepts_simplification_metadata() -> None:
    finding = ReviewFinding(
        **_finding_data(
            category="ai_bloat",
            severity="info",
            rule="ai-bloat.manual-accumulator-loop",
            confidence="high",
            rewrite_hint="Replace the append loop with a list comprehension.",
            canonical_pattern="manual-accumulator-loop",
            intent_key="customer-normalization",
            estimated_deletion_lines=3,
            related_locations=[EvidenceRef(path="src/customer.py", start_line=42, end_line=45)],
        )
    )

    assert finding.confidence == "high"
    assert finding.rewrite_hint == "Replace the append loop with a list comprehension."
    assert finding.canonical_pattern == "manual-accumulator-loop"
    assert finding.intent_key == "customer-normalization"
    assert finding.estimated_deletion_lines == 3
    assert finding.related_locations is not None
    assert finding.related_locations[0].path == "src/customer.py"
    assert finding.model_dump()["related_locations"][0]["start_line"] == 42


def test_review_finding_marks_deterministic_simplification_metadata() -> None:
    finding = ReviewFinding(
        **_finding_data(
            category="dry",
            severity="warning",
            rule="dry.duplicate-intent",
            confidence="high",
            rewrite_hint="Extract the duplicated request parsing.",
            canonical_pattern="duplicate-request-parsing",
            intent_key="request-parsing",
        )
    )

    assert finding.has_simplification_metadata()
    assert finding.simplification_metadata_is_deterministic()


def test_review_finding_accepts_guided_simplification_metadata() -> None:
    finding = ReviewFinding(
        **_finding_data(
            category="ai_bloat",
            severity="info",
            rule="ai-bloat.redundant-intermediate",
            confidence="high",
            rewrite_hint="Inline the one-use temporary into the return statement.",
            canonical_pattern="one-use-temporary",
            estimated_deletion_lines=1,
            guidance_kind="safe_mechanical",
            recommended_action="inline",
            clean_code_principle="kiss",
            rationale="The local variable is assigned once and read only by the following return.",
            safety_checks=["same expression is returned", "temporary has no later reads"],
            action_status="recommended",
        )
    )

    assert finding.has_guided_simplification_metadata()
    assert finding.is_safe_mechanical_simplification()


def test_review_finding_accepts_guided_metadata_without_action_status() -> None:
    finding = ReviewFinding(
        **_finding_data(
            category="ai_bloat",
            severity="info",
            rule="ai-bloat.redundant-intermediate",
            confidence="high",
            rewrite_hint="Inline the one-use temporary into the return statement.",
            canonical_pattern="one-use-temporary",
            estimated_deletion_lines=1,
            guidance_kind="safe_mechanical",
            recommended_action="inline",
            clean_code_principle="kiss",
            rationale="The local variable is assigned once and read only by the following return.",
            safety_checks=["same expression is returned", "temporary has no later reads"],
        )
    )

    assert finding.action_status is None
    assert finding.is_safe_mechanical_simplification()


def test_review_finding_rejects_preserve_guidance_without_preserve_reason() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(
            **_finding_data(
                category="ai_bloat",
                severity="info",
                guidance_kind="preserve",
                recommended_action="keep",
                clean_code_principle="api_stability",
                rationale="The optional argument is part of a public extension contract.",
                safety_checks=["public compatibility boundary checked"],
                action_status="recommended",
            )
        )


def test_review_finding_rejects_guided_fields_without_guidance_kind() -> None:
    with pytest.raises(ValidationError, match="guidance_kind is required"):
        ReviewFinding(
            **_finding_data(
                category="ai_bloat",
                severity="info",
                recommended_action="remove",
            )
        )


@pytest.mark.parametrize(
    "field_payload",
    [
        cast(ReviewFindingPayload, {"before_ref": EvidenceRef(path="src/example.py", start_line=10, end_line=12)}),
        cast(ReviewFindingPayload, {"after_ref": EvidenceRef(path="src/example.py", start_line=10, end_line=10)}),
        cast(ReviewFindingPayload, {"improvement": "Removed one redundant branch."}),
    ],
)
def test_review_finding_rejects_guided_evidence_fields_without_guidance_kind(
    field_payload: ReviewFindingPayload,
) -> None:
    finding_payload = _finding_data(category="ai_bloat", severity="info")
    finding_payload.update(field_payload)

    with pytest.raises(ValidationError, match="guidance_kind is required"):
        ReviewFinding(**finding_payload)


def test_review_finding_rejects_partial_simplification_metadata_as_nondeterministic() -> None:
    finding = ReviewFinding(
        **_finding_data(
            category="dry",
            severity="warning",
            rule="dry.duplicate-intent",
            confidence="high",
        )
    )

    assert finding.has_simplification_metadata()
    assert not finding.simplification_metadata_is_deterministic()


@pytest.mark.parametrize("severity", ["error", "warning", "info"])
def test_review_finding_accepts_supported_severity_values(
    severity: Literal["error", "warning", "info"],
) -> None:
    finding = ReviewFinding(**_finding_data(severity=severity))

    assert finding.severity == severity


@pytest.mark.parametrize(
    "category",
    [
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
    ],
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
            "naming",
            "kiss",
            "yagni",
            "dry",
            "solid",
            "ai_bloat",
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


def test_review_report_uses_schema_1_1_when_simplification_metadata_is_present() -> None:
    report = ReviewReport(
        run_id="run-simplify",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=85,
        findings=[
            ReviewFinding(
                **_finding_data(
                    category="ai_bloat",
                    severity="info",
                    confidence="high",
                    rewrite_hint="Inline the one-use temporary.",
                    canonical_pattern="one-use-temporary",
                    estimated_deletion_lines=1,
                )
            )
        ],
        summary="Simplification advisories.",
    )

    assert report.schema_version == "1.1"
    assert report.overall_verdict == "PASS"
    assert report.ci_exit_code == 0


def test_review_report_uses_schema_1_2_and_summary_when_guided_metadata_is_present() -> None:
    report = ReviewReport(
        run_id="run-guided-simplify",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=85,
        findings=[
            ReviewFinding(
                **_finding_data(
                    category="ai_bloat",
                    severity="info",
                    confidence="high",
                    rewrite_hint="Inline the one-use temporary into the return statement.",
                    canonical_pattern="one-use-temporary",
                    estimated_deletion_lines=1,
                    guidance_kind="safe_mechanical",
                    recommended_action="inline",
                    clean_code_principle="kiss",
                    rationale="The local variable is assigned once and read only by the following return.",
                    safety_checks=["same expression is returned", "temporary has no later reads"],
                    action_status="recommended",
                )
            )
        ],
        summary="Guided simplification advisories.",
    )

    assert report.schema_version == "1.2"
    assert report.simplification_summary is not None
    assert report.simplification_summary.by_guidance_kind == {"safe_mechanical": 1}
    assert report.simplification_summary.by_action_status == {"recommended": 1}
    assert report.simplification_summary.blocking_simplification_count == 1


def test_review_report_counts_failed_safe_mechanical_findings_as_blocking() -> None:
    report = ReviewReport(
        run_id="run-guided-simplify",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=85,
        findings=[
            ReviewFinding(
                **_finding_data(
                    category="ai_bloat",
                    severity="info",
                    confidence="high",
                    rewrite_hint="Remove the duplicate terminal branch.",
                    canonical_pattern="duplicate-terminal-guard",
                    estimated_deletion_lines=1,
                    guidance_kind="safe_mechanical",
                    recommended_action="remove",
                    clean_code_principle="kiss",
                    rationale="The branch repeats an earlier terminal guard.",
                    safety_checks=["same guard expression already returned earlier"],
                    action_status="failed",
                )
            )
        ],
        summary="Guided simplification advisories.",
    )

    assert report.simplification_summary is not None
    assert report.simplification_summary.blocking_simplification_count == 1


def test_review_report_counts_missing_status_safe_mechanical_findings_as_blocking() -> None:
    report = ReviewReport(
        run_id="run-guided-simplify",
        timestamp=datetime(2026, 3, 11, tzinfo=UTC),
        score=85,
        findings=[
            ReviewFinding(
                **_finding_data(
                    category="ai_bloat",
                    severity="info",
                    confidence="high",
                    rewrite_hint="Remove the duplicate terminal branch.",
                    canonical_pattern="duplicate-terminal-guard",
                    estimated_deletion_lines=1,
                    guidance_kind="safe_mechanical",
                    recommended_action="remove",
                    clean_code_principle="kiss",
                    rationale="The branch repeats an earlier terminal guard.",
                    safety_checks=["same guard expression already returned earlier"],
                )
            )
        ],
        summary="Guided simplification advisories.",
    )

    assert report.simplification_summary is not None
    assert report.simplification_summary.blocking_simplification_count == 1


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
