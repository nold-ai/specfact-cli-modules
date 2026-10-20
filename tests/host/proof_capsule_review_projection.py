from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.host.capsule_source_fixtures import (
    SOURCE_CANARY,
    SOURCE_INVOCATIONS,
    run_complete_source_bootstrap,
    run_independent_source_command,
    run_source_publication,
    source_observed,
    source_publisher_environment,
    source_unavailable,
    synthetic_installed_source_reviewer,
    write_source_receipt_case,
)
from tests.support import capsule_producer_cases as producer_cases
from tests.support.capsule_review_fixtures import (
    REPO_ROOT,
    STEP_NAME,
    assert_incomplete_preparation,
    assert_installed_review_arguments,
    create_isolated_reviewer,
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
    assert all(_SNAPSHOT_FACTS_FIELD not in row for row in rows)


_SNAPSHOT_FACTS_FIELD = "snapshot_diagnostic_facts"
_SNAPSHOT_FACT_CASES = [
    pytest.param(({}, ("missing", "not_string", False), "unclassified"), id="missing"),
    *[
        pytest.param(({"diagnostic": value}, ("non_string", "not_string", False), "unclassified"), id=name)
        for name, value in (
            ("null", None),
            ("false", False),
            ("number", 42),
            ("list", []),
            ("object", {"private": _SNAPSHOT_CANARY}),
        )
    ],
    pytest.param(({"diagnostic": ""}, ("string", "empty", False), "unclassified"), id="empty"),
    *[
        pytest.param(({"diagnostic": value}, ("string", "within_bound", recognized), "unclassified"), id=name)
        for name, value, recognized in (
            ("unknown", "unknown:" + _SNAPSHOT_CANARY, False),
            ("literal-unclassified", "unclassified", True),
            ("unclassified-suffix", "unclassified:" + _SNAPSHOT_CANARY, True),
            ("embedded", "private:analyzer_process_error", False),
            ("leading-space", " analyzer_process_error", False),
            ("case-changed", "ANALYZER_PROCESS_ERROR", False),
            ("longest-prefix-extended", "pre_namespace_observation_requires_single_threadx:" + _SNAPSHOT_CANARY, False),
            ("longest-prefix-no-colon", "pre_namespace_observation_requires_single_threadx", False),
        )
    ],
]
for _character in ("x", "é"):
    for _length in (4096, 4097):
        for _prefix in ("unknown", "unclassified", "analyzer_process_error"):
            _diagnostic = _prefix + ":" + _character * (_length - len(_prefix) - 1)
            assert len(_diagnostic) == _length
            _classified = _prefix == "analyzer_process_error" and _length == 4096
            _expected = (
                None
                if _classified
                else ("string", "within_bound" if _length == 4096 else "over_bound", _prefix != "unknown")
            )
            _SNAPSHOT_FACT_CASES.append(
                pytest.param(
                    ({"diagnostic": _diagnostic}, _expected, _prefix if _classified else "unclassified"),
                    id=f"{_prefix}-{_length}-{ord(_character)}",
                )
            )


def _assert_snapshot_fact_rows(owner, rows, expected):
    if expected is None:
        assert all(_SNAPSHOT_FACTS_FIELD not in row for row in rows)
        return
    if owner == "candidate":
        envelopes = [row for row in rows if _SNAPSHOT_FACTS_FIELD in row]
        assert envelopes == [{_SNAPSHOT_FACTS_FIELD: expected}], "Missing or invalid finite fallback envelope"
        actual = envelopes[0][_SNAPSHOT_FACTS_FIELD]
    else:
        assert len(rows) == 1
        assert _SNAPSHOT_FACTS_FIELD in rows[0], "Missing finite fallback field"
        assert rows[0][_SNAPSHOT_FACTS_FIELD] == expected
        actual = rows[0][_SNAPSHOT_FACTS_FIELD]
    assert all(isinstance(fact["recognized_leading_token"], bool) for fact in actual)


@pytest.mark.parametrize("diagnostic_case", _SNAPSHOT_FACT_CASES)
@pytest.mark.parametrize("side", ("base", "head"))
@pytest.mark.parametrize("state", ({"execution_state": "error"}, {"evidence_outcome": "UNKNOWN"}))
def test_snapshot_fallback_facts_retain_only_closed_observations(snapshot_projector, diagnostic_case, side, state):
    owner, invoke = snapshot_projector
    fields, facts, reason = diagnostic_case
    rows = invoke(json.dumps(_snapshot_report(**{side: {**state, **fields}})))
    expected = None
    if facts is not None:
        shape, bucket, recognized = facts
        expected = [
            {
                "analyzer": "contracts",
                "side": side,
                "shape": shape,
                "length_bucket": bucket,
                "recognized_leading_token": recognized,
            }
        ]
    _assert_snapshot_fact_rows(owner, rows, expected)
    assert [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row] == [
        [{"analyzer": "contracts", "side": side, "reason": reason}]
    ]


@pytest.mark.parametrize("reason", _SNAPSHOT_REASONS)
def test_snapshot_fallback_facts_recognize_every_bounded_vocabulary_token(snapshot_projector, reason):
    owner, invoke = snapshot_projector
    diagnostic = reason + ":" + "x" * (4097 - len(reason) - 1)
    assert len(diagnostic) == 4097
    rows = invoke(json.dumps(_snapshot_report(base={"execution_state": "error", "diagnostic": diagnostic})))
    _assert_snapshot_fact_rows(
        owner,
        rows,
        [
            {
                "analyzer": "contracts",
                "side": "base",
                "shape": "string",
                "length_bucket": "over_bound",
                "recognized_leading_token": True,
            }
        ],
    )
    assert [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row] == [
        [{"analyzer": "contracts", "side": "base", "reason": "unclassified"}]
    ]


@pytest.mark.parametrize("large", (False, True))
@pytest.mark.parametrize("swapped", (False, True))
def test_snapshot_fallback_facts_preserve_order_and_report_acceptance(snapshot_projector, large, swapped):
    owner, invoke = snapshot_projector
    nodes = [
        {"execution_state": "error"},
        {"evidence_outcome": "UNKNOWN", "diagnostic": "sandbox_launch_failed:" + "x" * 4097},
    ]
    facts = [("missing", "not_string", False), ("string", "over_bound", True)]
    if swapped:
        nodes.reverse()
        facts.reverse()
    root = _snapshot_report(**dict(zip(("base", "head"), nodes, strict=True)))
    root["private_inventory"] = "x" * (2 * 1024 * 1024 if large else 0)
    rows = invoke(json.dumps(root))
    expected = [
        {
            "analyzer": "contracts",
            "side": side,
            "shape": shape,
            "length_bucket": bucket,
            "recognized_leading_token": recognized,
        }
        for side, (shape, bucket, recognized) in zip(("base", "head"), facts, strict=True)
    ]
    _assert_snapshot_fact_rows(owner, rows, expected)
    assert [row[_SNAPSHOT_FIELD] for row in rows if _SNAPSHOT_FIELD in row] == [
        [{"analyzer": "contracts", "side": side, "reason": "unclassified"} for side in ("base", "head")]
    ]
    if owner == "independent":
        assert rows[0]["report_outcome"] == ("oversized_report" if large else "structured_report")
        assert rows[0]["assurance_status"] == ("UNAVAILABLE" if large else "UNKNOWN")
        assert rows[0]["overall_verdict"] == ("UNAVAILABLE" if large else "FAIL")


@pytest.mark.parametrize("payload", ("null", "[]", "42", '"PRIVATE_CANARY"', '{"analyzer_evidence":"PRIVATE_CANARY"}'))
def test_snapshot_fallback_facts_omit_invalid_report_shapes(snapshot_projector, payload):
    _, invoke = snapshot_projector
    rows = invoke(payload)
    assert all(_SNAPSHOT_FACTS_FIELD not in row for row in rows)


def test_snapshot_fallback_facts_accept_unique_contracts_among_unrelated_values(snapshot_projector):
    owner, invoke = snapshot_projector
    report = _snapshot_report(head={"evidence_outcome": "UNKNOWN"})
    report["analyzer_evidence"] = [None, [], _SNAPSHOT_CANARY, {"id": "ruff"}, *report["analyzer_evidence"]]
    rows = invoke(json.dumps(report))
    _assert_snapshot_fact_rows(
        owner,
        rows,
        [
            {
                "analyzer": "contracts",
                "side": "head",
                "shape": "missing",
                "length_bucket": "not_string",
                "recognized_leading_token": False,
            }
        ],
    )


@pytest.mark.parametrize("unclassified_side", ("base", "head"))
def test_snapshot_fallback_facts_do_not_promote_the_classified_side(snapshot_projector, unclassified_side):
    owner, invoke = snapshot_projector
    classified_side = "head" if unclassified_side == "base" else "base"
    rows = invoke(
        json.dumps(
            _snapshot_report(
                **{
                    unclassified_side: {"execution_state": "error"},
                    classified_side: {
                        "execution_state": "error",
                        "diagnostic": "analyzer_process_error:" + _SNAPSHOT_CANARY,
                    },
                }
            )
        )
    )
    _assert_snapshot_fact_rows(
        owner,
        rows,
        [
            {
                "analyzer": "contracts",
                "side": unclassified_side,
                "shape": "missing",
                "length_bucket": "not_string",
                "recognized_leading_token": False,
            }
        ],
    )


def _source_rows(result):
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert SOURCE_CANARY not in result.stdout
    assert "PRIVATE_SOURCE_CANARY" not in result.stdout
    assert "/private/" not in result.stdout
    assert len(result.stdout.encode()) < 1024
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows) == 2, "installed source publisher must emit two records"
    assert [row["invocation"] for row in rows] == list(SOURCE_INVOCATIONS)
    return rows


