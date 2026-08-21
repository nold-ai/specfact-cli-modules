from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict, Unpack, cast

import pytest
from pydantic import ValidationError

from specfact_code_review.run.findings import (
    AiBloatIndex,
    CleanupForecast,
    DeletionEstimate,
    EvidenceRef,
    GuidanceKindForecast,
    PreserveReasonEvidence,
    RemediationPacket,
    RequirementsEvidenceContext,
    ReviewedLoc,
    ReviewFinding,
    ReviewReport,
    SignalTraceEntry,
)


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
    signal_trace: list[SignalTraceEntry]
    preserve_reasons: list[PreserveReasonEvidence]
    remediation_packet: RemediationPacket


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


def _agent_payload_finding() -> ReviewFinding:
    return ReviewFinding(
        **_finding_data(
            category="ai_bloat",
            severity="info",
            tool="ast",
            rule="ai-bloat.redundant-intermediate",
            file="src/example.py",
            line=1,
            message="Simplify local code.",
            fixable=True,
            signal_trace=[
                SignalTraceEntry(
                    tool="ast",
                    source="ai-bloat.redundant-intermediate",
                    fired=True,
                    explanation="AST pattern matched a redundant intermediate assignment.",
                )
            ],
            preserve_reasons=[
                PreserveReasonEvidence(
                    reason="public_api",
                    evidence_refs=[EvidenceRef(path="src/example.py", start_line=1)],
                    explanation="Public API boundary.",
                )
            ],
            remediation_packet=RemediationPacket(
                issue="Simplify local code.",
                recommended_action="inspect",
                possible_keep_reason="Public API boundary.",
                safety_checks=["verify public behavior"],
                validation_plan=["run targeted tests"],
                safe_to_autofix=False,
            ),
        )
    )


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


def test_review_finding_accepts_cleanup_handoff_metadata() -> None:
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
            signal_trace=[
                SignalTraceEntry(
                    tool="ast",
                    source="ai-bloat.redundant-intermediate",
                    fired=True,
                    score=1.0,
                    value="one-use-temporary",
                    evidence_refs=[EvidenceRef(path="src/example.py", start_line=12)],
                    explanation="AST pattern matched a one-use temporary.",
                )
            ],
            preserve_reasons=[
                PreserveReasonEvidence(
                    reason="public_api",
                    evidence_refs=[EvidenceRef(path="src/example.py", start_line=12)],
                    explanation="Exported in __all__.",
                )
            ],
            remediation_packet=RemediationPacket(
                issue="One-use temporary can be inlined.",
                recommended_action="inline",
                possible_keep_reason="Keep only if readability would regress.",
                safety_checks=["same expression is returned"],
                validation_plan=["run targeted tests", "rerun simplify review"],
                safe_to_autofix=False,
                patch_forecast_refs=["preview:src/example.py:12"],
            ),
        )
    )

    assert finding.signal_trace is not None
    assert finding.signal_trace[0].tool == "ast"
    assert finding.preserve_reasons is not None
    assert finding.preserve_reasons[0].reason == "public_api"
    assert finding.remediation_packet is not None
    assert not finding.remediation_packet.safe_to_autofix
    assert not finding.is_safe_mechanical_simplification()


def test_review_finding_rejects_unknown_preserve_reason() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(
            **_finding_data(
                category="ai_bloat",
                severity="info",
                guidance_kind="safe_mechanical",
                recommended_action="inline",
                clean_code_principle="kiss",
                rationale="The local rewrite is safe.",
                safety_checks=["same expression is returned"],
                preserve_reasons=cast(
                    Any,
                    [
                        {
                            "reason": "unknown_reason",
                            "evidence_refs": [EvidenceRef(path="src/example.py", start_line=12)],
                            "explanation": "Not in taxonomy.",
                        }
                    ],
                ),
            )
        )


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


def test_review_report_uses_schema_1_5_for_requirements_evidence() -> None:
    report = ReviewReport(
        run_id="run-requirements-context",
        timestamp=datetime(2026, 8, 4, tzinfo=UTC),
        score=85,
        findings=[],
        summary="Finalized Requirements provenance.",
        requirements_evidence=RequirementsEvidenceContext(
            path="artifacts/requirements-evidence.json",
            content_digest="sha256:" + "a" * 64,
            mapping_digest="sha256:" + "b" * 64,
            plan_digest="sha256:" + "c" * 64,
            source_ref="d" * 40,
            gate_decision="pass",
        ),
    )

    assert report.schema_version == "1.5"
    assert report.requirements_evidence is not None


