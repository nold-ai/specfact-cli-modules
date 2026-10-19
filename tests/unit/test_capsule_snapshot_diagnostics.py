from __future__ import annotations

import json
import subprocess
import sys

import pytest
import yaml

from tests.support.capsule_review_fixtures import REPO_ROOT, STEP_NAME


_SNAPSHOT_FIELD = "snapshot_diagnostic_observations"
_SNAPSHOT_REASONS = (
    "analyzer_reported_incomplete_execution",
    "analyzer_output_invalid",
    "capsule_request_failed",
    "linux_bubblewrap_identity_missing",
    "namespace_unavailable",
    "sandbox_filesystem_error",
    "analyzer_process_error",
    "sandbox_launch_failed",
    "reserved_import_catalog_unavailable",
    "reserved_import_collision",
    "bubblewrap_identity_mismatch",
    "trace_helper_failed",
    "pre_namespace_observation_unsupported",
    "pre_namespace_observation_requires_single_thread",
    "pre_namespace_exec_stop_missing",
    "pre_namespace_observation_failed",
    "pre_namespace_executable_missing",
    "pre_namespace_executable_ambiguous",
    "pre_namespace_host_object",
    "unclassified",
)
_SNAPSHOT_CANARY = "PRIVATE_CANARY:/private/review.py --private-argument return private_source"


def _snapshot_report(**sides):
    return {
        "assurance_status": "UNKNOWN",
        "overall_verdict": "FAIL",
        "findings": [],
        "analyzer_evidence": [{"id": "contracts", "diagnostic": "snapshot_member_incomplete", **sides}],
    }


@pytest.fixture(name="snapshot_projector", params=("candidate", "independent"))
def snapshot_projector_fixture(request, tmp_path, monkeypatch):
    owner = request.param
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    job = workflow["jobs"]["customer" if owner == "candidate" else "independent-review"]
    name = STEP_NAME if owner == "candidate" else "Project independent review failure privately"
    marker = "PY_CANDIDATE_FAILURE" if owner == "candidate" else "PY_REVIEW_FAILURE"
    recipe = next(step["run"] for step in job["steps"] if step.get("name") == name)
    program = recipe.split("<<'" + marker + "'", 1)[1].split("\n", 1)[1].split("\n" + marker, 1)[0]
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    log = tmp_path / "review.private.log"
    log.write_text(_SNAPSHOT_CANARY)
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(log))

    def invoke(payload):
        report.write_text(payload)
        before = report.read_bytes()
        result = subprocess.run(
            [sys.executable, "-I", "-c", program], cwd=tmp_path, capture_output=True, text=True, check=False
        )
        assert result.returncode == 0 and result.stderr == ""
        for private in ("PRIVATE_CANARY", "/private/review.py", "--private-argument", "return private_source"):
            assert private not in result.stdout + result.stderr
        assert report.read_bytes() == before
        return [json.loads(line) for line in result.stdout.splitlines()]

    return owner, invoke


@pytest.mark.parametrize("large", (False, True))
@pytest.mark.parametrize("swapped", (False, True))
def test_snapshot_reasons_preserve_side_association_and_legacy_output(snapshot_projector, large, swapped):
    owner, invoke = snapshot_projector
    reasons = ["analyzer_process_error", "analyzer_output_invalid"]
    if swapped:
        reasons.reverse()
    root = _snapshot_report(
        **{
            side: {
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "diagnostic": reason + ":" + _SNAPSHOT_CANARY,
            }
            for side, reason in zip(("base", "head"), reasons, strict=True)
        }
    )
    root["private_inventory"] = "x" * (2 * 1024 * 1024 if large else 0)
    payload = json.dumps(root)
    size = len(payload.encode("utf-8"))
    assert (2 * 1024 * 1024 < size <= 32 * 1024 * 1024) if large else (size <= 2 * 1024 * 1024)
    rows = invoke(payload)
    observed = [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row]
    if owner == "candidate":
        legacy = [
            {"analyzer": "contracts", "incomplete_snapshot_sides": ["base", "head"]},
            {"analyzer": "contracts", "diagnostic_codes": ["snapshot_member_incomplete"]},
        ]
        if large:
            legacy.insert(0, {"analyzer": "contracts", "diagnostic_class": "candidate_report_unavailable"})
        assert [row for row in rows if _SNAPSHOT_FIELD not in row] == legacy
        assert all(set(row) == {_SNAPSHOT_FIELD} for row in rows if _SNAPSHOT_FIELD in row)
    else:
        expected = {
            "phase": "independent_review",
            "report_outcome": "oversized_report" if large else "structured_report",
            "assurance_status": "UNAVAILABLE" if large else "UNKNOWN",
            "overall_verdict": "UNAVAILABLE" if large else "FAIL",
            "findings_present": False,
            "tool_error_present": False,
            "execution_error_present": True,
            "unknown_evidence_present": True,
            "error_analyzers": ["contracts"],
            "unknown_analyzers": ["contracts"],
            "diagnostic_observations": ["unclassified"],
            "error_analyzer_sides": {"contracts": ["base", "head"]},
            "crosshair_failure_observations": [],
        }
        if large:
            expected["report_header_observed"] = True
        assert [{key: value for key, value in row.items() if key != _SNAPSHOT_FIELD} for row in rows] == [expected]
    assert observed == [
        [
            {"analyzer": "contracts", "side": side, "reason": reason}
            for side, reason in zip(("base", "head"), reasons, strict=True)
        ]
    ]