@pytest.mark.parametrize("case", ["valid", "other_version", "cache_present"])
@pytest.mark.parametrize("invocation", SOURCE_INVOCATIONS)
def test_installed_source_receipt_precedes_subject_entry(tmp_path, case, invocation):
    trusted, environment, digests = synthetic_installed_source_reviewer(tmp_path, case)
    entry = run_complete_source_bootstrap(trusted, invocation)
    assert entry["receipt"] is not None, "complete source receipt must exist before subject entry"
    expected = source_observed(invocation, digests)
    assert json.loads(entry["receipt"]) == expected
    rows = _source_rows(run_source_publication(trusted, environment))
    assert rows == [expected if name == invocation else source_unavailable(name) for name in SOURCE_INVOCATIONS]
    calls = [json.loads(line) for line in (trusted / "verifier-calls.jsonl").read_text().splitlines()]
    assert len(calls) == 1
    call = calls[0]
    assert call["package"] == str(trusted / "home/.specfact/modules/specfact-code-review")
    assert call["metadata"]["name"] == "nold-ai/specfact-code-review"
    assert {key: value for key, value in call.items() if key not in {"package", "metadata"}} == {
        "allow_unsigned": False,
        "require_integrity": True,
        "require_signature": True,
        "public_key_pem": "SYNTHETIC_BUNDLED_PEM\n",
    }
    assert not (trusted / "subject/tempting.json").exists()


