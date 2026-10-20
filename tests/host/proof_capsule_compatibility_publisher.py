"""SDK-free full-publisher controls using explicitly synthetic private receipts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys

import pytest

from tests.support.capsule_review_fixtures import independent_review_job


CANARY = "PRIVATE_COMPATIBILITY_CANARY"
PREDICATE = "pinned_version_string_inequality"
CATEGORY = "contracts_pinned_transitive"
SIDES = ("base", "head")
NATIVE_REASON = "z3-solver: target=0.0.0+private.compatibility.canary, sealed entry=5.1.0.0"
CONFLICT = "project_analyzer_dependency_incompatible:" + NATIVE_REASON


def conflict_digest(conflicts):
    return "sha256:" + hashlib.sha256(json.dumps(conflicts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def synthetic_receipt():
    """Publisher input only, never evidence that a production observer ran."""
    rows = []
    for index, side in enumerate(SIDES):
        rows.append(
            {
                "status": "observed",
                "binding": {
                    "side": side,
                    "descriptor_identity": "sha256:" + str(index + 1) * 64,
                    "project_identity": "sha256:" + str(index + 3) * 64,
                    "environment_id": "linux-x86_64-cp312",
                    "worker_identity": "sha256:" + "5" * 64,
                    "source_roots": ["src"],
                },
                "native_conflicts": {"contracts": CONFLICT},
                "conflict_digest": conflict_digest({"contracts": CONFLICT}),
                "witnesses": [
                    {
                        "member": "contracts",
                        "predicate": PREDICATE,
                        "category": CATEGORY,
                        "native_reason": NATIVE_REASON,
                    }
                ],
                "signed_reference_matches": True,
                "clearing_subsets": [[CATEGORY]],
            }
        )
    return {"schema": "compatibility-observation-v1", "sides": rows}


def synthetic_report(receipt):
    bindings = {}
    members: dict[str, object] = {"id": "contracts"}
    for row in receipt["sides"]:
        binding = row["binding"]
        side = binding["side"]
        bindings[side] = {
            "status": "PASS",
            "schema": "project-runtime-layer-v2",
            "identity": binding["descriptor_identity"],
            "project_identity": binding["project_identity"],
            "environment_id": binding["environment_id"],
            "authority": "local_build",
            "protected_pr_eligible": False,
            "source_roots": binding["source_roots"],
        }
        members[side] = {"execution_state": "error", "evidence_outcome": "UNKNOWN", "diagnostic": CONFLICT}
    return {
        "findings": [],
        "analyzer_evidence": [members],
        "scope_evidence": {"project_runtime": bindings},
        "assurance_status": "UNKNOWN",
        "overall_verdict": "FAIL",
        "private_canary": CANARY,
    }


def expected_proof(status="native_compatibility_clear", categories=(CATEGORY,)):
    return {
        "status": "observed",
        "records": [
            {"side": side, "analyzer": "contracts", "predicate": PREDICATE, "category": CATEGORY} for side in SIDES
        ],
        "reference_comparison": {"status": status, "substitution_categories": list(categories)},
    }


def legacy_summary():
    return {
        "phase": "independent_review",
        "report_outcome": "structured_report",
        "assurance_status": "UNKNOWN",
        "overall_verdict": "FAIL",
        "findings_present": False,
        "tool_error_present": False,
        "execution_error_present": True,
        "unknown_evidence_present": True,
        "error_analyzers": ["contracts"],
        "unknown_analyzers": ["contracts"],
        "diagnostic_observations": ["unclassified"],
        "error_analyzer_sides": {"contracts": ["base", "head"]},
        "crosshair_failure_observations": [],
        "snapshot_diagnostic_observations": [
            {"analyzer": "contracts", "side": side, "reason": "unclassified"} for side in SIDES
        ],
        "snapshot_diagnostic_facts": [
            {
                "analyzer": "contracts",
                "side": side,
                "shape": "string",
                "length_bucket": "within_bound",
                "recognized_leading_token": False,
            }
            for side in SIDES
        ],
        "snapshot_producer_categories": [
            {"analyzer": "contracts", "side": side, "category": "project_analyzer_dependency_incompatible"}
            for side in SIDES
        ],
    }


def publisher_fixture(tmp_path, receipt, report):
    trusted = tmp_path / "trusted"
    trusted.mkdir(mode=0o700)
    (trusted / "venv/bin").mkdir(parents=True)
    (trusted / "venv/bin/python").symlink_to(sys.executable)
    (trusted / "review-attempted").touch()
    (trusted / "review.private.log").write_text(CANARY)
    (trusted / "review.private.json").write_text(json.dumps(report))
    receipt_path = trusted / "compatibility.private.json"
    receipt_path.write_text(json.dumps(receipt))
    receipt_path.chmod(0o600)
    return trusted


def run_publisher(trusted):
    step = next(step for step in independent_review_job()["steps"] if "PY_REVIEW_FAILURE" in step.get("run", ""))
    original = {path.name: path.read_bytes() for path in trusted.glob("review.private.*")}
    environment = dict(os.environ, TRUSTED_ROOT=str(trusted))
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=trusted,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    (trusted / "publisher.stdout").write_text(result.stdout)
    (trusted / "publisher.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert CANARY not in result.stdout
    assert "private.compatibility.canary" not in result.stdout
    assert {path.name: path.read_bytes() for path in trusted.glob("review.private.*")} == original
    return json.loads(result.stdout)


REPORT_MUTATIONS = {
    "status": "FAIL",
    "schema": "foreign",
    "identity": "sha256:" + "9" * 64,
    "project_identity": "sha256:" + "9" * 64,
    "environment_id": "linux-x86_64-cp311",
    "authority": "protected",
    "protected_pr_eligible": True,
    "source_roots": [CANARY],
}


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "oversized",
        *REPORT_MUTATIONS,
        "diagnostic",
        "duplicate_member",
        "missing_side",
        "swapped_sides",
        "malformed_report",
        "duplicate_json",
        "over_cap",
        "beyond_ten",
        "not_incomplete",
        "extra_native_member",
    ],
)
def test_publisher_binds_complete_report(tmp_path, case):
    receipt = synthetic_receipt()
    report = synthetic_report(receipt)
    mutate_report_binding(receipt, report, case)
    trusted = publisher_fixture(tmp_path, receipt, report)
    mutate_report_bytes(trusted, report, case)
    projected = run_publisher(trusted)
    expected = expected_proof() if case in {"valid", "oversized"} else {"status": "unavailable"}
    assert projected.get("compatibility_proof") == expected
    if case == "valid":
        assert projected == legacy_summary() | {"compatibility_proof": expected}
    if case == "oversized":
        assert projected["assurance_status"] == "UNAVAILABLE"
        assert projected["overall_verdict"] == "UNAVAILABLE"
        assert projected["report_outcome"] == "oversized_report"


def mutate_report_binding(receipt, report, case):
    if case in REPORT_MUTATIONS:
        report["scope_evidence"]["project_runtime"]["base"][case] = REPORT_MUTATIONS[case]
    if case == "diagnostic":
        report["analyzer_evidence"][0]["base"]["diagnostic"] += CANARY
    if case == "duplicate_member":
        report["analyzer_evidence"] *= 2
    if case == "missing_side":
        del report["scope_evidence"]["project_runtime"]["head"]
    if case == "swapped_sides":
        report["scope_evidence"]["project_runtime"] = dict(
            zip(SIDES, reversed(list(report["scope_evidence"]["project_runtime"].values())), strict=True)
        )
    if case == "beyond_ten":
        report["analyzer_evidence"] = [{"id": "ruff"}] * 10 + report["analyzer_evidence"]
    if case == "not_incomplete":
        report["analyzer_evidence"][0]["base"] |= {"execution_state": "success", "evidence_outcome": "PASS"}
    if case == "extra_native_member":
        for row in receipt["sides"]:
            row["native_conflicts"]["basedpyright"] = "project_analyzer_dependency_incompatible:" + CANARY
            row["conflict_digest"] = conflict_digest(row["native_conflicts"])


def mutate_report_bytes(trusted, report, case):
    report_path = trusted / "review.private.json"
    if case in {"oversized", "over_cap"}:
        with report_path.open("ab") as stream:
            stream.write(b" " * ((2 if case == "oversized" else 32) * 1024 * 1024 + 1))
    if case == "malformed_report":
        report_path.write_text('{"findings": []')
    if case == "duplicate_json":
        report_path.write_text('{"findings": [],' + json.dumps(report)[1:])


RECEIPT_CASES = [
    "missing",
    "symlink",
    "hardlink",
    "fifo",
    "directory",
    "wrong_mode",
    "oversized",
    "invalid_utf8",
    "invalid_json",
    "duplicate_json",
    "unknown_key",
    "unknown_binding",
    "duplicate_side",
    "missing_side",
    "wrong_digest",
    "wrong_reason",
    "wrong_member",
    "wrong_category",
    "pinned_other",
    "unknown_predicate",
    "boolean_string",
    "wrong_schema",
    "unavailable",
]


@pytest.mark.parametrize("case", RECEIPT_CASES)
def test_publisher_rejects_invalid_receipt(tmp_path, case):
    receipt = synthetic_receipt()
    report = synthetic_report(receipt)
    updates = {
        "wrong_digest": (receipt["sides"][0], "conflict_digest", "sha256:" + "0" * 64),
        "wrong_reason": (receipt["sides"][0]["witnesses"][0], "native_reason", CANARY),
        "wrong_member": (receipt["sides"][0]["witnesses"][0], "member", "basedpyright"),
        "wrong_category": (receipt["sides"][0]["witnesses"][0], "category", "pylint_entry"),
        "pinned_other": (receipt["sides"][0]["witnesses"][0], "category", "other"),
        "unknown_predicate": (receipt["sides"][0]["witnesses"][0], "predicate", CANARY),
        "boolean_string": (receipt["sides"][0], "signed_reference_matches", "true"),
        "wrong_schema": (receipt, "schema", CANARY),
        "unknown_key": (receipt, CANARY, CANARY),
        "unknown_binding": (receipt["sides"][0]["binding"], CANARY, CANARY),
    }
    if case in updates:
        target, key, value = updates[case]
        target[key] = value
    if case == "duplicate_side":
        receipt["sides"] = [receipt["sides"][0], copy.deepcopy(receipt["sides"][0])]
    if case == "missing_side":
        receipt["sides"].pop()
    if case == "unavailable":
        receipt["sides"][1] = {"status": "unavailable", "side": "head"}
    trusted = publisher_fixture(tmp_path, receipt, report)
    path = trusted / "compatibility.private.json"
    mutate_receipt_file(path, case)
    projected = run_publisher(trusted)
    assert projected == legacy_summary() | {"compatibility_proof": {"status": "unavailable"}}


def mutate_receipt_file(path, case):
    if case in {"missing", "symlink", "hardlink", "fifo", "directory"}:
        payload = path.read_bytes()
        path.unlink()
        if case in {"symlink", "hardlink"}:
            target = path.with_name("private-target.json")
            target.write_bytes(payload)
            target.chmod(0o600)
            if case == "symlink":
                path.symlink_to(target)
            else:
                os.link(target, path)
        if case == "fifo":
            os.mkfifo(path, 0o600)
        if case == "directory":
            path.mkdir()
    if case == "wrong_mode":
        path.chmod(0o644)
    replacements = {"oversized": b" " * (64 * 1024 + 1), "invalid_utf8": b"\xff", "invalid_json": b"{"}
    if case in replacements:
        path.write_bytes(replacements[case])
    if case == "duplicate_json":
        path.write_text('{"schema":"foreign",' + path.read_text()[1:])


@pytest.mark.parametrize(
    "case", ["unique", "disjoint", "tied", "larger_common", "unavailable_reference", "other_witness"]
)
def test_publisher_selects_common_reference_subset(tmp_path, case):
    receipt = synthetic_receipt()
    report = synthetic_report(receipt)
    expected = expected_proof()
    base, head = receipt["sides"][0], receipt["sides"][1]
    if case == "disjoint":
        head["clearing_subsets"] = [["contracts_entry"]]
        expected = expected_proof("not_proven", ())
    if case == "tied":
        base["clearing_subsets"] = head["clearing_subsets"] = [[CATEGORY], ["contracts_entry"]]
        expected = expected_proof("ambiguous", ())
    if case == "larger_common":
        base["clearing_subsets"] = [[CATEGORY], ["contracts_entry", CATEGORY]]
        head["clearing_subsets"] = [["contracts_entry"], ["contracts_entry", CATEGORY]]
        expected = expected_proof("native_compatibility_clear", ("contracts_entry", CATEGORY))
    if case == "unavailable_reference":
        head["signed_reference_matches"] = False
        head["clearing_subsets"] = []
        expected = expected_proof("unavailable", ())
    if case == "other_witness":
        for row in receipt["sides"]:
            row["witnesses"] = [
                {
                    "member": "contracts",
                    "predicate": "active_requirement_rejects_target",
                    "category": "other",
                    "native_reason": "private-dependency: target=0, required=>=1 by crosshair-tool",
                }
            ]
            row["native_conflicts"] = {
                "contracts": "project_analyzer_dependency_incompatible:" + row["witnesses"][0]["native_reason"]
            }
            row["conflict_digest"] = conflict_digest(row["native_conflicts"])
            report["analyzer_evidence"][0][row["binding"]["side"]]["diagnostic"] = row["native_conflicts"]["contracts"]
        expected = expected_proof("not_proven", ())
        for row in expected["records"]:
            row.update(predicate="active_requirement_rejects_target", category="other")
    if case in {"disjoint", "tied", "larger_common"}:
        include_entry_witness(receipt, report)
        expected["records"] = [
            {"side": side, "analyzer": "contracts", "predicate": PREDICATE, "category": category}
            for side in SIDES
            for category in ("contracts_entry", CATEGORY)
        ]
    projected = run_publisher(publisher_fixture(tmp_path, receipt, report))
    assert projected == legacy_summary() | {"compatibility_proof": expected}


def test_existing_projection_fields_are_preserved(tmp_path):
    receipt = synthetic_receipt()
    projected = run_publisher(publisher_fixture(tmp_path, receipt, synthetic_report(receipt)))
    projected.pop("compatibility_proof", None)
    assert projected == legacy_summary()


@pytest.mark.parametrize(
    "member,predicate,category,name",
    [
        (member, predicate, category, name)
        for member, roles in (
            ("contracts", (("contracts_entry", "crosshair-tool"), ("contracts_pinned_transitive", "z3-solver"))),
            ("pylint", (("pylint_entry", "pylint"), ("pylint_pinned_transitive", "astroid"))),
        )
        for predicate in (PREDICATE, "active_requirement_rejects_target")
        for category, name in (roles if predicate == PREDICATE else (*roles, ("other", "private-canary-package")))
    ],
)
def test_publisher_projects_finite_member_predicates(tmp_path, member, predicate, category, name):
    receipt = synthetic_receipt()
    suffix = "sealed entry=1.0" if predicate == PREDICATE else "required=>=1 by synthetic-entry"
    reason = f"{name}: target=0.0.0+private.compatibility.canary, {suffix}"
    for row in receipt["sides"]:
        row["witnesses"] = [{"member": member, "predicate": predicate, "category": category, "native_reason": reason}]
        row["native_conflicts"] = {member: "project_analyzer_dependency_incompatible:" + reason}
        row["conflict_digest"] = conflict_digest(row["native_conflicts"])
        row["signed_reference_matches"] = False
        row["clearing_subsets"] = []
    report = synthetic_report(receipt)
    report["analyzer_evidence"][0]["id"] = member
    for side in SIDES:
        report["analyzer_evidence"][0][side]["diagnostic"] = "project_analyzer_dependency_incompatible:" + reason
    expected = legacy_summary()
    expected.update(error_analyzers=[member], unknown_analyzers=[member], error_analyzer_sides={member: list(SIDES)})
    if member == "pylint":
        for field in ("snapshot_diagnostic_observations", "snapshot_diagnostic_facts", "snapshot_producer_categories"):
            del expected[field]
    expected["compatibility_proof"] = {
        "status": "observed",
        "records": [{"side": side, "analyzer": member, "predicate": predicate, "category": category} for side in SIDES],
        "reference_comparison": {"status": "unavailable", "substitution_categories": []},
    }
    assert run_publisher(publisher_fixture(tmp_path, receipt, report)) == expected


def include_entry_witness(receipt, report):
    reason = "crosshair-tool: target=0.0.0+private.compatibility.canary, sealed entry=0.0.109"
    conflict = "project_analyzer_dependency_incompatible:" + reason + "; " + NATIVE_REASON
    for row in receipt["sides"]:
        row["witnesses"].insert(
            0, {"member": "contracts", "predicate": PREDICATE, "category": "contracts_entry", "native_reason": reason}
        )
        row["native_conflicts"] = {"contracts": conflict}
        row["conflict_digest"] = conflict_digest(row["native_conflicts"])
        report["analyzer_evidence"][0][row["binding"]["side"]]["diagnostic"] = conflict


def test_standalone_publisher_preserves_complete_legacy_output(tmp_path):
    receipt = synthetic_receipt()
    trusted = publisher_fixture(tmp_path, receipt, synthetic_report(receipt))
    step = next(step for step in independent_review_job()["steps"] if "PY_REVIEW_FAILURE" in step.get("run", ""))
    program = step["run"].split("<<'PY_REVIEW_FAILURE'", 1)[1].split("\n", 1)[1].split("\nPY_REVIEW_FAILURE", 1)[0]
    environment = dict(
        os.environ, REVIEW_REPORT=str(trusted / "review.private.json"), REVIEW_LOG=str(trusted / "review.private.log")
    )
    environment.pop("TRUSTED_ROOT", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", program], env=environment, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == legacy_summary()
