import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/capsule-customer-execution.yml"
JOBS = ("customer", "independent-review")
SOURCE = "tests/test_customer.py"
PRIVATE = "PRIVATE_SECRET_/customer/dependency.py"
NATIVE_DETAILS = (
    "Set SPECFACT_HATCH_PROOF_WORKSPACE with native Hatch and Python 3.11 prerequisites for the acceptance cell",
    "Native Hatch and project Python are required for customer storage acceptance",
    "Native Hatch and project Python are required for absolute declaration acceptance",
)
CROSSHAIR_MARKERS = (
    ("CrossHair timed out before mandatory evidence completed.", "crosshair_timeout_observed"),
    ("CrossHair process error:", "crosshair_process_error_observed"),
    ("Unrecognized CrossHair output:", "crosshair_unrecognized_output_observed"),
    ("Unable to execute CrossHair:", "crosshair_execute_error_observed"),
)
EXCEPTIONS = (
    ("ModuleNotFoundError", "module_not_found_observed"),
    ("ImportError", "import_error_observed"),
    ("SyntaxError", "syntax_error_observed"),
    ("PermissionError", "permission_error_observed"),
    ("TypeError", "type_error_observed"),
    ("FileNotFoundError", "file_not_found_observed"),
    ("ValueError", "value_error_observed"),
    ("wrong parameter order", "wrong_parameter_order_observed"),
)


@pytest.fixture(autouse=True)
def record_selector(request, record_property):
    record_property("specfact.selector", request.node.nodeid)


def _recipe(job, projection):
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"][job]["steps"]
    if projection == "failure" and job == "independent-review":
        return next(step["run"] for step in steps if step.get("name") == "Project independent review failure privately")
    identifier = "deferred_review" if job == "customer" else "independent_review"
    return next(step["run"] for step in steps if step.get("id") == identifier)


def _program(job, projection):
    recipe = _recipe(job, projection)
    marker = "PY_CANDIDATE_FAILURE" if job == "customer" else "PY_REVIEW_FAILURE"
    if projection == "locations":
        invocation = next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)
        return recipe.split(invocation + "\n", 1)[1].split("\nPY", 1)[0]
    return recipe.split("<<'" + marker + "'", 1)[1].split("\n", 1)[1].split("\n" + marker, 1)[0]


@pytest.fixture
def project(tmp_path):
    source = tmp_path / SOURCE
    source.parent.mkdir()
    source.write_text("def test_customer():\n    assert True\n")
    for arguments in (("init", "-q"), ("add", SOURCE)):
        subprocess.run(["git", *arguments], cwd=tmp_path, capture_output=True, check=True)
    (tmp_path / ".specfact").mkdir()
    return tmp_path