@pytest.mark.parametrize(
    "case",
    [
        "verifier_false",
        "verifier_exception",
        "wrong_name",
        "invalid_metadata",
        "missing_key",
        "oversized_key",
        "missing_runner",
        "missing_sandbox",
        "missing_spec",
        "runner_file",
        "sandbox_file",
        "runner_origin",
        "sandbox_origin",
        "relative_origin",
        "relative_file",
        "bytecode_origin",
        "missing_bindings",
        "noncallable_binding",
        "shared_string_binding",
        "different_binding",
        "missing_source",
        "directory_source",
        "fifo_source",
        "oversized_source",
        "oversized_manifest",
        "symlink_source",
        "symlink_descendant",
        "symlink_package",
        "manifest_drift",
        "runner_drift",
        "sandbox_drift",
        "manifest_replace",
        "observer_error",
    ],
)
@pytest.mark.parametrize("invocation", SOURCE_INVOCATIONS)
def test_installed_source_predicates_preserve_operation(tmp_path, case, invocation):
    trusted, environment, _ = synthetic_installed_source_reviewer(tmp_path, case)
    entry = run_complete_source_bootstrap(trusted, invocation)
    assert entry["receipt"] is not None, "unavailable source receipt must exist before subject entry"
    assert json.loads(entry["receipt"]) == source_unavailable(invocation)
    assert _source_rows(run_source_publication(trusted, environment)) == [
        source_unavailable(name) for name in SOURCE_INVOCATIONS
    ]


