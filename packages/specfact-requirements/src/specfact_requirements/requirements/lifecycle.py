"""Deterministic lifecycle evidence for mapped Requirements scenarios.

This module deliberately validates and reconciles evidence only. Test execution,
review-provider integration, and Git ancestry checks remain core-owned.
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure


_MATURITY_ORDER = {
    "incomplete": 0,
    "planned": 1,
    "accepted": 2,
    "test-authored": 3,
    "red": 4,
    "verified": 5,
}
_SUPPORTED_METHODS = {"test", "analysis", "inspection", "demonstration"}
_SUPPORTED_REQUIRED_MATURITY = {"planned", "accepted", "test-authored", "red", "verified"}
_SOURCE_REF_PATTERN = re.compile(r"[0-9a-f]{40,64}")
_PYTEST_SELECTOR_PATTERN = re.compile(r"(?!-)[^\s:\x00-\x1f]+\.py::[^\s\x00-\x1f]+")


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _mapping_payload(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Return the semantically relevant source mapping for digest calculation."""
    return {
        "schema_version": mapping.get("schema_version"),
        "requirements": mapping.get("requirements"),
    }


def _append_missing(findings: list[str], value: object, field: str, identifier: str) -> None:
    if not _is_text(value):
        findings.append(f"missing-{field}:{identifier}")


def _validate_selector(case: Mapping[str, Any], case_id: str, findings: list[str]) -> dict[str, str] | None:
    selector = case.get("selector")
    if not isinstance(selector, Mapping):
        findings.append(f"missing-selector:{case_id}")
        return None
    runner = selector.get("runner")
    node_id = selector.get("node_id")
    if runner != "pytest":
        findings.append(f"unsupported-selector-runner:{case_id}")
        return None
    if not isinstance(node_id, str) or _PYTEST_SELECTOR_PATTERN.fullmatch(node_id) is None:
        findings.append(f"invalid-selector:{case_id}")
        return None
    return {"runner": runner, "node_id": node_id}


def _selector_required(method: object, required_maturity: str, case: Mapping[str, Any]) -> bool:
    return (method == "test" and _MATURITY_ORDER[required_maturity] >= _MATURITY_ORDER["test-authored"]) or isinstance(
        case.get("selector"), Mapping
    )


def _validated_case(
    case: object, requirement_id: str, required_maturity: str
) -> tuple[dict[str, str] | None, list[str]]:
    if not isinstance(case, Mapping):
        return None, [f"invalid-verification-case:{requirement_id}"]
    case_id = case.get("case_id")
    if not _is_text(case_id):
        return None, [f"missing-case-id:{requirement_id}"]
    case_name = str(case_id)
    findings: list[str] = []
    for field in ("method", "intent", "observable"):
        _append_missing(findings, case.get(field), field, case_name)
    method = case.get("method")
    if method not in _SUPPORTED_METHODS:
        return None, [*findings, f"unsupported-verification-method:{case_name}"]
    selector = (
        _validate_selector(case, case_name, findings) if _selector_required(method, required_maturity, case) else None
    )
    if method != "test" or selector is None:
        return None, findings
    return {"requirement_id": requirement_id, "case_id": case_name, **selector}, findings


def _touchpoint_findings(requirement: Mapping[str, Any], identifier: str) -> list[str]:
    touchpoints = requirement.get("touchpoints")
    if not isinstance(touchpoints, list) or not touchpoints:
        return [f"missing-touchpoints:{identifier}"]
    invalid = any(
        not isinstance(touchpoint, Mapping)
        or not all(_is_text(touchpoint.get(field)) for field in ("id", "kind", "locator"))
        for touchpoint in touchpoints
    )
    return [f"invalid-touchpoint:{identifier}"] if invalid else []


def _verification_case_results(
    requirement: Mapping[str, Any], identifier: str, required_maturity: str
) -> tuple[list[dict[str, str]], list[str]]:
    verification_cases = requirement.get("verification_cases")
    if not isinstance(verification_cases, list) or not verification_cases:
        return [], [f"missing-verification-cases:{identifier}"]
    cases: list[dict[str, str]] = []
    findings: list[str] = []
    for case in verification_cases:
        validated, case_findings = _validated_case(case, identifier, required_maturity)
        findings.extend(case_findings)
        if validated is not None:
            cases.append(validated)
    return cases, findings