@pytest.mark.parametrize("reason", _SNAPSHOT_REASONS)
@pytest.mark.parametrize("state", ({"execution_state": "error"}, {"evidence_outcome": "UNKNOWN"}))
def test_snapshot_reason_vocabulary_uses_both_incompleteness_routes(snapshot_projector, reason, state):
    _, invoke = snapshot_projector
    root = _snapshot_report(base={**state, "diagnostic": reason + ":" + _SNAPSHOT_CANARY})
    rows = invoke(json.dumps(root))
    assert [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row] == [
        [{"analyzer": "contracts", "side": "base", "reason": reason}]
    ]


@pytest.mark.parametrize(
    "diagnostic,reason",
    [
        (None, "unclassified"),
        (False, "unclassified"),
        (42, "unclassified"),
        ({"private": _SNAPSHOT_CANARY}, "unclassified"),
        ([], "unclassified"),
        ("", "unclassified"),
        ("unknown:" + _SNAPSHOT_CANARY, "unclassified"),
        (" analyzer_process_error", "unclassified"),
        ("ANALYZER_PROCESS_ERROR", "unclassified"),
        ("private:analyzer_process_error", "unclassified"),
        ("ValueError:namespace_unavailable", "unclassified"),
        ("analyzer_process_error:analyzer_output_invalid", "analyzer_process_error"),
        *[
            (
                "analyzer_process_error:" + char * (length - len("analyzer_process_error:")),
                "analyzer_process_error" if length == 4096 else "unclassified",
            )
            for char in ("x", "\u00e9")
            for length in (4096, 4097)
        ],
    ],
    ids=lambda value: f"{len(value)}-codepoints-{value[-1]}" if isinstance(value, str) and len(value) > 100 else None,
)
def test_snapshot_reason_accepts_only_bounded_exact_leading_token(snapshot_projector, diagnostic, reason):
    owner, invoke = snapshot_projector
    root = _snapshot_report(head={"evidence_outcome": "UNKNOWN", "diagnostic": diagnostic})
    rows = invoke(json.dumps(root))
    if owner == "independent" and diagnostic == "ValueError:namespace_unavailable":
        assert rows[0]["diagnostic_observations"] == ["namespace_unavailable"]
    assert [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row] == [
        [{"analyzer": "contracts", "side": "head", "reason": reason}]
    ]


@pytest.mark.parametrize(
    "case",
    (
        "missing",
        "complete",
        "badside",
        "absent",
        "unrelated",
        "duplicate",
        "ten",
        "eleven",
        "overfull",
    ),
)
def test_snapshot_observation_requires_one_unambiguous_contracts_row(snapshot_projector, case):
    _, invoke = snapshot_projector
    root = _snapshot_report(base={"execution_state": "error", "diagnostic": "analyzer_process_error"})
    row = root["analyzer_evidence"][0]
    expected = []
    if case == "missing":
        del row["base"]["diagnostic"]
        expected = [{"analyzer": "contracts", "side": "base", "reason": "unclassified"}]
    elif case == "complete":
        row["base"] = {"execution_state": "ran", "evidence_outcome": "PASS", "diagnostic": "analyzer_process_error"}
    elif case == "badside":
        row.update(base=_SNAPSHOT_CANARY, head=[], other={"execution_state": "error"})
    elif case == "absent":
        del row["base"]
    elif case == "unrelated":
        row["id"] = "ruff"
    elif case == "duplicate":
        root["analyzer_evidence"].append(dict(row))
    else:
        root["analyzer_evidence"] = [{"id": "ruff"}] * 9 + [row]
        if case == "ten":
            expected = [{"analyzer": "contracts", "side": "base", "reason": "analyzer_process_error"}]
        else:
            root["analyzer_evidence"].append(dict(row) if case == "eleven" else {"id": "ruff"})
    rows = invoke(json.dumps(root))
    assert [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row] == ([expected] if expected else [])


@pytest.mark.parametrize(
    "case", ("root_key", "row_id", "side_key", "diagnostic_key", "truncated", "trailing", "oversized")
)
def test_snapshot_observation_never_salvages_invalid_private_report(snapshot_projector, case):
    _, invoke = snapshot_projector
    payload = json.dumps(_snapshot_report(base={"execution_state": "error", "diagnostic": "analyzer_process_error"}))
    replacements = {
        "root_key": ('"findings": []', '"findings": [], "findings": []'),
        "row_id": ('"id": "contracts"', '"id": "contracts", "id": "contracts"'),
        "side_key": ('"base": {', '"base": {}, "base": {'),
        "diagnostic_key": (
            '"diagnostic": "analyzer_process_error"',
            '"diagnostic": null, "diagnostic": "analyzer_process_error"',
        ),
    }
    if case in replacements:
        payload = payload.replace(*replacements[case])
    elif case == "truncated":
        payload = payload[:-1]
    elif case == "trailing":
        payload += _SNAPSHOT_CANARY
    else:
        payload = payload[:-1] + ', "private_inventory": "' + "x" * (32 * 1024 * 1024) + '"}'
    rows = invoke(payload)
    assert all(_SNAPSHOT_FIELD not in row for row in rows)