def _run(project, job, projection, data, review_exit=17):
    report = project / ".specfact/code-review.json"
    payload = data if isinstance(data, str) else json.dumps(data)
    report.write_text(payload)
    environment = dict(
        os.environ,
        REVIEW_REPORT=str(report),
        REVIEW_PUBLIC_REPORT=str(report),
        REVIEW_LOG=str(project / "absent.log"),
        REVIEW_PUBLIC_EXIT=str(review_exit),
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", _program(job, projection)],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert PRIVATE not in result.stdout + result.stderr
    assert report.read_text() == payload
    return result


def _report(findings=(), rows=(), oversized=False):
    return {
        "findings": list(findings),
        "analyzer_evidence": list(rows),
        "assurance_status": "FAIL",
        "overall_verdict": "FAIL",
        "private_padding": PRIVATE + ("x" * (2 * 1024 * 1024) if oversized else ""),
    }


def _finding(**fields):
    return {
        "file": SOURCE,
        "line": 1,
        "severity": "warning",
        "tool": "pytest",
        "category": "tool_error",
        "rule": "tool_error",
        "message": PRIVATE,
        **fields,
    }


def _output(result):
    assert result.returncode == 0, result.stderr
    return [json.loads(line) for line in result.stdout.splitlines()]


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize("oversized", [False, True])
@pytest.mark.parametrize("side", ["base", "head", "unavailable"])
def test_failure_provenance_retains_actual_side(project, job, oversized, side):
    evidence = {"execution_state": "error", "evidence_outcome": "UNKNOWN", "diagnostic": PRIVATE}
    row = {"id": "contracts", **(evidence if side == "unavailable" else {side: evidence})}
    result = _output(_run(project, job, "failure", _report(rows=[row], oversized=oversized)))
    observed = (
        next(item["incomplete_snapshot_sides"] for item in result if "incomplete_snapshot_sides" in item)
        if job == "customer"
        else result[0].get("error_analyzer_sides", {}).get("contracts")
    )
    assert observed == [side]


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize("oversized", [False, True])
@pytest.mark.parametrize("marker,code", CROSSHAIR_MARKERS, ids=["timeout", "process", "unrecognized", "execute"])
def test_crosshair_classes_match_structured_and_oversized(project, job, oversized, marker, code):
    finding = _finding(tool="crosshair", message=marker + " " + PRIVATE)
    rows = _output(_run(project, job, "failure", _report([finding], oversized=oversized)))
    if job == "customer":
        observations = [
            row["diagnostic_class"] for row in rows if row.get("diagnostic_class") != "candidate_report_unavailable"
        ]
    else:
        observations = rows[0].get("crosshair_failure_observations")
    assert observations == [code]


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "exception,code",
    EXCEPTIONS,
    ids=["module", "import", "syntax", "permission", "type", "file", "value", "parameter-order"],
)
def test_crosshair_exception_observations_are_closed(project, job, exception, code):
    finding = _finding(tool="crosshair", message="CrossHair process error: " + exception + ": " + PRIVATE)
    rows = _output(_run(project, job, "failure", _report([finding])))
    if job == "customer":
        assert rows == [
            {
                "analyzer": "contracts",
                "diagnostic_class": "crosshair_process_error_observed",
                "exception_observations": [code],
            }
        ]
    else:
        assert rows[0].get("crosshair_failure_observations") == sorted(["crosshair_process_error_observed", code])


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "state,status,blocking",
    [
        ("fixed", "fixed", False),
        ("introduced", "open", True),
        ("unchanged", "open", True),
        ("unknown", "waived-by-reference", False),
    ],
)
def test_finding_lifecycle_preserves_authoritative_fields(project, job, state, status, blocking):
    finding = _finding(differential_state=state, status=status, blocking=blocking)
    rows = _output(_run(project, job, "locations", _report([finding])))
    location = rows[0]["finding_location"]
    assert {field: location.get(field) for field in ("differential_state", "status", "blocking")} == {
        "differential_state": state,
        "status": status,
        "blocking": blocking,
    }
    assert location["severity"] == "warning"


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_invalid_lifecycle_never_defaults_to_nonblocking(project, job, value):
    finding = _finding(differential_state=value, status=value, blocking=value)
    rows = _output(_run(project, job, "locations", _report([finding])))
    assert not {"differential_state", "status", "blocking"}.intersection(rows[0]["finding_location"])


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "message,code",
    [
        (PRIVATE, "unclassified"),
        ("project_pytest_collection_failed:" + PRIVATE, "project_pytest_collection_failed"),
        ("[Errno 2] " + PRIVATE, "file_missing"),
        ("[Errno 13] " + PRIVATE, "permission_denied"),
    ],
    ids=["unknown", "collection", "file-missing", "permission"],
)
def test_pytest_error_classification_does_not_infer_from_anchor(project, job, message, code):
    rows = _output(_run(project, job, "locations", _report([_finding(message=message)])))
    location = rows[0]["finding_location"]
    assert location.get("diagnostic_code") == code
    assert location["file"] == SOURCE


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "detail", [*NATIVE_DETAILS, PRIVATE, ""], ids=["workspace", "storage", "declaration", "unknown", "absent"]
)
@pytest.mark.parametrize("outcome", ["skipped", "failed"])
def test_native_prerequisite_classification_uses_only_recorded_skips(project, job, detail, outcome):
    nodeid = SOURCE + "::test_customer"
    record = {"nodeid": nodeid, "outcome": outcome, "phase": "call", "detail": detail}
    row = {"id": "targeted-pytest-coverage", "head": {"target_execution": {"records": [record]}}}
    finding = _finding(
        category="testing", rule="TEST_OUTCOME_NOT_PASS", message=f"Test {nodeid} {outcome} during call."
    )
    rows = _output(_run(project, job, "locations", _report([finding], [row])))
    location = rows[0]["finding_location"]
    expected = "native_prerequisites_not_supplied" if detail in NATIVE_DETAILS and outcome == "skipped" else None
    assert location.get("test_diagnostic") == expected


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "payload",
    ["{" + PRIVATE, '{"findings":[],"findings":[],"analyzer_evidence":[]}', "[]", "x" * (32 * 1024 * 1024 + 1)],
    ids=["invalid-json", "duplicate-key", "invalid-shape", "over-bound"],
)
def test_failure_projection_rejects_invalid_private_reports(project, job, payload):
    rows = _output(_run(project, job, "failure", payload))
    assert all(not row.get("error_analyzers") and not row.get("incomplete_snapshot_sides") for row in rows)
    assert all(row.get("overall_verdict") != "PASS" for row in rows)