def _requirement_cases(
    requirement_id: object, requirement: object, required_maturity: str
) -> tuple[list[dict[str, str]], list[str]]:
    if not _is_text(requirement_id) or not isinstance(requirement, Mapping):
        return [], ["invalid-requirement-entry"]
    identifier = str(requirement_id)
    findings: list[str] = []
    _append_missing(findings, requirement.get("rationale"), "rationale", identifier)
    findings.extend(_touchpoint_findings(requirement, identifier))
    cases, case_findings = _verification_case_results(requirement, identifier, required_maturity)
    return cases, [*findings, *case_findings]


def _duplicate_selector_findings(cases: list[dict[str, str]]) -> list[str]:
    selectors = [case["node_id"] for case in cases]
    duplicates = {selector for selector in selectors if selectors.count(selector) > 1}
    return [f"duplicate-selector:{selector}" for selector in sorted(duplicates)]


def _validated_cases(mapping: Mapping[str, Any], required_maturity: str) -> tuple[list[dict[str, str]], list[str]]:
    if mapping.get("schema_version") != "2":
        return [], ["unsupported-sidecar-schema"]
    requirements = mapping.get("requirements")
    if not isinstance(requirements, Mapping) or not requirements:
        return [], ["missing-requirements"]
    cases: list[dict[str, str]] = []
    findings: list[str] = []
    for requirement_id, requirement in sorted(requirements.items(), key=lambda item: str(item[0])):
        requirement_cases, requirement_findings = _requirement_cases(requirement_id, requirement, required_maturity)
        cases.extend(requirement_cases)
        findings.extend(requirement_findings)
    return cases, sorted({*findings, *_duplicate_selector_findings(cases)})


def _valid_acceptance(review_evidence: Mapping[str, Any] | None, mapping_digest: str) -> list[str]:
    if review_evidence is None:
        return ["acceptance-missing"]
    findings = [
        f"acceptance-missing-{field}"
        for field in ("reviewer_id", "reviewer_role", "recorded_at", "reference")
        if not _is_text(review_evidence.get(field))
    ]
    if review_evidence.get("decision") != "accepted":
        findings.append("acceptance-not-accepted")
    if review_evidence.get("mapping_digest") != mapping_digest:
        findings.append("acceptance-stale")
    return findings


def _lifecycle_report(
    *,
    required_maturity: str,
    observed_maturity: str,
    mapping_digest: str,
    findings: list[str],
    cases: list[dict[str, str]],
) -> dict[str, Any]:
    passed = not findings and _MATURITY_ORDER[observed_maturity] >= _MATURITY_ORDER[required_maturity]
    delivery_status = {
        "planned": "proposal-only",
        "accepted": "proposal-accepted",
        "test-authored": "test-design",
        "red": "failing-first-proven",
        "verified": "implementation-verified",
        "incomplete": "incomplete",
    }[observed_maturity]
    implementation_evidence = {
        "planned": "not-yet-available",
        "accepted": "not-yet-available",
        "test-authored": "tests-not-executed",
        "red": "failing-first-proven",
        "verified": "passing-after-red-proven",
        "incomplete": "not-available",
    }[observed_maturity]
    return {
        "schema_version": "2",
        "verdict": "passed" if passed else "failed",
        "gate_decision": "pass" if passed else "fail",
        "required_maturity": required_maturity,
        "observed_maturity": observed_maturity,
        "delivery_status": delivery_status,
        "implementation_evidence": implementation_evidence,
        "mapping_digest": mapping_digest,
        "findings": sorted(set(findings)),
        "plan": {"mapping_digest": mapping_digest, "cases": cases},
    }


