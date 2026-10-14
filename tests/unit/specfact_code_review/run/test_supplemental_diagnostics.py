"""Supplemental evidence never leaks tool text or upgrades review authority."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from specfact_code_review.run import supplemental_diagnostics as diagnostic
from specfact_code_review.run.findings import ReviewFinding, ReviewReport


def _finding(**updates):
    values = {
        "category": "security",
        "severity": "error",
        "tool": "semgrep",
        "rule": "specfact-bugs-eval-exec",
        "file": "sample.py",
        "line": 2,
        "message": "PRIVATE_SENTINEL",
        "differential_state": "introduced",
    }
    return ReviewFinding(**{**values, **updates})


def _inputs(findings=None):
    findings = [_finding()] if findings is None else findings
    source = b"def evaluate(value):\n    return eval(value)\n"
    entry = SimpleNamespace(
        git_mode="100644",
        object_type="blob",
        object_id=hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest(),
    )
    snapshots = [
        SimpleNamespace(tree=tree, contents={"sample.py": source}, entries={"sample.py": entry})
        for tree in diagnostic.EXPECTED_TREES
    ]
    resolution = SimpleNamespace(base_snapshot=snapshots[0], head_snapshot=snapshots[1])
    results = [
        SimpleNamespace(findings_by_member={"semgrep-bugs": []}),
        SimpleNamespace(findings_by_member={"semgrep-bugs": findings}),
    ]
    report = ReviewReport(
        run_id="PRIVATE_SENTINEL",
        score=0,
        summary="PRIVATE_SENTINEL",
        findings=findings,
        ci_exit_code=1,
        assurance_status="UNKNOWN",
        has_unknown_required_evidence=True,
        analyzer_evidence=[
            {
                "id": "semgrep-bugs",
                "evidence_outcome": "FAIL",
                "diagnostic": "PRIVATE_SENTINEL",
                "base": {"evidence_outcome": "PASS"},
                "head": {"evidence_outcome": "FAIL"},
            }
        ],
    )
    return report, resolution, results


def test_source_checked_rule_and_location_without_private_text():
    payload = diagnostic.build_sidecar(*_inputs())
    assert "PRIVATE_SENTINEL" not in json.dumps(payload)
    record = payload["findings"][0]
    assert (record["side"], record["rule"], record["function"], record["line"]) == (
        "head",
        "specfact-bugs-eval-exec",
        "evaluate",
        2,
    )
    assert len(record["source_sha256"]) == 64
    assert payload["purpose"] == "SUPPLEMENTARY_DIAGNOSTIC_ONLY"
    assert payload["original_exit_code"] == 1
    assert payload["effective_deadline"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    "updates", [{"file": "../private.py"}, {"file": "/private.py"}, {"line": 99}, {"rule": "PRIVATE_SENTINEL"}]
)
def test_invalid_location_or_catalog_rule_is_unavailable(updates):
    payload = diagnostic.build_sidecar(*_inputs([_finding(**updates)]))
    assert not payload["findings"]
    assert payload["omitted_findings"] == 1
    assert "PRIVATE_SENTINEL" not in json.dumps(payload)


def test_wrong_tree_and_symlink_never_emit_locations():
    inputs = _inputs()
    inputs[1].head_snapshot.tree = "0" * 40
    assert diagnostic.build_sidecar(*inputs)["status"] == "UNAVAILABLE"
    inputs = _inputs()
    inputs[1].head_snapshot.entries["sample.py"].git_mode = "120000"
    assert not diagnostic.build_sidecar(*inputs)["findings"]


def test_colliding_error_anchors_keep_actual_side():
    finding = _finding(
        category="tool_error",
        tool="crosshair",
        rule="CROSSHAIR_INCOMPLETE_EVIDENCE",
        differential_state="unknown",
        message="Unrecognized CrossHair output: PRIVATE_SENTINEL",
    )
    report, resolution, results = _inputs([])
    results[0].findings_by_member = {"contracts": [finding]}
    results[1].findings_by_member = {"contracts": [finding]}
    payload = diagnostic.build_sidecar(report, resolution, results)
    assert [item["side"] for item in payload["findings"]] == ["base", "head"]
    assert all(item["diagnostic"] == "crosshair_unrecognized_output" for item in payload["findings"])
    assert "PRIVATE_SENTINEL" not in json.dumps(payload)


def test_bounds_and_duplicates_account_for_omissions():
    inputs = _inputs([_finding()] * (diagnostic.MAX_RECORDS + 5))
    payload = diagnostic.build_sidecar(*inputs)
    assert len(payload["findings"]) == 1
    assert payload["omitted_findings"] == diagnostic.MAX_RECORDS + 4
    assert not payload["complete"]
    assert len(json.dumps(payload).encode()) <= diagnostic.MAX_BYTES


def test_disabled_and_failed_emission_leave_report_unchanged(tmp_path, monkeypatch):
    inputs = _inputs()
    before = inputs[0].model_dump()
    monkeypatch.delenv(diagnostic.OUTPUT_ENV, raising=False)
    assert diagnostic.emit_sidecar(*inputs) == "DISABLED"
    monkeypatch.setenv(diagnostic.OUTPUT_ENV, str(tmp_path / "missing" / "diagnostic.json"))
    assert diagnostic.emit_sidecar(*inputs) == "UNAVAILABLE"
    assert inputs[0].model_dump() == before


def test_emission_refuses_existing_file_and_symlink(tmp_path, monkeypatch):
    output = tmp_path / "diagnostic.json"
    output.write_text("keep")
    monkeypatch.setenv(diagnostic.OUTPUT_ENV, str(output))
    assert diagnostic.emit_sidecar(*_inputs()) == "UNAVAILABLE"
    assert output.read_text() == "keep"
    output.unlink()
    output.symlink_to(tmp_path / "elsewhere")
    assert diagnostic.emit_sidecar(*_inputs()) == "UNAVAILABLE"
    assert not (tmp_path / "elsewhere").exists()


def test_source_bytes_must_match_the_immutable_git_blob():
    inputs = _inputs()
    inputs[1].head_snapshot.contents["sample.py"] = b"def forged():\n    return 0\n"
    payload = diagnostic.build_sidecar(*inputs)
    assert payload["findings"] == []
    assert payload["omitted_findings"] == 1


def test_empty_or_partial_member_inventory_is_not_complete():
    report, resolution, results = _inputs([])
    report.analyzer_evidence = []
    payload = diagnostic.build_sidecar(report, resolution, results)
    assert payload["complete"] is False


def test_unknown_tool_cannot_borrow_an_error_rule():
    finding = _finding(tool="PRIVATE_SENTINEL", rule="tool_error", category="tool_error")
    payload = diagnostic.build_sidecar(*_inputs([finding]))
    assert payload["findings"] == []


def test_completeness_requires_all_member_outcomes_and_function_labels():
    report, resolution, results = _inputs([])
    report.analyzer_evidence = [
        {
            "id": member,
            "diagnostic": "snapshot_member_incomplete",
            "evidence_outcome": "UNKNOWN",
            "base": {"diagnostic": "snapshot_member_incomplete"},
            "head": {"diagnostic": "snapshot_member_incomplete"},
        }
        for member in diagnostic.MEMBERS
    ]
    assert diagnostic.build_sidecar(report, resolution, results)["complete"] is False


def test_introduced_identity_does_not_select_old_message_at_same_location():
    new = _finding(message="new observation")
    old = _finding(message="old observation", differential_state=None)
    report, _resolution, results = _inputs([new])
    results[1].findings_by_member["semgrep-bugs"] = [old, new]
    selected = diagnostic._selected_findings(report, results)
    assert len(selected) == 1
    assert selected[0][2].message == "new observation"


@pytest.mark.parametrize(
    "member,tool,rule",
    [
        ("semgrep-bugs", "pytest", "specfact-bugs-eval-exec"),
        ("contracts", "pylint", "CROSSHAIR_INCOMPLETE_EVIDENCE"),
        ("pylint", "pylint", "TEST_OUTCOME_NOT_PASS"),
    ],
)
def test_known_tokens_cannot_form_a_false_analyzer_identity(member, tool, rule):
    finding = _finding(tool=tool, rule=rule, category="tool_error")
    report, resolution, results = _inputs([finding])
    results[1].findings_by_member = {member: [finding]}
    assert diagnostic.build_sidecar(report, resolution, results)["findings"] == []


def test_emission_preserves_failed_report_and_private_file_permissions(tmp_path, monkeypatch):
    inputs = _inputs()
    before = inputs[0].model_dump()
    output = tmp_path / "diagnostic.json"
    monkeypatch.setenv(diagnostic.OUTPUT_ENV, str(output))
    assert diagnostic.emit_sidecar(*inputs) == "WRITTEN"
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.stat().st_size <= diagnostic.MAX_BYTES
    assert json.loads(output.read_text())["original_exit_code"] == 1
    assert inputs[0].model_dump() == before
