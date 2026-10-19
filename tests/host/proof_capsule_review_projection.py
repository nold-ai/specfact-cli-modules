from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.support.capsule_review_fixtures import (
    REPO_ROOT,
    STEP_NAME,
    public_projector,
    write_preparation_fixture,
)


def _public_projector_invocation(job_name):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    return next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)


def _write_preparation_interpreter(tmp_path):

    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        "#!" + sys.executable + "\n"
        "import os,sys\nfrom pathlib import Path\n"
        "if sys.argv[1:3] == ['-I','-c']:\n"
        "    if os.environ['REPORT_CASE'] == 'missing':\n"
        "        Path('commit-review-preparation.private.json').unlink()\n"
        "    else: print(Path('controlled-report.json').read_text())\n"
        "    raise SystemExit(int(os.environ['PREPARATION_EXIT']))\n"
        "os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n"
    )
    interpreter.chmod(0o700)


@pytest.fixture(name="preparation_shell")
def preparation_shell_fixture(tmp_path, monkeypatch):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = "# Provisioning" + step["run"].split("# Provisioning", 1)[1].split("review_exit=0", 1)[0]
    _write_preparation_interpreter(tmp_path)

    def invoke(preparation):
        preparation_exit, report_case = preparation
        report = write_preparation_fixture(tmp_path, "prepared" if report_case == "missing" else report_case)
        (tmp_path / "controlled-report.json").write_text(report.read_text())
        for name, value in {
            "CUSTOMER_ROOT": str(tmp_path),
            "GITHUB_WORKSPACE": str(tmp_path),
            "PROJECT_CONFIG": str(tmp_path / "project.toml"),
            "PREPARATION_EXIT": str(preparation_exit),
            "REPORT_CASE": report_case,
        }.items():
            monkeypatch.setenv(name, value)
        return subprocess.run(
            ["bash", "-c", "set -euo pipefail\n" + recipe + "printf 'REVIEW_STARTED\\n'"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    return invoke


@pytest.mark.parametrize(
    "preparation,expected",
    [
        ((0, "prepared"), (0, "PREPARED", "prepared")),
        ((0, "not_applicable"), (0, "NOT_APPLICABLE", "not_applicable")),
        ((7, "not_applicable"), (7, "INCOMPLETE", "preparation_command_failed")),
        ((0, "not_applicable_reason"), (1, "INCOMPLETE", "invalid_not_applicable")),
        ((7, "prepared"), (7, "INCOMPLETE", "preparation_command_failed")),
        ((0, "invalid"), (1, "INCOMPLETE", "invalid_json")),
        ((7, "invalid"), (7, "INCOMPLETE", "invalid_json")),
        ((0, "missing"), (1, "INCOMPLETE", "unreadable_report")),
        ((7, "missing"), (7, "INCOMPLETE", "unreadable_report")),
    ],
)
def test_preparation_shell_preserves_failure_and_projects_incomplete(preparation_shell, preparation, expected):

    expected_exit, expected_status, expected_outcome = expected
    accepted = expected_status in {"PREPARED", "NOT_APPLICABLE"}
    result = preparation_shell(preparation)
    assert result.returncode == expected_exit
    lines = result.stdout.splitlines()
    assert lines, "every preparation exit must produce bounded diagnosis"
    projection = json.loads(lines[0])
    assert projection["status"] == expected_status
    assert ("REVIEW_STARTED" in lines) is accepted
    assert "private" not in result.stdout + result.stderr
    assert projection["report_outcome"] == expected_outcome


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_projector_crash_preserves_original_review_exit(tmp_path: Path, job_name, review_exit):

    invocation = _public_projector_invocation(job_name)
    guard = invocation.split("<<'PY'", 1)[1]
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text('{"analyzer_evidence":42}')
    program = public_projector(job_name)
    shell = (
        f"set -e\nreview_exit={review_exit}\n"
        f"REVIEW_PUBLIC_EXIT=$review_exit {shlex.quote(sys.executable)} - <<'PY'{guard}\n"
        + program
        + '\nPY\nexit "$review_exit"\n'
    )
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == review_exit, "Diagnostics must preserve the original failed review result"
    assert result.stderr == "", "Projector tracebacks must remain private"
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_projection_failed",
    }
    assert "TypeError" in (tmp_path / "review-projection.private.log").read_text()


@pytest.mark.parametrize("review_exit", [17, 124])
def test_candidate_secondary_projector_crash_preserves_review_exit(tmp_path: Path, review_exit):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(step["run"] for step in workflow["jobs"]["customer"]["steps"] if step.get("name") == STEP_NAME)
    marker = "<<'PY_CANDIDATE_FAILURE'"
    invocation = next(line for line in recipe.splitlines() if marker in line)
    guard = invocation.split(marker, 1)[1]
    program = recipe.split(marker, 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    shell = (
        f"set -e\nreview_exit={review_exit}\n{shlex.quote(sys.executable)} - {marker}{guard}\n"
        + "raise SystemExit(3)\n"
        + program
        + '\nPY_CANDIDATE_FAILURE\nexit "$review_exit"\n'
    )
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == review_exit, "Every diagnostic invocation must preserve the failed review result"
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_projection_failed",
    }


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("module_name", ["ast", "json"])
@pytest.mark.parametrize("import_origin", ["checkout", "pythonpath"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_actual_projector_launch_excludes_untrusted_imports(
    tmp_path: Path, job_name, module_name, import_origin, review_exit
):
    invocation = _public_projector_invocation(job_name)
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    ambient = tmp_path / "ambient"
    ambient.mkdir()
    marker = tmp_path / "untrusted-import-executed"
    poison = candidate if import_origin == "checkout" else ambient
    (poison / f"{module_name}.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        "raise RuntimeError('UNTRUSTED_IMPORT')\n"
    )
    report = candidate / ".specfact/code-review.json" if job_name == "customer" else tmp_path / "review.private.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text("PRIVATE_REPORT invalid JSON")
    shell = f"set -e\ntrusted_env=(env)\nreview_exit={review_exit}\n" + invocation + "\n" + public_projector(job_name)
    shell += '\nPY\nexit "$review_exit"\n'
    environment = dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path), PYTHONPATH=str(ambient))
    environment["REVIEW_PUBLIC_REPORT"] = str(report)
    result = subprocess.run(
        ["bash", "-c", shell], cwd=candidate, env=environment, capture_output=True, text=True, check=False
    )
    assert not marker.exists(), "Candidate or ambient standard-library lookalikes executed on the host"
    assert result.returncode == review_exit and result.stderr == ""
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[-1] == {"status": "INCOMPLETE", "phase": "review", "diagnostic": "review_report_unreadable"}
    assert (review_exit != 124) or rows[0]["diagnostic"] == "analysis_timeout"
    assert "PRIVATE_REPORT" not in result.stdout and "UNTRUSTED_IMPORT" not in result.stdout
    assert report.read_text() == "PRIVATE_REPORT invalid JSON"


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


def _assert_candidate_snapshot_legacy_output(rows, large):
    legacy = [
        {"analyzer": "contracts", "incomplete_snapshot_sides": ["base", "head"]},
        {"analyzer": "contracts", "diagnostic_codes": ["snapshot_member_incomplete"]},
    ]
    if large:
        legacy.insert(0, {"analyzer": "contracts", "diagnostic_class": "candidate_report_unavailable"})
    assert [row for row in rows if _SNAPSHOT_FIELD not in row] == legacy
    assert all(set(row) == {_SNAPSHOT_FIELD} for row in rows if _SNAPSHOT_FIELD in row)


def _assert_independent_snapshot_legacy_output(rows, large):
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
        _assert_candidate_snapshot_legacy_output(rows, large)
    else:
        _assert_independent_snapshot_legacy_output(rows, large)
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


_SNAPSHOT_ERROR_ROW = {
    "id": "contracts",
    "diagnostic": "snapshot_member_incomplete",
    "base": {"execution_state": "error", "diagnostic": "analyzer_process_error"},
}


@pytest.mark.parametrize(
    "evidence,expected",
    [
        pytest.param(
            [{"id": "contracts", "diagnostic": "snapshot_member_incomplete", "base": {"execution_state": "error"}}],
            [{"analyzer": "contracts", "side": "base", "reason": "unclassified"}],
            id="missing",
        ),
        pytest.param(
            [
                {
                    "id": "contracts",
                    "diagnostic": "snapshot_member_incomplete",
                    "base": {
                        "execution_state": "ran",
                        "evidence_outcome": "PASS",
                        "diagnostic": "analyzer_process_error",
                    },
                }
            ],
            [],
            id="complete",
        ),
        pytest.param(
            [
                {
                    "id": "contracts",
                    "diagnostic": "snapshot_member_incomplete",
                    "base": _SNAPSHOT_CANARY,
                    "head": [],
                    "other": {"execution_state": "error"},
                }
            ],
            [],
            id="badside",
        ),
        pytest.param([{"id": "contracts", "diagnostic": "snapshot_member_incomplete"}], [], id="absent"),
        pytest.param([{**_SNAPSHOT_ERROR_ROW, "id": "ruff"}], [], id="unrelated"),
        pytest.param([_SNAPSHOT_ERROR_ROW, _SNAPSHOT_ERROR_ROW], [], id="duplicate"),
        pytest.param(
            [{"id": "ruff"}] * 9 + [_SNAPSHOT_ERROR_ROW],
            [{"analyzer": "contracts", "side": "base", "reason": "analyzer_process_error"}],
            id="ten",
        ),
        pytest.param([{"id": "ruff"}] * 9 + [_SNAPSHOT_ERROR_ROW, _SNAPSHOT_ERROR_ROW], [], id="eleven"),
        pytest.param([{"id": "ruff"}] * 9 + [_SNAPSHOT_ERROR_ROW, {"id": "ruff"}], [], id="overfull"),
    ],
)
def test_snapshot_observation_requires_one_unambiguous_contracts_row(snapshot_projector, evidence, expected):
    _, invoke = snapshot_projector
    root = _snapshot_report()
    root["analyzer_evidence"] = evidence
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
