"""TDD coverage for lifecycle-aware Requirements evidence."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from specfact_requirements.requirements.evidence import _write_markdown_summary
from specfact_requirements.requirements.lifecycle import (
    MAX_JUNIT_BYTES,
    build_plan,
    canonical_digest,
    evaluate_mapping,
    reconcile_junit,
)


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


def test_plans_preserve_non_test_case_semantics_but_require_safe_test_selectors() -> None:
    mapping = _planned_mapping()
    cases = mapping["requirements"]["REQ-001"]["verification_cases"]  # type: ignore[index]
    cases.append(  # type: ignore[union-attr]
        {
            "case_id": "REQ-001-A01",
            "method": "analysis",
            "intent": "Review the documented dependency policy.",
            "observable": "A policy decision is recorded.",
        }
    )
    cases[0]["selector"] = {"runner": "pytest", "node_id": "tests/../secrets.py::test_leak"}  # type: ignore[index]

    report = evaluate_mapping(mapping, required_maturity="test-authored")

    assert report["gate_decision"] == "fail"
    assert "invalid-selector:REQ-001-S01" in report["findings"]
    analysis_case = next(case for case in report["plan"]["cases"] if case["method"] == "analysis")
    assert analysis_case["observable"] == "A policy decision is recorded."


def test_mapping_digest_normalizes_yaml_scalars_and_rejects_runner_options() -> None:
    mapping = _planned_mapping()
    mapping["requirements"]["REQ-001"]["rationale"] = date(2026, 8, 2)  # type: ignore[index]

    report = evaluate_mapping(mapping, required_maturity="test-authored")

    assert report["gate_decision"] == "fail"
    assert "missing-rationale:REQ-001" in report["findings"]

    selector_mapping = _planned_mapping()
    case = selector_mapping["requirements"]["REQ-001"]["verification_cases"][0]  # type: ignore[index]
    case["selector"] = {"runner": "pytest", "node_id": "-p.py::test_option"}  # type: ignore[index]
    selector_report = evaluate_mapping(selector_mapping, required_maturity="test-authored")

    assert selector_report["gate_decision"] == "fail"
    assert "invalid-selector:REQ-001-S01" in selector_report["findings"]


def test_canonical_digest_is_injective_for_yaml_values_and_total_plan_ordering() -> None:
    date_digest = canonical_digest({"value": date(2026, 8, 2)})
    sentinel_digest = canonical_digest({"value": {"__unsupported_value__": "date", "value": "2026-08-02"}})
    non_string_key_digest = canonical_digest({1: 2})
    sentinel_key_digest = canonical_digest({"__mapping_entries__": [[1, 2]]})
    cases = [
        {"requirement_id": "REQ-001", "case_id": "S01", "method": "analysis"},
        {"requirement_id": "REQ-001", "case_id": "S01", "method": "demonstration"},
    ]

    assert date_digest != sentinel_digest
    assert non_string_key_digest != sentinel_key_digest
    assert canonical_digest({"values": {2, 1}}) == canonical_digest({"values": {1, 2}})
    source_path = Path(__file__).parents[3] / "packages/specfact-requirements/src"
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            "from specfact_requirements.requirements.lifecycle import canonical_digest; "
            "print(canonical_digest({'values': {1, 2}}))",
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(source_path)},
        text=True,
    )
    assert process.stdout.strip() == canonical_digest({"values": {1, 2}})
    assert build_plan("sha256:" + "a" * 64, cases) == build_plan("sha256:" + "a" * 64, list(reversed(cases)))
    with pytest.raises(ValueError, match="unsupported-sidecar-value:object"):
        canonical_digest({"value": object()})


def test_red_and_verified_require_execution_reconciliation() -> None:
    mapping = _planned_mapping()

    red = evaluate_mapping(mapping, required_maturity="red")
    verified = evaluate_mapping(mapping, required_maturity="verified")

    assert "execution-proof-required:red" in red["findings"]
    assert "execution-proof-required:verified" in verified["findings"]


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
    case["selector"] = {
        "runner": "pytest",
        "node_id": "tests/test_readiness.py::test_unavailable",
    }  # type: ignore[index]
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


def test_reconciliation_finding_retains_the_observed_outcome(tmp_path: Path) -> None:
    mapping = _planned_mapping()
    case = mapping["requirements"]["REQ-001"]["verification_cases"][0]  # type: ignore[index]
    case["selector"] = {
        "runner": "pytest",
        "node_id": "tests/test_readiness.py::test_unavailable",
    }  # type: ignore[index]
    planned = evaluate_mapping(mapping, required_maturity="planned")
    plan = evaluate_mapping(
        mapping,
        required_maturity="test-authored",
        review_evidence={
            "decision": "accepted",
            "reviewer_id": "owner@example.test",
            "reviewer_role": "product-owner",
            "recorded_at": "2026-08-02T00:00:00Z",
            "reference": "review:369",
            "mapping_digest": planned["mapping_digest"],
        },
    )
    junit = tmp_path / "skipped.xml"
    junit.write_text(
        '<testsuite><testcase><properties><property name="specfact.selector" '
        'value="tests/test_readiness.py::test_unavailable"/></properties><skipped/></testcase></testsuite>',
        encoding="utf-8",
    )

    report = reconcile_junit(plan, junit, run_stage="red", source_ref="a" * 40)

    assert "red-proof-skipped-not-failed:tests/test_readiness.py::test_unavailable" in report["findings"]
    assert report["gate_decision"] == "fail"
    assert report["observed_maturity"] == "incomplete"


def test_reconciliation_rejects_incomplete_or_unsafe_plan_and_junit_doctype(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mapping = _planned_mapping()
    incomplete_plan = evaluate_mapping(mapping, required_maturity="planned")
    junit = tmp_path / "result.xml"
    junit.write_text("<testsuite/>", encoding="utf-8")

    with pytest.raises(ValueError, match="test-authored"):
        reconcile_junit(incomplete_plan, junit, run_stage="red", source_ref="a" * 40)
    with pytest.raises(ValueError, match="full lowercase"):
        reconcile_junit(incomplete_plan, junit, run_stage="red", source_ref="a" * 41)

    mapping_case = mapping["requirements"]["REQ-001"]["verification_cases"][0]  # type: ignore[index]
    mapping_case["selector"] = {
        "runner": "pytest",
        "node_id": "tests/test_readiness.py::test_unavailable",
    }  # type: ignore[index]
    planned = evaluate_mapping(mapping, required_maturity="planned")
    accepted_plan = evaluate_mapping(
        mapping,
        required_maturity="test-authored",
        review_evidence={
            "decision": "accepted",
            "reviewer_id": "owner@example.test",
            "reviewer_role": "product-owner",
            "recorded_at": "2026-08-02T00:00:00Z",
            "reference": "review:369",
            "mapping_digest": planned["mapping_digest"],
        },
    )
    junit.write_text("<!DOCTYPE testsuite><testsuite/>", encoding="utf-8")
    rejected = reconcile_junit(accepted_plan, junit, run_stage="red", source_ref="a" * 40)

    assert "junit-unsafe-doctype" in rejected["findings"]
    assert "junit_digest" not in rejected["execution_proof"]
    fifo_path = tmp_path / "junit.fifo"
    os.mkfifo(fifo_path)
    non_regular = reconcile_junit(accepted_plan, fifo_path, run_stage="red", source_ref="a" * 40)
    assert "junit-not-regular-file" in non_regular["findings"]
    malformed_plan = {**accepted_plan, "plan": {**accepted_plan["plan"], "mapping_digest": 123}}
    with pytest.raises(ValueError, match="lifecycle plan"):
        reconcile_junit(malformed_plan, junit, run_stage="red", source_ref="a" * 40)
    monkeypatch.setattr("specfact_requirements.requirements.lifecycle.MAX_JUNIT_BYTES", 1)
    oversized = reconcile_junit(accepted_plan, junit, run_stage="red", source_ref="a" * 40)
    assert "junit-too-large" in oversized["findings"]
    assert MAX_JUNIT_BYTES > 1


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