@pytest.mark.parametrize("job", JOBS)
def test_public_location_bounds_and_private_fields_remain_closed(project, job):
    findings = [_finding(file="/" + PRIVATE), _finding(file="../" + PRIVATE), _finding(line=True)]
    findings += [
        _finding(line=index + 1, differential_state="fixed", status="fixed", blocking=False) for index in range(205)
    ]
    rows = _output(_run(project, job, "locations", _report(findings)))
    locations = [row["finding_location"] for row in rows]
    assert len(locations) == 200
    assert [location["line"] for location in locations] == list(range(1, 201))
    assert all(
        set(location)
        == {
            "file",
            "line",
            "severity",
            "category",
            "tool",
            "rule",
            "differential_state",
            "status",
            "blocking",
            "diagnostic_code",
        }
        for location in locations
    )


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize("review_exit", [17, 124])
def test_diagnostics_preserve_failed_review_capture_and_identity(project, job, review_exit):
    recipe = _recipe(job, "locations")
    assert recipe.rstrip().endswith('exit "$review_exit"')
    assert "review_exit=$?" in recipe
    assert 'REVIEW_PUBLIC_EXIT="$review_exit"' in recipe
    data = _report([_finding(differential_state="fixed", status="fixed", blocking=False)])
    data.update(subject_commit=PRIVATE, reviewer_identity=PRIVATE)
    rows = _output(_run(project, job, "locations", data, review_exit))
    assert all(row.get("status") != "PASS" and row.get("overall_verdict") != "PASS" for row in rows)
    if review_exit == 124:
        assert rows[0]["diagnostic"] == "analysis_timeout"


@pytest.mark.parametrize("job", JOBS)
def test_failure_iteration_limits_do_not_reveal_late_private_evidence(project, job):
    rows = [{"id": "ruff"}] * 10 + [{"id": "contracts", "base": {"execution_state": "error"}}]
    findings = [{}] * 10_000 + [_finding(tool="crosshair", message="CrossHair process error: " + PRIVATE)]
    output = _output(_run(project, job, "failure", _report(findings, rows)))
    if job == "customer":
        assert output == []
    else:
        assert output[0].get("error_analyzer_sides", {}) == {}
        assert output[0].get("crosshair_failure_observations", []) == []


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "detail", ["E   ModuleNotFoundError: " + PRIVATE, "E   PrivateException: " + PRIVATE], ids=["known", "unknown"]
)
def test_recorded_pytest_exceptions_remain_allowlisted(project, job, detail):
    nodeid = SOURCE + "::test_customer"
    record = {"nodeid": nodeid, "outcome": "failed", "phase": "call", "detail": detail}
    evidence = {"id": "targeted-pytest-coverage", "head": {"target_execution": {"records": [record]}}}
    finding = _finding(category="testing", rule="TEST_OUTCOME_NOT_PASS", message=f"Test {nodeid} failed during call.")
    rows = _output(_run(project, job, "locations", _report([finding], [evidence])))
    expected = "ModuleNotFoundError" if detail.startswith("E   ModuleNotFoundError:") else None
    assert rows[0]["finding_location"].get("test_failure_class") == expected


@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(
    "message,failure_class,diagnostic_code",
    [
        ("Unable to execute targeted tests: [Errno 2] " + PRIVATE, "pytest_execute_error", "file_missing"),
        ("Unable to execute targeted tests: [Errno 13] " + PRIVATE, "pytest_execute_error", "permission_denied"),
        ("Unable to execute targeted tests: " + PRIVATE, "pytest_execute_error", "unclassified"),
        (
            "Unable to read targeted pytest evidence: project_pytest_collection_failed:" + PRIVATE,
            "pytest_evidence_read_error",
            "project_pytest_collection_failed",
        ),
        ("Unable to read targeted pytest evidence: " + PRIVATE, "pytest_evidence_read_error", "unclassified"),
        (
            "Targeted pytest observer, JUnit, and process outcomes could not be reconciled.",
            "pytest_outcome_reconciliation_failed",
            "unclassified",
        ),
        ("private wrapper: Unable to execute targeted tests: [Errno 2] " + PRIVATE, None, "unclassified"),
    ],
    ids=[
        "execute-file",
        "execute-permission",
        "execute-unknown",
        "read-collection",
        "read-unknown",
        "reconciliation",
        "arbitrary-wrapper",
    ],
)
def test_pytest_producer_failures_retain_fixed_cause_without_private_text(
    project, job, message, failure_class, diagnostic_code
):
    rows = _output(_run(project, job, "locations", _report([_finding(message=message)])))
    location = rows[0]["finding_location"]
    assert location.get("failure_class") == failure_class
    assert location.get("diagnostic_code") == diagnostic_code
