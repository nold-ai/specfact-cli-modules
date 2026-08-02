"""Deterministic lifecycle evidence for mapped Requirements scenarios.

This module deliberately validates and reconciles evidence only. Test execution,
review-provider integration, and Git ancestry checks remain core-owned.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from stat import S_ISREG
from typing import Any, cast

from beartype import beartype
from icontract import ensure


MATURITY_ORDER = {
    "incomplete": 0,
    "planned": 1,
    "accepted": 2,
    "test-authored": 3,
    "red": 4,
    "verified": 5,
}
_SUPPORTED_METHODS = {"test", "analysis", "inspection", "demonstration"}
SUPPORTED_REQUIRED_MATURITY = frozenset({"planned", "accepted", "test-authored", "red", "verified"})
DELIVERY_STATUS_BY_MATURITY = {
    "planned": "proposal-only",
    "accepted": "proposal-accepted",
    "test-authored": "test-design",
    "red": "failing-first-proven",
    "verified": "implementation-verified",
    "incomplete": "incomplete",
}
IMPLEMENTATION_EVIDENCE_BY_MATURITY = {
    "planned": "not-yet-available",
    "accepted": "not-yet-available",
    "test-authored": "tests-not-executed",
    "red": "failing-first-proven",
    "verified": "passing-after-red-proven",
    "incomplete": "not-available",
}
_SOURCE_REF_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
_PYTEST_SELECTOR_PATTERN = re.compile(r"(?!-)[A-Za-z0-9_./-]+\.py::[A-Za-z0-9_:.\[\]-]+")
_SELECTOR_FORBIDDEN_CHARACTERS = frozenset('$&;|`<>*?(){}!\\"')
MAX_JUNIT_BYTES = 10 * 1024 * 1024
_SCALAR_TAGS = {
    bool: "bool",
    int: "int",
    float: "float",
    str: "str",
    datetime: "datetime",
    date: "date",
}


def _encoded_sort_key(value: list[Any]) -> str:
    """Return a deterministic order key for a canonical encoded node."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def _scalar_node(value: object) -> list[Any] | None:
    """Encode supported scalar values while retaining their Python/YAML type."""
    if value is None:
        return ["none"]
    tag = _SCALAR_TAGS.get(type(value))
    if tag is None:
        return None
    encoded = value if tag == "bool" else cast(float, value).hex() if tag == "float" else str(value)
    return [tag, encoded]


def _json_safe(value: object) -> list[Any]:
    """Encode values injectively for stable cross-process lifecycle digests."""
    if (scalar := _scalar_node(value)) is not None:
        return scalar
    if isinstance(value, Mapping):
        entries = [[_json_safe(key), _json_safe(item)] for key, item in value.items()]
        return [
            "mapping",
            sorted(entries, key=lambda entry: (_encoded_sort_key(entry[0]), _encoded_sort_key(entry[1]))),
        ]
    if isinstance(value, list | tuple):
        tag = "list" if isinstance(value, list) else "tuple"
        return [tag, [_json_safe(item) for item in value]]
    if isinstance(value, set | frozenset):
        return ["set", sorted((_json_safe(item) for item in value), key=_encoded_sort_key)]
    raise ValueError(f"unsupported-sidecar-value:{type(value).__name__}")