@pytest.mark.parametrize(
    ("legacy_payload", "expected_schema_version"),
    [
        (
            {
                "schema_version": "1.2",
                "run_id": "legacy-guided",
                "timestamp": "2026-03-11T00:00:00Z",
                "score": 85,
                "findings": [],
                "summary": "Legacy guided report.",
            },
            "1.2",
        ),
        (
            {
                "schema_version": "1.4",
                "run_id": "legacy-enforcement",
                "timestamp": "2026-03-11T00:00:00Z",
                "score": 85,
                "findings": [],
                "summary": "Legacy enforcement report.",
                "enforcement_mode": "changed",
            },
            "1.4",
        ),
    ],
)
def test_review_report_accepts_legacy_schema_fixtures_without_requirements_provenance(
    legacy_payload: dict[str, Any], expected_schema_version: str
) -> None:
    report = ReviewReport.model_validate(legacy_payload)

    assert report.schema_version == expected_schema_version
    assert report.requirements_evidence is None


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


def test_review_report_uses_schema_1_3_when_cleanup_forecast_is_present() -> None:
    report = ReviewReport(
        run_id="run-cleanup-forecast",
        timestamp=datetime(2026, 5, 24, tzinfo=UTC),
        score=85,
        findings=[],
        summary="Cleanup forecast.",
        cleanup_forecast=CleanupForecast(
            reviewed_loc=ReviewedLoc(production=80, tests=20, total=100),
            estimated_deletion_lines=DeletionEstimate(low=2, expected=5, high=8),
            ai_bloat_index=AiBloatIndex(
                findings_per_kloc=20.0,
                weighted_bloat_points_per_kloc=16.0,
                cleanup_yield_loc_per_kloc=50.0,
            ),
            by_guidance_kind={
                "safe_mechanical": GuidanceKindForecast(count=2, estimated_deletion_lines=2),
                "needs_tests": GuidanceKindForecast(count=1, estimated_deletion_lines=5),
            },
            by_action_status={"recommended": 3},
        ),
    )

    assert report.schema_version == "1.3"
    assert report.cleanup_forecast is not None
    assert report.cleanup_forecast.ai_bloat_index.weighted_bloat_points_per_kloc == 16.0


def test_review_report_uses_schema_1_3_when_finding_agent_payload_is_present() -> None:
    report = ReviewReport(
        run_id="run-cleanup-handoff",
        timestamp=datetime(2026, 5, 24, tzinfo=UTC),
        score=85,
        findings=[_agent_payload_finding()],
        summary="Cleanup agent payload.",
    )

    assert report.schema_version == "1.3"
    assert report.findings[0].signal_trace is not None
    assert report.findings[0].preserve_reasons is not None
    assert report.findings[0].remediation_packet is not None


def test_reviewed_loc_rejects_total_mismatch() -> None:
    with pytest.raises(ValidationError, match=r"reviewed_loc.total must equal production \+ tests"):
        ReviewedLoc(production=80, tests=20, total=90)


def test_deletion_estimate_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError, match="estimated_deletion_lines must satisfy low <= expected <= high"):
        DeletionEstimate(low=6, expected=5, high=10)

    with pytest.raises(ValidationError, match="estimated_deletion_lines must satisfy low <= expected <= high"):
        DeletionEstimate(low=1, expected=5, high=4)


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


def test_fixable_error_remains_blocking_until_applied() -> None:
    finding = ReviewFinding(**_finding_data(severity="error", fixable=True))

    assert finding.is_blocking() is True


def test_report_never_says_all_passed_with_mandatory_unknown() -> None:
    from specfact_code_review.run import findings

    report = findings.build_assurance_report(
        status="UNKNOWN",
        enforcement="full",
        member_evidence=({"id": "contracts", "outcome": "UNKNOWN", "diagnostic": "timeout"},),
        valid_blockers=(),
    )

    assert report.assurance_status == "UNKNOWN"
    assert "all passed" not in report.summary.lower()
    assert report.has_unknown_required_evidence is True


