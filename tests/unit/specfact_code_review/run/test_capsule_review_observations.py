"""Portable public observation proofs with unchanged identity and privacy assertions."""

from __future__ import annotations

import json
import os
import re
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.capsule_review_fixtures import (
    _DEPTH_FAILURE_FINDING_ROWS,
    _git,
    _write_public_report,
    independent_review_job,
    public_projector,
    write_public_phase_record_report,
)


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
def test_public_tool_errors_cannot_disappear_after_two_hundred_ordinary_findings(tmp_path: Path, job_name):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    rows = [{"file": "public.py", "line": n, "severity": "info"} for n in range(1, 220)]
    rows.append(
        {
            "file": "public.py",
            "line": 1,
            "severity": "error",
            "category": "tool_error",
            "tool": "pytest",
            "message": "PRIVATE_SECRET",
        }
    )
    report.write_text(json.dumps({"findings": rows}))
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    projected = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert result.returncode == 0, result.stderr
    assert len(projected) == 200
    assert projected[0]["category"] == "tool_error" and projected[0]["tool"] == "pytest"
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit,diagnostic", [("1", "review_report_missing"), ("124", "analysis_timeout")])
def test_missing_review_report_has_fixed_public_cause(tmp_path: Path, job_name, review_exit, diagnostic):
    environment = dict(os.environ, REVIEW_PUBLIC_EXIT=review_exit)
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "INCOMPLETE", "phase": "review", "diagnostic": diagnostic}


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "message,failure_class",
    [
        ("semgrep returned structured errors PRIVATE", "structured_errors"),
        ("semgrep process failed PRIVATE", "process_failure"),
        ("semgrep returned empty stdout PRIVATE", "empty_output"),
        ("Unrecognized CrossHair output PRIVATE", "unrecognized_output"),
    ],
)
def test_public_execution_classification_never_prints_raw_messages(tmp_path: Path, job_name, message, failure_class):
    _write_public_report(
        tmp_path,
        [{"file": "public.py", "line": 1, "severity": "error", "category": "tool_error", "message": message}],
    )
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert row["failure_class"] == failure_class
    assert "PRIVATE" not in result.stdout