@pytest.mark.parametrize("invocation", SOURCE_INVOCATIONS)
def test_installed_source_receipt_write_failure_preserves_operation(tmp_path, invocation):
    trusted, environment, _ = synthetic_installed_source_reviewer(tmp_path, "receipt_write_error")
    run_complete_source_bootstrap(trusted, invocation)
    assert not (trusted / f"controller-source-{invocation}.private.json").exists()
    assert _source_rows(run_source_publication(trusted, environment)) == [
        source_unavailable(name) for name in SOURCE_INVOCATIONS
    ]


@pytest.mark.parametrize(
    "review_exit,status,reason",
    [
        (0, "PASS", ""),
        (2, "PASS", ""),
        (7, "PASS", ""),
        (17, "PASS", ""),
        (124, "PASS", ""),
        (0, "NOT_APPLICABLE", "no_governed_impact"),
        (7, "NOT_APPLICABLE", "no_governed_impact"),
        (0, "UNKNOWN", "policy_parse_failure"),
    ],
)
def test_installed_source_publication_preserves_command_result(tmp_path, review_exit, status, reason):
    case = (review_exit, status, reason)
    legacy_root, legacy_environment = create_isolated_reviewer(tmp_path / "legacy", case)
    private_report = json.dumps({"findings": [], "private_path": SOURCE_CANARY}).encode()
    (legacy_root / "review.private.json").write_bytes(private_report)
    legacy = run_independent_source_command(legacy_root, legacy_environment)
    trusted, environment, digests = synthetic_installed_source_reviewer(tmp_path / "observed", review_case=case)
    report = trusted / "review.private.json"
    report.write_bytes(private_report)
    command = run_independent_source_command(trusted, environment)
    expected_exit = 1 if status == "UNKNOWN" else review_exit
    assert command.returncode == legacy.returncode == expected_exit
    assert command.stdout == legacy.stdout
    assert command.stderr == legacy.stderr == ""
    if status == "UNKNOWN":
        assert_incomplete_preparation(trusted, command, reason)
    else:
        assert_installed_review_arguments(trusted, prepared=status == "PASS")
    publication = run_source_publication(trusted, environment)
    assert report.read_bytes() == private_report
    assert SOURCE_CANARY not in command.stdout + command.stderr
    expected = [source_observed("preparation", digests)]
    expected.append(source_unavailable("review") if status == "UNKNOWN" else source_observed("review", digests))
    assert _source_rows(publication) == expected
    assert command.returncode == expected_exit


def test_installed_source_invocations_keep_distinct_authenticated_bytes(tmp_path):
    trusted, environment, digests = synthetic_installed_source_reviewer(tmp_path, "distinct_invocations")
    sandbox = trusted / "home/.specfact/modules/specfact-code-review/src/specfact_code_review/run/sandbox.py"
    review_digests = digests | {"sandbox": hashlib.sha256(sandbox.read_bytes() + b"# review source\n").hexdigest()}
    command = run_independent_source_command(trusted, environment)
    assert command.returncode == 0, command.stdout + command.stderr
    assert_installed_review_arguments(trusted)
    assert _source_rows(run_source_publication(trusted, environment)) == [
        source_observed("preparation", digests),
        source_observed("review", review_digests),
    ]


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "symlink",
        "directory",
        "fifo",
        "unreadable",
        "invalid_utf8",
        "invalid_json",
        "trailing_json",
        "duplicate_key",
        "nonobject",
        "oversized",
        "oversized_unicode",
        "extra_key",
        "wrong_phase",
        "wrong_invocation",
        "wrong_status",
        "wrong_identity",
        "null_digest",
        "uppercase_digest",
        "nonhex_digest",
        "short_digest",
        "long_digest",
        "missing_digest",
        "runner_sha256",
        "error",
        "path",
        "identity_kind",
    ],
)
def test_installed_source_publisher_rejects_private_receipts(tmp_path, case):
    trusted, environment = source_publisher_environment(tmp_path)
    receipt = trusted / "controller-source-preparation.private.json"
    write_source_receipt_case(receipt, case)
    review = source_observed("review", {"runner": "c" * 64, "sandbox": "d" * 64})
    (trusted / "controller-source-review.private.json").write_text(json.dumps(review))
    try:
        result = run_source_publication(trusted, environment)
    finally:
        if case == "unreadable":
            receipt.chmod(0o600)
    assert _source_rows(result) == [source_unavailable("preparation"), review]