@pytest.mark.parametrize(
    ("status", "enforcement", "legacy_verdict", "exit_code"),
    [
        ("PASS", "full", "PASS", 0),
        ("FAIL", "full", "FAIL", 1),
        ("UNKNOWN", "full", "FAIL", 1),
        ("NOT_APPLICABLE", "full", "PASS_WITH_ADVISORY", 0),
        ("PASS", "shadow", "PASS", 0),
        ("FAIL", "shadow", "FAIL", 0),
        ("UNKNOWN", "shadow", "FAIL", 0),
        ("NOT_APPLICABLE", "shadow", "PASS_WITH_ADVISORY", 0),
    ],
)
def test_schema_1_6_assurance_status_legacy_projection_and_exit_matrix(
    status: str, enforcement: str, legacy_verdict: str, exit_code: int
) -> None:
    from specfact_code_review.run import findings

    projection = findings.project_assurance_status(status=status, enforcement=enforcement)

    assert projection.overall_verdict == legacy_verdict
    assert projection.ci_exit_code == exit_code
    assert projection.enforcement_mode == enforcement


def test_assurance_status_fail_precedes_unknown_with_known_blocker() -> None:
    from specfact_code_review.run import findings

    report = findings.build_assurance_report(
        status=None,
        enforcement="full",
        member_evidence=({"id": "contracts", "outcome": "UNKNOWN", "diagnostic": "timeout"},),
        valid_blockers=({"rule": "introduced-blocker", "status": "open"},),
    )

    assert report.assurance_status == "FAIL"
    assert report.has_unknown_required_evidence is True
    assert report.ci_exit_code == 1


def test_fixed_baseline_failure_is_excluded_from_aggregate_blockers() -> None:
    from specfact_code_review.run import findings

    report = findings.build_assurance_report(
        status=None,
        enforcement="full",
        member_evidence=({"id": "ruff", "base": "FAIL", "head": "PASS", "disposition": "fixed"},),
        valid_blockers=(),
    )

    assert report.assurance_status == "PASS"
    assert report.aggregate_blockers == ()
    assert report.member_evidence[0].disposition == "fixed"


@pytest.mark.parametrize("schema_version", ["1.6", "1.10", "2.0"])
def test_schema_1_6_or_newer_missing_assurance_status_is_unknown(schema_version: str) -> None:
    from specfact_code_review.run import findings

    payload = {
        "schema_version": schema_version,
        "overall_verdict": "PASS",
        "ci_exit_code": 0,
        "run_id": "missing-status",
        "score": 100,
        "findings": [],
        "summary": "legacy says pass",
    }

    result = findings.read_review_report(payload)

    assert result.status == "UNKNOWN"
    assert result.ci_exit_code == 1


def test_schema_1_6_consumer_compatibility_matrix_is_closed() -> None:
    from specfact_code_review.run import findings

    resource = (
        Path(__file__).resolve().parents[4]
        / "packages/specfact-code-review/src/specfact_code_review/resources/contracts/review-report-schema-1.6-consumer-matrix.json"
    )
    matrix = json.loads(resource.read_text(encoding="utf-8"))

    result = findings.validate_consumer_matrix(matrix)

    assert result.status == "PASS"
    assert {case["assurance_status"] for case in matrix["canonical_status_reports"]} == {
        "PASS",
        "FAIL",
        "UNKNOWN",
        "NOT_APPLICABLE",
    }
    assert matrix["legacy_schema_less_ledger_fixture"]["normalized"]["reward_delta"] == 5
    assert {case["disposition"] for case in matrix["finding_multiset_cases"]} == {
        "fixed",
        "introduced",
        "unchanged",
        "unknown",
    }
    assert {case["expected_status"] for case in matrix["project_runtime_cases"]} == {"PASS", "UNKNOWN"}
    assert {case["dimension"] for case in matrix["pr_range_boundary_cases"]} == {
        "accepted",
        "analyzer_profile",
        "merge_base",
        "producer_identity",
        "project_runtime",
        "schema",
        "suppression_catalog",
    }


def test_consumer_matrix_missing_packaged_catalog_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    from specfact_code_review.run import findings

    monkeypatch.setattr(findings, "_packaged_suppression_catalog_digest", lambda: None)

    result = findings.validate_consumer_matrix({})

    assert result.status == "UNKNOWN"
    assert result.reason == "suppression_catalog_resource_unavailable"


def test_report_binds_suppression_catalog_identity() -> None:
    from specfact_code_review.run import findings

    report = findings.build_assurance_report(
        status="PASS",
        enforcement="full",
        member_evidence=(),
        valid_blockers=(),
        suppression_catalog_digest="sha256:" + "a" * 64,
    )

    assert report.suppression_catalog_digest == "sha256:" + "a" * 64