def test_trusted_review_budget_timeout_retains_thirty_minutes_and_fixed_exit(monkeypatch, tmp_path):
    recipe = next(
        step["run"]
        for step in independent_review_job()["steps"]
        if step.get("name") == "Prepare and review through the authenticated installed controller"
    )
    command = re.findall(r"-I -c \\\n\s*'([^']+)'", recipe)[-1]
    wrapper = tmp_path / "trusted_review_budget.py"
    wrapper.write_text(command)
    observed = []

    def timeout(args, *, timeout, check):
        observed.append((args, timeout, check))
        raise subprocess.TimeoutExpired(args, timeout, stderr="PRIVATE_SECRET")

    monkeypatch.setattr(subprocess, "run", timeout)
    monkeypatch.setattr(sys, "argv", ["-c", "trusted-python", "trusted-reviewer.py"])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(wrapper), run_name="__main__")
    assert result.value.code == 124
    assert observed == [(["trusted-python", "trusted-reviewer.py"], 1800, False)]


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "details,expected",
    [
        (
            [{"type": "Syntax error", "message": "PRIVATE_SOURCE"}, {"type": "Timeout"}, {"type": "SECRET_TYPE"}],
            ["Syntax error", "Timeout"],
        ),
        (
            [{"type": ["PartialParsing", "PRIVATE_SPAN"]}, {"type": "Fatal error", "private": "PRIVATE_TOKEN"}],
            ["Fatal error", "PartialParsing"],
        ),
        (
            [{"type": "Syntax error"}, {"type": "Timeout"}, {"type": "Fatal error"}, {"type": "Out of memory"}],
            ["Fatal error", "Syntax error", "Timeout"],
        ),
    ],
)
def test_structured_semgrep_failure_projects_only_fixed_variant_tags(tmp_path: Path, job_name, details, expected):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "tool_error",
        "tool": "semgrep",
        "message": "semgrep returned structured errors; details=" + json.dumps(details),
    }
    report.write_text(json.dumps({"findings": [finding]}))
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)], cwd=tmp_path, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected["failure_class"] == "structured_errors"
    assert projected["semgrep_error_types"] == expected
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "details",
    [
        '{"type":"Syntax error"}',
        "not-json",
        '[{"type":"SECRET_TYPE"}]',
        '[{"type":"Syntax error"}]' + "PRIVATE" * 1000,
        "[" * 1500 + "]" * 1500,
    ],
)
def test_malformed_or_oversized_semgrep_details_keep_generic_public_cause(tmp_path: Path, job_name, details):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "tool_error",
        "tool": "semgrep",
        "message": "semgrep returned structured errors; details=" + details,
    }
    report.write_text(json.dumps({"findings": [finding]}))
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)], cwd=tmp_path, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected["failure_class"] == "structured_errors"
    assert "semgrep_error_types" not in projected
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
def test_semgrep_decoder_depth_failure_keeps_generic_public_cause(tmp_path: Path, job_name):
    _write_public_report(tmp_path, _DEPTH_FAILURE_FINDING_ROWS)
    fault = """import json
_original_loads = json.loads
def _depth_failure(value, *args, **kwargs):
    if value == "DECODER_DEPTH_FAILURE":
        raise RecursionError("PRIVATE_DECODER_TRACE")
    return _original_loads(value, *args, **kwargs)
json.loads = _depth_failure
"""
    result = subprocess.run(
        [sys.executable, "-c", fault + public_projector(job_name)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected["failure_class"] == "structured_errors"
    assert "semgrep_error_types" not in projected
    assert "PRIVATE" not in result.stdout and "PRIVATE" not in result.stderr


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "message,code",
    [
        ("project_pytest_coverage_worker_missing; PRIVATE", "project_pytest_coverage_worker_missing"),
        ("project_pytest_coverage_evidence_unavailable:PRIVATE", "project_pytest_coverage_evidence_unavailable"),
        ("project_pytest_execution_incomplete:exit=4 PRIVATE", "project_pytest_execution_incomplete"),
        ("project_pytest_root_outside_snapshot", "project_pytest_root_outside_snapshot"),
        ("project_pytest_root_missing_or_invalid; PRIVATE", "project_pytest_root_missing_or_invalid"),
        ("project_pytest_collection_error; PRIVATE", "project_pytest_collection_error"),
        ("project_pytest_coverage_diagnostic_invalid:PRIVATE", "project_pytest_coverage_diagnostic_invalid"),
        ("project_pytest_coverage_policy_invalid:PRIVATE", "project_pytest_coverage_policy_invalid"),
        ("project_pytest_coverage_candidate_invalid:PRIVATE", "project_pytest_coverage_candidate_invalid"),
        (
            "project_pytest_installed_coverage_directory_invalid:PRIVATE",
            "project_pytest_installed_coverage_directory_invalid",
        ),
        (
            "project_pytest_installed_coverage_module_invalid:PRIVATE",
            "project_pytest_installed_coverage_module_invalid",
        ),
        ("[Errno 2] PRIVATE_PATH", "file_missing"),
        ("[Errno 13] PRIVATE_PATH", "permission_denied"),
        ("PRIVATE project_pytest_execution_incomplete", None),
        ("project_pytest_execution_incomplete_PRIVATE", None),
        ("PRIVATE_UNKNOWN", None),
    ],
)
def test_public_pytest_failure_codes_withhold_private_payload(tmp_path: Path, job_name, message, code):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "file": "public.py",
                        "line": 1,
                        "severity": "error",
                        "category": "tool_error",
                        "tool": "pytest",
                        "message": message,
                    }
                ]
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected.get("diagnostic_code") == code
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize(
    "progress,analyzer",
    [
        ("PRIVATE\nChecking capsule analyzer contracts...\n", "contracts"),
        (
            "Checking capsule analyzer pylint...\nPRIVATE\nChecking capsule analyzer targeted-pytest-coverage...\n",
            "targeted-pytest-coverage",
        ),
        ("Checking capsule analyzer PRIVATE...\n", None),
        ("PRIVATE Checking capsule analyzer pylint...\n", None),
        ("Checking capsule analyzer pylint...\n" + "X" * 65537, None),
    ],
)
def test_independent_timeout_projects_only_bounded_exact_progress(tmp_path: Path, progress, analyzer):
    log = tmp_path / "progress.private.log"
    log.write_text(progress)
    environment = dict(os.environ, REVIEW_PUBLIC_EXIT="124", REVIEW_PUBLIC_PROGRESS=str(log))
    result = subprocess.run(
        [sys.executable, "-c", public_projector("independent-review")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)
    assert row["diagnostic"] == "analysis_timeout"
    assert row.get("analyzer") == analyzer
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("rule", ["TEST_OUTCOME_NOT_PASS", "TEST_COVERAGE_POLICY_FAILED"])
def test_public_testing_findings_survive_ordinary_location_cap(tmp_path: Path, job_name, rule):
    rows = [{"file": "public.py", "line": n, "severity": "info"} for n in range(1, 220)]
    rows.append(
        {
            "file": "public.py",
            "line": 1,
            "severity": "error",
            "category": "testing",
            "tool": "pytest",
            "rule": rule,
            "message": "PRIVATE_TRACE_WITH_PARAMETERS",
        }
    )
    _write_public_report(tmp_path, rows)
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    projected = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert result.returncode == 0, result.stderr
    assert len(projected) == 200
    assert projected[0].get("category") == "testing"
    assert projected[0].get("rule") == rule
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "outcome,phase,xfail", [("failed", "call", False), ("skipped", "setup", False), ("passed", "call", True)]
)
def test_public_test_observations_identify_only_tracked_source_functions(tmp_path, job_name, outcome, phase, xfail):
    suffix = " with an xfail marker." if xfail else "."
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "testing",
        "tool": "pytest",
        "rule": "TEST_OUTCOME_NOT_PASS",
        "message": (
            f"Test public.py::test_public_case[PRIVATE_PARAMETER::test_inner[PRIVATE_NESTED]] "
            f"{outcome} during {phase}{suffix}"
        ),
    }
    _write_public_report(tmp_path, [finding])
    (tmp_path / "public.py").write_text("def test_public_case():\n    pass\ndef test_inner():\n    pass\n")
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert row.get("test_outcome") == outcome
    assert row.get("test_phase") == phase
    assert row.get("test_xfail") is xfail
    assert row.get("test_function") == "test_public_case"
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "message",
    [
        "Test public.py::PRIVATE_FUNCTION[PRIVATE_PARAMETER] failed during call.",
        "Test /private/SECRET.py::test_public_case failed during call.",
        "Test public.py::test_public_case failed during PRIVATE_PHASE.",
        "Test public.py::test_public_case[" + "PRIVATE" * 1000 + "] failed during call.",
    ],
)
def test_public_test_observations_reject_private_or_malformed_identity(tmp_path, job_name, message):
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "testing",
        "tool": "pytest",
        "rule": "TEST_OUTCOME_NOT_PASS",
        "message": message,
    }
    _write_public_report(tmp_path, [finding])
    (tmp_path / "public.py").write_text("def test_public_case():\n    pass\n")
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert "test_function" not in row
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "failure_case",
    [
        ("E FileNotFoundError: [Errno 2] PRIVATE_PATH", "FileNotFoundError", None, None),
        ("E subprocess.CalledProcessError: PRIVATE_COMMAND", "CalledProcessError", None, None),
        (
            "E RuntimeError: project_python_option_unsupported:-I; PRIVATE_TRACE",
            "RuntimeError",
            "project_python_option_unsupported",
            "-I",
        ),
        ("E PRIVATE_EXCEPTION: PRIVATE_TRACE", None, None, None),
    ],
)
def test_public_test_failure_class_uses_matching_record_only(tmp_path, job_name, failure_case):
    detail, exception, diagnostic, option = failure_case
    write_public_phase_record_report(tmp_path, "public.py::test_public_case[PRIVATE_PARAMETER]", detail)
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert row.get("test_failure_class") == exception
    assert row.get("test_diagnostic") == diagnostic
    assert row.get("python_option") == option
    assert "PRIVATE" not in result.stdout and "PermissionError" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("snapshot", ["head", "base", "head_and_base"])