@beartype
@ensure(lambda result: isinstance(result, dict))
def evaluate_mapping(
    mapping: Mapping[str, Any],
    *,
    required_maturity: str,
    review_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a schema-v2 mapping without executing tests."""
    if required_maturity not in _SUPPORTED_REQUIRED_MATURITY:
        raise ValueError("required maturity must be planned, accepted, test-authored, red, or verified")
    mapping_digest = _canonical_digest(_mapping_payload(mapping))
    cases, findings = _validated_cases(mapping, required_maturity)
    observed = "incomplete" if findings else "planned"
    if not findings and _MATURITY_ORDER[required_maturity] >= _MATURITY_ORDER["accepted"]:
        acceptance_findings = _valid_acceptance(review_evidence, mapping_digest)
        findings.extend(acceptance_findings)
        if not acceptance_findings:
            observed = "accepted"
    if not findings and _MATURITY_ORDER[required_maturity] >= _MATURITY_ORDER["test-authored"]:
        observed = "test-authored"
    return _lifecycle_report(
        required_maturity=required_maturity,
        observed_maturity=observed,
        mapping_digest=mapping_digest,
        findings=findings,
        cases=cases,
    )


def _junit_case_result(test_case: ET.Element) -> tuple[str | None, str]:
    selector = next(
        (
            property_.get("value")
            for property_ in test_case.findall("./properties/property")
            if property_.get("name") == "specfact.selector"
        ),
        None,
    )
    if test_case.find("failure") is not None:
        return selector, "failed"
    if test_case.find("error") is not None:
        return selector, "errored"
    if test_case.find("skipped") is not None:
        return selector, "skipped"
    return selector, "passed"


def _junit_results(junit_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    try:
        root = ET.fromstring(junit_path.read_bytes())
    except (OSError, ET.ParseError):
        return {}, ["junit-malformed"]
    results: dict[str, list[str]] = {}
    findings: list[str] = []
    for test_case in root.iter("testcase"):
        selector, outcome = _junit_case_result(test_case)
        if not _is_text(selector):
            findings.append("junit-selector-missing")
            continue
        results.setdefault(str(selector), []).append(outcome)
    return results, findings


def _plan_cases(plan_report: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    plan = plan_report.get("plan")
    if (
        not isinstance(plan, Mapping)
        or not isinstance(plan.get("cases"), list)
        or not _is_text(plan.get("mapping_digest"))
    ):
        raise ValueError("plan report must contain a lifecycle plan")
    cases = [dict(case) for case in plan["cases"] if isinstance(case, Mapping) and _is_text(case.get("node_id"))]
    return str(plan["mapping_digest"]), cases


def _selector_result_finding(selector: str, outcomes: list[str], expected_outcome: str, maturity: str) -> str | None:
    if not outcomes:
        return f"uncollected-selector:{selector}"
    if len(outcomes) != 1:
        return f"duplicate-selector-result:{selector}"
    if outcomes[0] != expected_outcome:
        return f"{maturity}-proof-not-{expected_outcome}:{selector}"
    return None


def _selector_result_findings(expected: set[str], results: Mapping[str, list[str]], run_stage: str) -> list[str]:
    expected_outcome = "failed" if run_stage == "red" else "passed"
    maturity = "red" if run_stage == "red" else "final"
    findings = [
        _selector_result_finding(selector, results.get(selector, []), expected_outcome, maturity)
        for selector in sorted(expected)
    ]
    return [finding for finding in findings if finding is not None]


def _prior_red_proof_findings(prior_red_proof: Mapping[str, Any] | None, mapping_digest: str) -> list[str]:
    if prior_red_proof is None:
        return ["prior-red-proof-missing"]
    valid = (
        prior_red_proof.get("observed_maturity") == "red"
        and prior_red_proof.get("mapping_digest") == mapping_digest
        and prior_red_proof.get("gate_decision") == "pass"
    )
    return [] if valid else ["prior-red-proof-invalid"]


@beartype
@ensure(lambda result: isinstance(result, dict))
def reconcile_junit(
    plan_report: Mapping[str, Any],
    junit_path: Path,
    *,
    run_stage: str,
    source_ref: str,
    prior_red_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconcile trusted JUnit results without starting a test process."""
    if run_stage not in {"red", "final"}:
        raise ValueError("run stage must be red or final")
    if _SOURCE_REF_PATTERN.fullmatch(source_ref) is None:
        raise ValueError("source ref must be a full lowercase Git object id")
    mapping_digest, cases = _plan_cases(plan_report)
    results, junit_findings = _junit_results(junit_path)
    expected = {str(case["node_id"]) for case in cases}
    findings = [*junit_findings, *_selector_result_findings(expected, results, run_stage)]
    if run_stage == "final":
        findings.extend(_prior_red_proof_findings(prior_red_proof, mapping_digest))
    observed = "red" if run_stage == "red" else "verified"
    report = _lifecycle_report(
        required_maturity=observed,
        observed_maturity=observed if not findings else "incomplete",
        mapping_digest=mapping_digest,
        findings=findings,
        cases=[dict(case) for case in cases],
    )
    report["execution_proof"] = {
        "run_stage": run_stage,
        "source_ref": source_ref,
        "junit_digest": _sha256_file(junit_path),
        "selectors": sorted(expected),
    }
    return report