@pytest.mark.parametrize(
    "first,second",
    [("observed", "observed"), ("unavailable", "unavailable"), ("observed", "invalid"), ("exact_bound", "observed")],
)
def test_installed_source_publication_reconstructs_independent_variants(tmp_path, first, second):
    trusted, environment = source_publisher_environment(tmp_path)
    expected = []
    for invocation, variant in zip(SOURCE_INVOCATIONS, (first, second), strict=True):
        value = (
            source_observed(invocation, {"runner": "1" * 64, "sandbox": "2" * 64})
            if variant in {"observed", "exact_bound"}
            else source_unavailable(invocation)
        )
        expected.append(value)
        payload = "PRIVATE_SOURCE_CANARY" if variant == "invalid" else json.dumps(value)
        if variant == "exact_bound":
            payload = payload.ljust(4096)
        (trusted / f"controller-source-{invocation}.private.json").write_text(payload)
    assert _source_rows(run_source_publication(trusted, environment)) == expected


@pytest.mark.parametrize(
    "case", ["missing_root", "missing_interpreter", "missing_reviewer", "partial_projector", "bootstrap_failure"]
)
def test_installed_source_publication_survives_setup_and_projector_failure(tmp_path, case):
    trusted, environment = source_publisher_environment(tmp_path)
    if case == "missing_root":
        environment.pop("TRUSTED_ROOT")
    if case == "missing_interpreter":
        (trusted / "venv/bin/python").unlink()
    if case == "partial_projector":
        interpreter = trusted / "venv/bin/python"
        interpreter.unlink()
        interpreter.write_text(
            "#!/bin/sh\n"
            "printf 'PRIVATE_SOURCE_CANARY partial\\n'\n"
            "printf 'PRIVATE_SOURCE_CANARY error\\n' >&2\nexit 7\n"
        )
        interpreter.chmod(0o700)
    if case == "bootstrap_failure":
        trusted, environment = create_isolated_reviewer(tmp_path / "failed", (0, "PASS", ""))
        site = next((trusted / "venv/lib").glob("python*/site-packages"))
        (site / "specfact_cli/registry/__init__.py").write_text("raise RuntimeError('PRIVATE_SOURCE_CANARY')\n")
        command = run_independent_source_command(trusted, environment)
        assert command.returncode == 1
        assert not (trusted / "review-attempted").exists()
        assert "PRIVATE_SOURCE_CANARY" not in command.stdout + command.stderr
    assert _source_rows(run_source_publication(trusted, environment)) == [
        source_unavailable(name) for name in SOURCE_INVOCATIONS
    ]


@pytest.mark.parametrize("case", producer_cases.CASES, ids=lambda case: case["id"])
def test_snapshot_producer_categories_are_additive(snapshot_projector, case):
    field = producer_cases.FIELD
    owner, invoke = snapshot_projector
    Path(os.environ["REVIEW_LOG"]).write_text(case.get("log", _SNAPSHOT_CANARY), encoding="utf-8")
    rows = invoke(case["payload"])
    expected = case["categories"][owner]
    assert [row[field] for row in rows if field in row] == ([expected] if expected else []), (
        "Missing finite producer field"
    )
    if owner == "candidate":
        assert all(set(row) == {field} for row in rows if field in row)
        legacy = [row for row in rows if field not in row]
    else:
        legacy = [{key: value for key, value in row.items() if key != field} for row in rows]
    assert legacy == case["legacy"][owner]


@pytest.mark.parametrize("review_exit", (17, 124))
def test_candidate_producer_category_preserves_review_exit(tmp_path, review_exit):
    field = producer_cases.FIELD
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(producer_cases.FAILURE_PAYLOAD)
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(step["run"] for step in workflow["jobs"]["customer"]["steps"] if step.get("name") == STEP_NAME)
    guard = recipe[recipe.index('if [ "$review_exit" -ne 0 ]; then') :].splitlines()[0]
    invocation = next(line for line in recipe.splitlines() if "<<'PY_CANDIDATE_FAILURE'" in line)
    shell = f"set -euo pipefail\nreview_exit={review_exit}\n{guard}\n" + recipe[recipe.index(invocation) :]
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert result.returncode == review_exit and result.stderr == ""
    assert (tmp_path / "contract-projection.private.log").read_bytes() == b""
    assert [row[field] for row in rows if field in row] == [producer_cases.FAILURE_ROWS]
    assert "PRIVATE_CANARY" not in result.stdout + result.stderr
    assert report.read_text() == producer_cases.FAILURE_PAYLOAD
