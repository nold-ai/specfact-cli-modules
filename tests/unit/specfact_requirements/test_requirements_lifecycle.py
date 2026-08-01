"""TDD coverage for lifecycle-aware Requirements evidence."""

from __future__ import annotations

from pathlib import Path

from specfact_requirements.requirements.evidence import _write_markdown_summary
from specfact_requirements.requirements.lifecycle import evaluate_mapping, reconcile_junit


def _planned_mapping() -> dict[str, object]:
    return {
        "schema_version": "2",
        "requirements": {
            "REQ-001": {
                "rationale": "Operators need a reliable readiness decision.",
                "stakeholder_refs": ["issue:123"],
                "touchpoints": [{"id": "readiness-command", "kind": "cli_command", "locator": "specfact readiness"}],
                "verification_cases": [
                    {
                        "case_id": "REQ-001-S01",
                        "scenario_id": "REQ-001-S01",
                        "method": "test",
                        "intent": "Report unavailable dependencies.",
                        "observable": "Structured readiness result and exit code.",
                    }
                ],
            }
        },
    }


def test_complete_proposal_mapping_passes_without_claiming_execution() -> None:
    report = evaluate_mapping(_planned_mapping(), required_maturity="planned")

    assert report["gate_decision"] == "pass"
    assert report["required_maturity"] == "planned"
    assert report["observed_maturity"] == "planned"
    assert report["delivery_status"] == "proposal-only"
    assert report["implementation_evidence"] == "not-yet-available"
    assert report["verdict"] == "passed"
    assert report["mapping_digest"].startswith("sha256:")


def test_incomplete_proposal_mapping_fails_without_synthetic_test_link() -> None:
    mapping = _planned_mapping()
    case = mapping["requirements"]["REQ-001"]["verification_cases"][0]  # type: ignore[index]
    del case["observable"]  # type: ignore[index]

    report = evaluate_mapping(mapping, required_maturity="planned")

    assert report["gate_decision"] == "fail"
    assert report["observed_maturity"] == "incomplete"
    assert "missing-observable:REQ-001-S01" in report["findings"]


def test_accepted_maturity_requires_matching_provider_neutral_review() -> None:
    mapping = _planned_mapping()
    planned = evaluate_mapping(mapping, required_maturity="planned")
    missing = evaluate_mapping(mapping, required_maturity="accepted")
    accepted = evaluate_mapping(
        mapping,
        required_maturity="accepted",
        review_evidence={
            "decision": "accepted",
            "reviewer_id": "product-owner@example.test",
            "reviewer_role": "product-owner",
            "recorded_at": "2026-08-01T12:00:00Z",
            "reference": "review:123",
            "mapping_digest": planned["mapping_digest"],
        },
    )

    assert missing["gate_decision"] == "fail"
    assert "acceptance-missing" in missing["findings"]
    assert accepted["gate_decision"] == "pass"
    assert accepted["observed_maturity"] == "accepted"


def test_red_requires_collected_failure_and_final_requires_prior_red(tmp_path: Path) -> None:
    mapping = _planned_mapping()
    case = mapping["requirements"]["REQ-001"]["verification_cases"][0]  # type: ignore[index]
    case["selector"] = {"runner": "pytest", "node_id": "tests/test_readiness.py::test_unavailable"}  # type: ignore[index]
    plan = evaluate_mapping(
        mapping,
        required_maturity="test-authored",
        review_evidence={
            "decision": "accepted",
            "reviewer_id": "product-owner@example.test",
            "reviewer_role": "product-owner",
            "recorded_at": "2026-08-01T12:00:00Z",
            "reference": "review:123",
            "mapping_digest": evaluate_mapping(mapping, required_maturity="planned")["mapping_digest"],
        },
    )
    red_junit = tmp_path / "red.xml"
    red_junit.write_text(
        '<testsuite><testcase><properties><property name="specfact.selector" '
        'value="tests/test_readiness.py::test_unavailable"/></properties><failure/></testcase></testsuite>',
        encoding="utf-8",
    )
    final_junit = tmp_path / "final.xml"
    final_junit.write_text(
        '<testsuite><testcase><properties><property name="specfact.selector" '
        'value="tests/test_readiness.py::test_unavailable"/></properties></testcase></testsuite>',
        encoding="utf-8",
    )

    red = reconcile_junit(plan, red_junit, run_stage="red", source_ref="a" * 40)
    final_without_red = reconcile_junit(plan, final_junit, run_stage="final", source_ref="b" * 40)
    final = reconcile_junit(plan, final_junit, run_stage="final", source_ref="b" * 40, prior_red_proof=red)

    assert red["gate_decision"] == "pass"
    assert red["observed_maturity"] == "red"
    assert final_without_red["gate_decision"] == "fail"
    assert "prior-red-proof-missing" in final_without_red["findings"]
    assert final["gate_decision"] == "pass"
    assert final["observed_maturity"] == "verified"


def test_lifecycle_evidence_summary_uses_findings_without_execution_claim(tmp_path: Path) -> None:
    lifecycle = evaluate_mapping(_planned_mapping(), required_maturity="planned")
    report = {
        **lifecycle,
        "sources": [{"source": "openspec/changes/widget", **lifecycle}],
        "summary": {"failed_sources": 0, "passed_sources": 1, "skipped_sources": 0, "total_sources": 1},
    }
    summary = tmp_path / "requirements-evidence.md"

    _write_markdown_summary(report, summary)

    contents = summary.read_text(encoding="utf-8")
    assert "Gate decision: **pass**" in contents
    assert "not-yet-available" in contents
