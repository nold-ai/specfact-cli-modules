"""Bounded, opt-in observations for one immutable public diagnostic experiment."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from specfact_code_review.run.findings import ReviewFinding, ReviewReport


OUTPUT_ENV = "SPECFACT_SUPPLEMENTAL_DIAGNOSTIC_OUTPUT"
MAX_RECORDS = 80
MAX_BYTES = 65536
MAX_SOURCE_BYTES = 1 << 20
EXPECTED_TREES = ("0ef24f43e4cf4fe13d7b3d95e62165a4d2bbafc6", "acea0127e0ed3472c3439a6aa87cc4353eaa18c5")
EXPECTED_COMMITS = ("593656f675eaf4954b609aca51aa6504367dc02e", "5b451ec066e0ea5cbd8a97ef3b59d915ae54fe5b")
MEMBERS = (
    "ruff",
    "radon",
    "semgrep-clean",
    "ai-bloat-ast",
    "ast-clean-code",
    "basedpyright",
    "pylint",
    "contracts",
    "semgrep-bugs",
    "targeted-pytest-coverage",
)
OUTCOMES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}
REASONS = {
    "snapshot_member_incomplete",
    "differential_finding_mapping_failed",
    "analyzer_reported_incomplete_execution",
    "finding_correspondence_ambiguous",
    "source_correspondence_unknown",
    "project_range_runtime_identity_mismatch",
}
MEMBER_TOOLS = {
    "ruff": {"ruff"},
    "radon": {"radon", "radon-kiss"},
    "semgrep-clean": {"semgrep"},
    "ai-bloat-ast": {"ast"},
    "ast-clean-code": {"ast"},
    "basedpyright": {"basedpyright"},
    "pylint": {"pylint"},
    "contracts": {"crosshair", "contract_runner"},
    "semgrep-bugs": {"semgrep"},
    "targeted-pytest-coverage": {"pytest"},
}
ERROR_RULES = {
    "crosshair": {"tool_error", "CROSSHAIR_INCOMPLETE_EVIDENCE"},
    "pytest": {"tool_error", "TEST_OUTCOME_NOT_PASS", "TEST_COVERAGE_POLICY_FAILED"},
}
PYTEST_CODES = {
    "project_pytest_collection_failed",
    "project_pytest_collection_error",
    "project_pytest_execution_incomplete",
    "project_pytest_unexecuted",
    "project_pytest_coverage_missing",
    "project_pytest_internal_error",
    "project_pytest_configuration_or_collection_failed",
    "project_pytest_failure_without_observed_test",
    "project_pytest_coverage_evidence_unavailable",
    "project_pytest_coverage_controller_observation_missing",
}


def _catalog_rules() -> set[str]:
    catalog = Path(__file__).resolve().parents[1] / ".semgrep/bugs.yaml"
    payload = catalog.read_bytes()
    if len(payload) > 65536:
        return set()
    data = yaml.safe_load(payload)
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list) or len(rules) > 256:
        return set()
    return {
        rule["id"]
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("id"), str) and re.fullmatch(r"[a-z0-9-]{1,100}", rule["id"])
    }


def _function(source: bytes, line: int) -> str:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return "UNAVAILABLE"
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.lineno <= line <= (node.end_lineno or node.lineno)
        and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,79}", node.name)
    ]
    return max(matches, key=lambda node: node.lineno).name if matches else "UNAVAILABLE"


def _location(finding: ReviewFinding, snapshot: Any) -> dict[str, object] | None:
    path = finding.file
    if not re.fullmatch(r"[A-Za-z0-9_./-]{1,240}", path) or ".." in PurePosixPath(path).parts or path.startswith("/"):
        return None
    source = snapshot.contents.get(path)
    entry = snapshot.entries.get(path)
    if (
        not isinstance(source, bytes)
        or len(source) > MAX_SOURCE_BYTES
        or entry is None
        or entry.object_type != "blob"
        or entry.git_mode not in {"100644", "100755"}
    ):
        return None
    blob = b"blob " + str(len(source)).encode() + b"\0" + source
    if hashlib.sha1(blob, usedforsecurity=False).hexdigest() != entry.object_id:
        return None
    if not 1 <= finding.line <= len(source.splitlines()):
        return None
    return {
        "file": path,
        "line": finding.line,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "function": _function(source, finding.line),
    }


def _diagnostic(finding: ReviewFinding) -> str:
    message = finding.message
    if finding.tool == "crosshair" and message.startswith("Unrecognized CrossHair output:"):
        return "crosshair_unrecognized_output"
    if finding.tool == "pylint" and message.startswith("Unable to parse pylint output:") and "timed out" in message:
        return "pylint_timeout_observed"
    if finding.tool == "pytest":
        prefix = message.split(":", 1)[0].split(";", 1)[0]
        if prefix in PYTEST_CODES:
            return prefix
    return "UNAVAILABLE"


def _member_records(report: ReviewReport) -> list[dict[str, str]]:
    evidence = report.analyzer_evidence
    if not isinstance(evidence, list) or len(evidence) > len(MEMBERS):
        return []
    records = []
    seen = set()
    for node in evidence:
        if not isinstance(node, dict) or node.get("id") not in MEMBERS or node["id"] in seen:
            return []
        seen.add(node["id"])
        for side, value in (("combined", node), ("base", node.get("base")), ("head", node.get("head"))):
            if not isinstance(value, dict):
                continue
            outcome = value.get("evidence_outcome")
            reason = value.get("diagnostic")
            records.append(
                {
                    "member": node["id"],
                    "side": side,
                    "outcome": outcome if isinstance(outcome, str) and outcome in OUTCOMES else "UNAVAILABLE",
                    "diagnostic": reason if isinstance(reason, str) and reason in REASONS else "UNAVAILABLE",
                }
            )
    return records


def _finding_key(finding: ReviewFinding) -> tuple[str, str, str, int, str, str, bool]:
    return (
        finding.tool,
        finding.rule,
        finding.file,
        finding.line,
        " ".join(finding.message.split()),
        finding.severity,
        bool(finding.blocking),
    )


def _selected_findings(report: ReviewReport, results: Any) -> list[tuple[str, str, ReviewFinding, str]]:
    introduced = Counter(
        _finding_key(finding)
        for finding in report.findings
        if finding.tool == "semgrep" and finding.differential_state == "introduced"
    )
    selected = []
    for side, result in zip(("base", "head"), results, strict=True):
        for member in MEMBERS:
            for finding in result.findings_by_member.get(member, []):
                key = _finding_key(finding)
                state = "UNAVAILABLE"
                if side == "head" and member == "semgrep-bugs" and introduced[key] > 0:
                    state = "introduced"
                    introduced[key] -= 1
                if finding.category == "tool_error" or finding.tool == "pytest" or state == "introduced":
                    selected.append((side, member, finding, state))
    return selected


def _valid_identity(member: str, finding: ReviewFinding, catalog: set[str]) -> bool:
    if finding.tool not in MEMBER_TOOLS[member]:
        return False
    if member == "semgrep-bugs" and finding.tool == "semgrep" and finding.rule in catalog:
        return True
    return finding.rule in ERROR_RULES.get(finding.tool, {"tool_error"})


def _project_findings(report: ReviewReport, resolution: Any, results: Any) -> tuple[list[dict[str, object]], int]:
    rules = _catalog_rules()
    selected = _selected_findings(report, results)
    records: list[dict[str, object]] = []
    seen = set()
    snapshots = {"base": resolution.base_snapshot, "head": resolution.head_snapshot}
    for side, member, finding, state in selected[:MAX_RECORDS]:
        identity = (side, member, *_finding_key(finding))
        location = _location(finding, snapshots[side])
        if location is None or identity in seen or not _valid_identity(member, finding, rules):
            continue
        seen.add(identity)
        records.append(
            {
                "side": side,
                "member": member,
                "rule": finding.rule,
                "differential_state": state,
                "diagnostic": _diagnostic(finding),
                "location_is_cause": False,
                **location,
            }
        )
    return records, len(selected) - len(records)


def build_sidecar(report: ReviewReport, resolution: Any, results: Any) -> dict[str, Any]:
    """Project existing results without granting them required-gate authority."""
    payload: dict[str, Any] = {
        "schema": "supplemental-diagnostic-v1",
        "purpose": "SUPPLEMENTARY_DIAGNOSTIC_ONLY",
        "status": "UNAVAILABLE",
        "complete": False,
        "findings": [],
        "members": [],
        "omitted_findings": 0,
        "actual_loaded_adapter": "UNAVAILABLE",
        "effective_deadline": "UNAVAILABLE",
        "original_exit_code": report.ci_exit_code,
        "original_assurance": report.assurance_status,
    }
    snapshots = (resolution.base_snapshot, resolution.head_snapshot)
    if tuple(snapshot.tree for snapshot in snapshots) != EXPECTED_TREES or len(results) != 2:
        return payload
    if len(report.findings) > 10000 or any(
        sum(len(items) for items in result.findings_by_member.values()) > 10000 for result in results
    ):
        return payload
    records, omitted = _project_findings(report, resolution, results)
    payload.update(
        status="OBSERVED",
        findings=records,
        omitted_findings=omitted,
        members=_member_records(report),
        base_commit=EXPECTED_COMMITS[0],
        head_commit=EXPECTED_COMMITS[1],
        base_tree=EXPECTED_TREES[0],
        head_tree=EXPECTED_TREES[1],
    )
    # Unclassified private diagnostics intentionally remain incomplete.
    payload["complete"] = (
        omitted == 0
        and len(payload["members"]) == 30
        and all(record["diagnostic"] != "UNAVAILABLE" for record in records)
        and all(
            member["diagnostic"] != "UNAVAILABLE" and member["outcome"] in OUTCOMES for member in payload["members"]
        )
        and all(record["function"] != "UNAVAILABLE" for record in records)
    )
    if len(json.dumps(payload).encode()) > MAX_BYTES:
        payload.update(
            status="UNAVAILABLE", findings=[], members=[], complete=False, omitted_findings=len(records) + omitted
        )
    return payload


def emit_sidecar(report: ReviewReport, resolution: Any, results: Any) -> str:
    """Create a private, non-overwriting observation file when explicitly requested."""
    configured = os.environ.get(OUTPUT_ENV)
    if configured is None:
        return "DISABLED"
    try:
        output = Path(configured)
        if not output.is_absolute() or output.parent.resolve() != output.parent or output.name != "diagnostic.json":
            return "UNAVAILABLE"
        payload = json.dumps(build_sidecar(report, resolution, results), sort_keys=True).encode()
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
    except (OSError, ValueError, TypeError, AttributeError, RecursionError, yaml.YAMLError):
        return "UNAVAILABLE"
    return "WRITTEN"