@beartype
@ensure(lambda result: result.startswith("sha256:"))
def canonical_digest(value: Mapping[Any, Any]) -> str:
    """Return a stable SHA-256 digest for a mapping, including malformed YAML values."""
    encoded = json.dumps(_json_safe(value), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _is_text(value: object) -> bool:
    """Return whether a value is a non-blank text field."""
    return isinstance(value, str) and bool(value.strip())


def _is_digest(value: object) -> bool:
    """Return whether a value is one exact canonical SHA-256 digest."""
    return isinstance(value, str) and _DIGEST_PATTERN.fullmatch(value) is not None


def _mapping_payload(mapping: Mapping[Any, Any]) -> dict[str, Any]:
    """Return the semantically relevant source mapping for digest calculation."""
    return {
        "schema_version": mapping.get("schema_version"),
        "requirements": mapping.get("requirements"),
    }


def _append_missing(findings: list[str], value: object, field: str, identifier: str) -> None:
    """Record a deterministic missing-field finding when a value is blank."""
    if not _is_text(value):
        findings.append(f"missing-{field}:{identifier}")


def _validate_selector(case: Mapping[str, Any], case_id: str, findings: list[str]) -> dict[str, str] | None:
    """Validate a structured, repository-contained pytest selector."""
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
    test_path, _, _ = node_id.partition("::")
    path_parts = PurePosixPath(test_path).parts
    if (
        PurePosixPath(test_path).is_absolute()
        or ".." in path_parts
        or any(character in node_id for character in _SELECTOR_FORBIDDEN_CHARACTERS)
    ):
        findings.append(f"invalid-selector:{case_id}")
        return None
    return {"runner": runner, "node_id": node_id}


def _selector_required(method: object, required_maturity: str, case: Mapping[str, Any]) -> bool:
    """Return whether the case must identify an exact executable test."""
    return (method == "test" and MATURITY_ORDER[required_maturity] >= MATURITY_ORDER["test-authored"]) or isinstance(
        case.get("selector"), Mapping
    )


def _validated_case(
    case: object, requirement_id: str, required_maturity: str
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate and preserve one declared verification case for the plan."""
    if not isinstance(case, Mapping):
        return None, [f"invalid-verification-case:{requirement_id}"]
    case_id = case.get("case_id")
    if not _is_text(case_id):
        return None, [f"missing-case-id:{requirement_id}"]
    case_name = str(case_id)
    findings: list[str] = []
    for field in ("scenario_id", "method", "intent", "observable"):
        _append_missing(findings, case.get(field), field, case_name)
    method = case.get("method")
    if method not in _SUPPORTED_METHODS:
        return None, [*findings, f"unsupported-verification-method:{case_name}"]
    selector = (
        _validate_selector(case, case_name, findings) if _selector_required(method, required_maturity, case) else None
    )
    preserved = {
        "requirement_id": requirement_id,
        "case_id": case_name,
        "scenario_id": case.get("scenario_id"),
        "method": method,
        "intent": case.get("intent"),
        "observable": case.get("observable"),
    }
    if selector is not None:
        preserved["selector"] = selector
        preserved["runner"] = selector["runner"]
        preserved["node_id"] = selector["node_id"]
    return preserved, findings


def _touchpoint_findings(requirement: Mapping[str, Any], identifier: str) -> list[str]:
    """Validate declared customer-facing requirement touchpoints."""
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
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate all verification cases while retaining their declared semantics."""
    verification_cases = requirement.get("verification_cases")
    if not isinstance(verification_cases, list) or not verification_cases:
        return [], [f"missing-verification-cases:{identifier}"]
    cases: list[dict[str, Any]] = []
    findings: list[str] = []
    for case in verification_cases:
        validated, case_findings = _validated_case(case, identifier, required_maturity)
        findings.extend(case_findings)
        if validated is not None:
            cases.append(validated)
    return cases, findings


def _requirement_cases(
    requirement_id: object, requirement: object, required_maturity: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate one requirement and attach its touchpoints to its cases."""
    if not _is_text(requirement_id) or not isinstance(requirement, Mapping):
        return [], ["invalid-requirement-entry"]
    identifier = str(requirement_id)
    findings: list[str] = []
    _append_missing(findings, requirement.get("rationale"), "rationale", identifier)
    findings.extend(_touchpoint_findings(requirement, identifier))
    cases, case_findings = _verification_case_results(requirement, identifier, required_maturity)
    touchpoints = requirement.get("touchpoints")
    if isinstance(touchpoints, list):
        for case in cases:
            case["touchpoints"] = [dict(touchpoint) for touchpoint in touchpoints if isinstance(touchpoint, Mapping)]
    return cases, [*findings, *case_findings]


def _duplicate_selector_findings(cases: list[dict[str, Any]]) -> list[str]:
    """Return duplicate exact-test selector findings for executable cases."""
    selectors = [str(case["node_id"]) for case in cases if _is_text(case.get("node_id"))]
    duplicates = {selector for selector in selectors if selectors.count(selector) > 1}
    return [f"duplicate-selector:{selector}" for selector in sorted(duplicates)]


def _validated_cases(mapping: Mapping[Any, Any], required_maturity: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate all mapping requirements and return deterministic plan cases."""
    if mapping.get("schema_version") != "2":
        return [], ["unsupported-sidecar-schema"]
    requirements = mapping.get("requirements")
    if not isinstance(requirements, Mapping) or not requirements:
        return [], ["missing-requirements"]
    cases: list[dict[str, Any]] = []
    findings: list[str] = []
    for requirement_id, requirement in sorted(requirements.items(), key=lambda item: str(item[0])):
        requirement_cases, requirement_findings = _requirement_cases(requirement_id, requirement, required_maturity)
        cases.extend(requirement_cases)
        findings.extend(requirement_findings)
    return cases, sorted({*findings, *_duplicate_selector_findings(cases)})


def _valid_acceptance(review_evidence: Mapping[str, Any] | None, mapping_digest: str) -> list[str]:
    """Validate a provider-neutral acceptance record bound to the mapping."""
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


@beartype
@ensure(lambda result: isinstance(result, dict) and "plan_digest" in result)
def build_plan(mapping_digest: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a deterministic, complete plan and its stable identity digest."""
    ordered_cases = sorted(
        cases,
        key=lambda case: (str(case.get("requirement_id")), str(case.get("case_id")), canonical_digest(case)),
    )
    identity = {"mapping_digest": mapping_digest, "cases": ordered_cases}
    return {**identity, "plan_digest": canonical_digest(identity)}


def _lifecycle_report(
    *,
    required_maturity: str,
    observed_maturity: str,
    mapping_digest: str,
    findings: list[str],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a lifecycle report without implying more evidence than exists."""
    passed = not findings and MATURITY_ORDER[observed_maturity] >= MATURITY_ORDER[required_maturity]
    delivery_status, implementation_evidence = lifecycle_status(observed_maturity)
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
        "plan": build_plan(mapping_digest, cases),
    }


@beartype
@ensure(lambda result: len(result) == 2)
def lifecycle_status(observed_maturity: str) -> tuple[str, str]:
    """Return the delivery and execution labels for one observed maturity."""
    try:
        return DELIVERY_STATUS_BY_MATURITY[observed_maturity], IMPLEMENTATION_EVIDENCE_BY_MATURITY[observed_maturity]
    except KeyError as error:
        raise ValueError(f"unsupported observed maturity: {observed_maturity}") from error


@beartype
@ensure(lambda result: isinstance(result, dict))
def evaluate_mapping(
    mapping: Mapping[Any, Any],
    *,
    required_maturity: str,
    review_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a schema-v2 mapping without executing tests."""
    if required_maturity not in SUPPORTED_REQUIRED_MATURITY:
        raise ValueError("required maturity must be planned, accepted, test-authored, red, or verified")
    try:
        mapping_digest = canonical_digest(_mapping_payload(mapping))
    except ValueError as error:
        return _lifecycle_report(
            required_maturity=required_maturity,
            observed_maturity="incomplete",
            mapping_digest=canonical_digest({"invalid": type(error).__name__}),
            findings=[str(error)],
            cases=[],
        )
    cases, findings = _validated_cases(mapping, required_maturity)
    observed = "incomplete" if findings else "planned"
    if not findings and MATURITY_ORDER[required_maturity] >= MATURITY_ORDER["accepted"]:
        acceptance_findings = _valid_acceptance(review_evidence, mapping_digest)
        findings.extend(acceptance_findings)
        if not acceptance_findings:
            observed = "accepted"
    if not findings and MATURITY_ORDER[required_maturity] >= MATURITY_ORDER["test-authored"]:
        observed = "test-authored"
    if required_maturity in {"red", "verified"}:
        findings.append(f"execution-proof-required:{required_maturity}")
        observed = "incomplete"
    return _lifecycle_report(
        required_maturity=required_maturity,
        observed_maturity=observed,
        mapping_digest=mapping_digest,
        findings=findings,
        cases=cases,
    )


def _junit_case_result(test_case: ET.Element) -> tuple[str | None, str]:
    """Extract the canonical selector and terminal outcome from one testcase."""
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


def _junit_results(junit_path: Path) -> tuple[dict[str, list[str]], list[str], str | None]:
    """Safely parse bounded JUnit XML and preserve a digest only on success."""
    try:
        descriptor = os.open(junit_path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as junit_file:
            if not S_ISREG(os.fstat(junit_file.fileno()).st_mode):
                return {}, ["junit-not-regular-file"], None
            payload = junit_file.read(MAX_JUNIT_BYTES + 1)
    except OSError:
        return {}, ["junit-malformed"], None
    if len(payload) > MAX_JUNIT_BYTES:
        return {}, ["junit-too-large"], None
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        return {}, ["junit-unsafe-doctype"], None
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return {}, ["junit-malformed"], None
    results: dict[str, list[str]] = {}
    findings: list[str] = []
    for test_case in root.iter("testcase"):
        selector, outcome = _junit_case_result(test_case)
        if not _is_text(selector):
            findings.append("junit-selector-missing")
            continue
        results.setdefault(str(selector), []).append(outcome)
    return results, findings, f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _trusted_plan(plan_report: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the plan only when its lifecycle report authorizes reconciliation."""
    if plan_report.get("gate_decision") != "pass" or plan_report.get("observed_maturity") != "test-authored":
        raise ValueError("plan report must be a passing test-authored lifecycle report")
    plan = plan_report.get("plan")
    if (
        not isinstance(plan, Mapping)
        or not isinstance(plan.get("cases"), list)
        or not _is_digest(plan.get("mapping_digest"))
        or not _is_digest(plan.get("plan_digest"))
    ):
        raise ValueError("plan report must contain a lifecycle plan")
    return plan


def _consistent_plan_cases(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return nonempty plan cases only when their identity digest is valid."""
    all_cases = [dict(case) for case in plan["cases"] if isinstance(case, Mapping)]
    mapping_digest = plan["mapping_digest"]
    if not isinstance(mapping_digest, str):
        raise ValueError("plan report must contain a valid mapping digest")
    expected_plan = build_plan(mapping_digest, all_cases)
    if expected_plan["plan_digest"] != plan["plan_digest"]:
        raise ValueError("plan report has an invalid plan digest")
    if len(all_cases) != len(plan["cases"]) or not all_cases:
        raise ValueError("plan report must contain nonempty valid cases")
    return all_cases


def _execution_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return unique executable cases whose selectors remain structurally safe."""
    executable_cases = [case for case in cases if case.get("method") == "test"]
    if not executable_cases:
        raise ValueError("plan report must contain executable test cases")
    selectors: list[str] = []
    for case in executable_cases:
        findings: list[str] = []
        validated = _validate_selector(case, str(case.get("case_id", "<unknown>")), findings)
        if validated is None or findings or case.get("node_id") != validated["node_id"]:
            raise ValueError("plan report contains an invalid test selector")
        selectors.append(validated["node_id"])
    if len(set(selectors)) != len(selectors):
        raise ValueError("plan report contains duplicate test selectors")
    return executable_cases


def _plan_cases(plan_report: Mapping[str, Any]) -> tuple[str, str, Mapping[str, Any], list[dict[str, Any]]]:
    """Accept only a complete test-authored lifecycle plan for reconciliation."""
    plan = _trusted_plan(plan_report)
    all_cases = _consistent_plan_cases(plan)
    cases = _execution_cases(all_cases)
    return str(plan["mapping_digest"]), str(plan["plan_digest"]), plan, cases


def _selector_result_finding(selector: str, outcomes: list[str], expected_outcome: str, maturity: str) -> str | None:
    """Describe a selector result which cannot serve as the requested proof."""
    if not outcomes:
        return f"uncollected-selector:{selector}"
    if len(outcomes) != 1:
        return f"duplicate-selector-result:{selector}"
    if outcomes[0] != expected_outcome:
        return f"{maturity}-proof-{outcomes[0]}-not-{expected_outcome}:{selector}"
    return None


def _selector_result_findings(expected: set[str], results: Mapping[str, list[str]], run_stage: str) -> list[str]:
    """Reconcile every expected selector with one JUnit terminal outcome."""
    expected_outcome = "failed" if run_stage == "red" else "passed"
    maturity = "red" if run_stage == "red" else "final"
    findings = [
        _selector_result_finding(selector, results.get(selector, []), expected_outcome, maturity)
        for selector in sorted(expected)
    ]
    return [finding for finding in findings if finding is not None]


def _prior_red_proof_findings(
    prior_red_proof: Mapping[str, Any] | None, mapping_digest: str, plan_digest: str
) -> list[str]:
    """Require final proof to use the same mapped test plan as a valid red proof."""
    if prior_red_proof is None:
        return ["prior-red-proof-missing"]
    valid = (
        prior_red_proof.get("observed_maturity") == "red"
        and prior_red_proof.get("mapping_digest") == mapping_digest
        and prior_red_proof.get("plan_digest") == plan_digest
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
    mapping_digest, plan_digest, submitted_plan, cases = _plan_cases(plan_report)
    results, junit_findings, junit_digest = _junit_results(junit_path)
    expected = {str(case["node_id"]) for case in cases}
    findings = [*junit_findings, *_selector_result_findings(expected, results, run_stage)]
    if run_stage == "final":
        findings.extend(_prior_red_proof_findings(prior_red_proof, mapping_digest, plan_digest))
    observed = "red" if run_stage == "red" else "verified"
    report = _lifecycle_report(
        required_maturity=observed,
        observed_maturity=observed if not findings else "incomplete",
        mapping_digest=mapping_digest,
        findings=findings,
        cases=[dict(case) for case in cases],
    )
    report["execution_plan"] = report.pop("plan")
    report["plan"] = dict(submitted_plan)
    report["execution_proof"] = {
        "run_stage": run_stage,
        "source_ref": source_ref,
        "selectors": sorted(expected),
    }
    report["plan_digest"] = plan_digest
    if junit_digest is not None:
        report["execution_proof"]["junit_digest"] = junit_digest
    return report