def test_public_test_failure_reads_immutable_snapshot_records(tmp_path, job_name, snapshot):
    nodeid = "public.py::test_public_case[PRIVATE_PARAMETER]"
    write_public_phase_record_report(tmp_path, nodeid, "E FileNotFoundError: PRIVATE_PATH")
    report = tmp_path / ".specfact/code-review.json"
    data = json.loads(report.read_text())
    evidence = data["analyzer_evidence"][0]
    execution = evidence.pop("target_execution")
    selected = "head" if snapshot == "head_and_base" else snapshot
    evidence[selected] = {"target_execution": execution}
    if snapshot == "head_and_base":
        evidence["base"] = {
            "target_execution": {
                "records": [
                    {
                        "nodeid": nodeid,
                        "phase": "call",
                        "outcome": "failed",
                        "detail": "E PermissionError: PRIVATE_BASE",
                    },
                ]
            }
        }
    report.write_text(json.dumps(data))
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert row.get("test_failure_class") == "FileNotFoundError"
    assert "PRIVATE" not in result.stdout and "PermissionError" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("case", ["invalid", "non_object", "oversized", "recursive", "unreadable"])
def test_public_projector_bounds_and_rejects_unreadable_reports(tmp_path: Path, job_name, case):
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    fault = ""
    if case == "oversized":
        with report.open("wb") as stream:
            stream.write(b'{"private":"PRIVATE_SECRET')
            for _ in range(512):
                stream.write(b"x" * 65536)
            stream.write(b'"}')
    elif case == "recursive":
        report.write_text("[" * 10000 + "0" + "]" * 10000)
    else:
        report.write_text("PRIVATE_SECRET invalid JSON" if case == "invalid" else '["PRIVATE_SECRET"]')
    if case == "unreadable":
        fault = (
            "from pathlib import Path\ndef denied_open(*args, **kwargs):\n"
            "    raise OSError('PRIVATE_SECRET')\nPath.open = denied_open\n"
        )
    result = subprocess.run(
        [sys.executable, "-c", fault + public_projector(job_name)],
        cwd=tmp_path,
        env=dict(os.environ, REVIEW_PUBLIC_EXIT="17"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Malformed diagnostic input must not crash projection"
    assert json.loads(result.stdout) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_report_unreadable",
    }
    assert "PRIVATE_SECRET" not in result.stdout
