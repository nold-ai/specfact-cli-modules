from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from tests.support.capsule_review_fixtures import (
    _FIXED_ANALYZER_FINDING_ROWS,
    REPO_ROOT,
    STEP_NAME,
    _git,
    _write_public_report,
    independent_review_job,
    public_projector,
)


def test_hosted_preparation_has_separate_bound_and_cannot_bypass_review() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = step["run"]
    assert "timeout=1800" in recipe
    assert "code review runtime prepare --scope index" in recipe
    assert recipe.index("code review runtime prepare --scope index") < recipe.index("review_exit=0")
    assert 'SPECFACT_CODE_REVIEW_CAPSULE_CACHE="$CUSTOMER_ROOT/commit-review-cache"' in recipe
    assert "continue-on-error" not in step


def test_independent_reviewer_runs_in_fresh_job_without_candidate_host_code() -> None:
    independent = independent_review_job()
    assert independent is not None, "Installed reviewer must not share writable venv/HOME with candidate host code"
    assert independent["runs-on"] == "ubuntu-24.04"
    assert independent["if"] == "github.event_name == 'pull_request'"
    assert not independent.get("needs"), "Candidate execution cannot suppress the independent review job"
    recipe = "\n".join(str(step.get("run", "")) for step in independent["steps"])
    assert "specfact-cli==0.55.4" in recipe
    assert "--version 0.51.2" in recipe
    assert "--source marketplace" in recipe
    assert "env -i" in recipe


@pytest.mark.parametrize(
    "forbidden",
    [
        "pre_commit_code_review.py",
        "link_dev_module.py",
        "SPECFACT_MODULES_ROOTS",
        "SPECFACT_ALLOW_UNSIGNED",
        "$GITHUB_WORKSPACE/scripts",
    ],
)
def test_independent_reviewer_excludes_each_candidate_host_route(forbidden: str) -> None:
    independent = independent_review_job()
    recipe = "\n".join(str(step.get("run", "")) for step in independent["steps"])
    assert forbidden not in recipe


def test_independent_reviewer_preserves_scope_budgets_and_preload_order() -> None:
    independent = independent_review_job()
    recipe = "\n".join(str(step.get("run", "")) for step in independent["steps"])
    assert recipe.count("timeout=1800") == 2
    assert "--scope index --enforcement changed --bug-hunt" in recipe
    assert "discover_snapshot" in recipe and "prepare_runtime" in recipe
    assert "runtime prepare --project-config" not in recipe, "Mutable worktree prep cannot prewarm index identities"
    assert 'CommandRegistry.get_module_typer("code")' in recipe
    assert recipe.index('CommandRegistry.get_module_typer("code")') < recipe.index("os.chdir(sys.argv[1])")


def test_independent_reviewer_cannot_continue_after_failure_or_retain_credentials() -> None:
    for step in independent_review_job()["steps"]:
        assert not step.get("continue-on-error", False)
        if "checkout@" in step.get("uses", ""):
            assert step["with"]["persist-credentials"] is False


def _run_projector(tmp_path, program):

    path = tmp_path / "projector.py"
    path.write_text(program)
    return subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=False, cwd=tmp_path)


def _write_preparation_fixture(tmp_path, case):

    descriptor = tmp_path / "descriptor.json"
    descriptor.write_text("{}")
    payload = {"runtimes": {side: {"descriptor": str(descriptor)} for side in ("base", "head")}}
    if case.startswith("not_applicable"):
        payload = {"scope": "index", "status": "NOT_APPLICABLE", "diagnostic": "no_governed_impact", "runtimes": {}}
        overrides = {
            "not_applicable_reason": {"diagnostic": "private-reason"},
            "not_applicable_scope": {"scope": "full"},
            "not_applicable_runtimes": {"runtimes": ["private"]},
            "not_applicable_nonempty": {"runtimes": {"head": {"descriptor": str(descriptor)}}},
        }
        payload.update(overrides.get(case, {}))
    elif case == "missing_base":
        payload["runtimes"].pop("base")
    elif case == "missing_files":
        descriptor.unlink()
    report = tmp_path / "preparation.private.json"
    report.write_text("not-json/private" if case == "invalid" else json.dumps(payload))
    return report


@pytest.mark.parametrize(
    "case,expected",
    [
        ("prepared", (0, "PREPARED", "prepared", True, True, True, True)),
        ("not_applicable", (0, "NOT_APPLICABLE", "not_applicable", False, False, False, False)),
        *[
            (case, (1, "INCOMPLETE", "invalid_not_applicable", False, False, False, False))
            for case in (
                "not_applicable_reason",
                "not_applicable_scope",
                "not_applicable_runtimes",
                "not_applicable_nonempty",
            )
        ],
        ("missing_base", (1, "INCOMPLETE", "missing_descriptor_fields", False, True, False, True)),
        ("invalid", (1, "INCOMPLETE", "invalid_json", False, False, False, False)),
        ("missing_files", (1, "INCOMPLETE", "missing_descriptor_files", True, True, False, False)),
    ],
)
def test_successful_index_preparation_requires_both_descriptors(tmp_path, monkeypatch, case, expected):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    assert "PY_PREPARATION" in step["run"]
    program = step["run"].split("<<'PY_PREPARATION'\n", 1)[1].split("\nPY_PREPARATION", 1)[0]
    monkeypatch.setenv("PREPARATION_COMMAND_SUCCEEDED", "1")
    monkeypatch.setenv("PREPARATION_REPORT", str(_write_preparation_fixture(tmp_path, case)))
    result = _run_projector(tmp_path, program)
    code, status, outcome, base_supplied, head_supplied, base, head = expected
    assert result.returncode == code
    assert json.loads(result.stdout) == {
        "status": status,
        "phase": "index_preparation",
        "report_outcome": outcome,
        "base_descriptor_supplied": base_supplied,
        "head_descriptor_supplied": head_supplied,
        "base_descriptor_present": base,
        "head_descriptor_present": head,
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("private namespace_unavailable detail", "capsule_namespace_unavailable"),
        ("project_test_selection_ambiguous:private", "test_selection_ambiguous"),
        ("project_runtime_prepare_failed:private", "project_runtime_preparation_failed"),
        ("unknown/private", "unclassified_preparation_failure"),
    ],
)
def test_independent_preparation_failure_projects_only_fixed_classes(tmp_path, monkeypatch, text, expected):

    recipe = next(
        step["run"]
        for step in independent_review_job()["steps"]
        if step.get("name") == "Prepare and review through the authenticated installed controller"
    )
    assert "PY_FAILURE" in recipe
    program = recipe.split("<<'PY_FAILURE'\n", 1)[1].split("\nPY_FAILURE", 1)[0]
    report = tmp_path / "preparation.private.log"
    report.write_text(text)
    monkeypatch.setenv("PREPARATION_LOG", str(report))
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "status": "INCOMPLETE",
        "phase": "trusted_index_preparation",
        "diagnostic": expected,
    }


def _write_audit_fixture(tmp_path, profile):
    report = tmp_path / "audit.private.log"
    report.write_text(f'apparmor="DENIED" profile="{profile}" comm="bwrap-static" capname="net_admin" /private/path\n')
    baseline = tmp_path / "baseline.private.log"
    baseline.write_text(report.read_text() if profile == "stale" else "")
    if profile == "numeric_fd":
        report.write_text('apparmor="DENIED" profile="unconfined" comm="3" capname="net_admin" /private/path\n')
    if profile == "rotated":
        baseline.write_text("previous kernel prefix")
    return baseline, report


@pytest.mark.parametrize(
    "profile,flags",
    [
        ("specfact-customer-commit-review", (True, True, True, True, False, True, False, True, False)),
        ("unconfined", (True, True, True, True, False, False, True, True, False)),
        ("foreign", (True, True, True, True, False, False, False, True, False)),
        ("stale", (True, True, False, False, False, False, False, False, False)),
        ("numeric_fd", (True, True, True, False, True, False, True, True, False)),
        ("rotated", (True, False, False, False, False, False, False, False, False)),
        ("capture_failed", (False, False, False, False, False, False, False, False, False)),
    ],
)
def test_namespace_audit_retains_only_fixed_observation_booleans(tmp_path, monkeypatch, profile, flags):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    selected = [
        s
        for s in workflow["jobs"]["customer"]["steps"]
        if s.get("name") == "Collect namespace audit evidence privately"
    ]
    assert len(selected) == 1
    step = selected[0]
    assert step["if"] == "failure() && steps.deferred_review.outcome == 'failure'"
    program = step["run"].split("<<'PY_NAMESPACE'\n", 1)[1].split("\nPY_NAMESPACE", 1)[0]
    baseline, report = _write_audit_fixture(tmp_path, profile)
    monkeypatch.setenv("NAMESPACE_AUDIT_BASELINE", str(baseline))
    monkeypatch.setenv("NAMESPACE_AUDIT_BASELINE_CAPTURED", "1")
    monkeypatch.setenv("NAMESPACE_AUDIT", str(report))
    monkeypatch.setenv("NAMESPACE_AUDIT_CAPTURED", "0" if profile == "capture_failed" else "1")
    monkeypatch.setenv("EXPECTED_LAUNCHER_PROFILE", "specfact-customer-commit-review")
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    public = json.loads(result.stdout)
    phase = public.pop("phase")
    assert phase == "namespace_audit"
    assert set(map(type, public.values())) == {bool}
    keys = (
        "audit_captured",
        "audit_boundary_available",
        "apparmor_denial_audit_observed",
        "launcher_name_audit_observed",
        "numeric_descriptor_name_audit_observed",
        "expected_profile_audit_observed",
        "unconfined_profile_audit_observed",
        "net_admin_denial_observed",
        "userns_denial_observed",
    )
    assert public == dict(zip(keys, flags, strict=True))


def _write_independent_failure_fixture(tmp_path, case):

    report = {"assurance_status": "FAIL", "overall_verdict": "FAIL", "findings": [], "analyzer_evidence": []}
    if case == "findings":
        report["findings"] = [{"category": "correctness", "message": "private-token"}]
    elif case in {"nested", "direct"}:
        row = {
            "id": "pylint",
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "diagnostic": "namespace_unavailable:private-token",
        }
        report["analyzer_evidence"] = (
            [{"id": "pylint", "diagnostic": "snapshot_member_incomplete", "head": row}] if case == "nested" else [row]
        )
        report["analyzer_evidence"].append({**row, "id": "private-token"})
    elif case == "tool_error":
        report["findings"] = [{"category": "tool_error", "message": "private-token"}]
    path = tmp_path / "review.private.json"
    path.write_text(
        "invalid/private-token"
        if case == "invalid"
        else "x" * (2 * 1024 * 1024 + 1)
        if case == "oversized"
        else json.dumps(report)
    )
    if case in {"missing", "timeout"}:
        path.unlink()
    log = tmp_path / "review.private.log"
    log.write_text("TimeoutExpired:private-token" if case == "timeout" else "unclassified/private-token")
    return path, log


def _expected_review_projection(expected):
    outcome, flags, codes = expected
    verdict = "FAIL" if outcome == "structured_report" else "UNAVAILABLE"
    keys = ("findings_present", "tool_error_present", "execution_error_present", "unknown_evidence_present")
    projection = {
        "phase": "independent_review",
        "report_outcome": outcome,
        "assurance_status": verdict,
        "overall_verdict": verdict,
        "diagnostic_observations": codes,
        "error_analyzers": ["pylint"] if flags[2] else [],
        "unknown_analyzers": ["pylint"] if flags[3] else [],
        **dict(zip(keys, flags, strict=True)),
    }
    if outcome == "oversized_report":
        projection["report_header_observed"] = False
        projection["error_analyzer_sides"] = {}
        projection["crosshair_failure_observations"] = []
    return projection


@pytest.mark.parametrize(
    "case,expected",
    [
        ("findings", ("structured_report", (True, False, False, False), ["unclassified"])),
        ("nested", ("structured_report", (False, False, True, True), ["namespace_unavailable"])),
        ("direct", ("structured_report", (False, False, True, True), ["namespace_unavailable"])),
        ("tool_error", ("structured_report", (True, True, False, False), ["unclassified"])),
        ("missing", ("missing_report", (False, False, False, False), ["unclassified"])),
        ("invalid", ("invalid_json", (False, False, False, False), ["unclassified"])),
        ("oversized", ("oversized_report", (False, False, False, False), ["unclassified"])),
        ("timeout", ("missing_report", (False, False, False, False), ["timeout_marker_observed"])),
    ],
)
def test_independent_review_failure_keeps_nested_evidence_and_private_tokens(tmp_path, monkeypatch, case, expected):

    steps = independent_review_job()["steps"]
    selected = [step for step in steps if step.get("name") == "Project independent review failure privately"]
    assert len(selected) == 1
    step = selected[0]
    assert step["if"] == "failure() && steps.independent_review.outcome == 'failure'"
    program = step["run"].split("<<'PY_REVIEW_FAILURE'\n", 1)[1].split("\nPY_REVIEW_FAILURE", 1)[0]
    report, log = _write_independent_failure_fixture(tmp_path, case)
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(log))
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    projection = _expected_review_projection(expected)
    projection.update(
        snapshot_observations=[],
        enforcement_observation={"assurance_status": "FAIL"} if expected[0] == "structured_report" else {},
        finding_observations=[],
    )
    if case == "nested":
        projection["snapshot_observations"] = [
            {
                "analyzer": "pylint",
                "side": "head",
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "diagnostic_classes": ["namespace_unavailable"],
            }
        ]
    assert json.loads(result.stdout) == projection
    assert "private-token" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "message,tool,category,expected",
    [
        (
            "CrossHair timed out before mandatory evidence completed.",
            "crosshair",
            "tool_error",
            ("crosshair_timeout_observed", []),
        ),
        (
            "CrossHair process error: ModuleNotFoundError: private-token",
            "crosshair",
            "tool_error",
            ("crosshair_process_error_observed", ["module_not_found_observed"]),
        ),
        (
            "Unrecognized CrossHair output: private-token",
            "crosshair",
            "tool_error",
            ("crosshair_unrecognized_output_observed", []),
        ),
        (
            "Unable to execute CrossHair: PermissionError: private-token",
            "crosshair",
            "tool_error",
            ("crosshair_execute_error_observed", ["permission_error_observed"]),
        ),
        ("CrossHair process error: private-token", "pylint", "tool_error", None),
        ("CrossHair process error: private-token", "crosshair", "contracts", None),
    ],
)
def test_candidate_crosshair_failure_emits_only_fixed_classes(tmp_path, message, tool, category, expected):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    assert "PY_CANDIDATE_FAILURE" in step["run"]
    program = (
        step["run"].split("<<'PY_CANDIDATE_FAILURE'", 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    )
    root = tmp_path / ".specfact"
    root.mkdir()
    (root / "code-review.json").write_text(
        json.dumps(
            {
                "analyzer_evidence": [{"id": "private-token", "diagnostic": "private-token:private/path"}],
                "findings": [{"tool": tool, "category": category, "message": message}],
            }
        )
    )
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    output = (
        []
        if expected is None
        else [{"analyzer": "contracts", "diagnostic_class": expected[0], "exception_observations": expected[1]}]
    )
    observations = []
    if tool == "crosshair" and category == "tool_error" and message.startswith("Unrecognized CrossHair output:"):
        observations = [{"analyzer": "contracts", "diagnostic_class": "crosshair_rejected_other_stdout"}]
    output.append({"snapshot_observations": [], "enforcement_observation": {}, "finding_observations": observations})
    assert [json.loads(line) for line in result.stdout.splitlines()] == output
    assert "private-token" not in result.stdout + result.stderr


def _large_report_fixture():
    return {
        "analyzer_evidence": [
            {
                "id": "contracts",
                "base": {
                    "execution_state": "error",
                    "evidence_outcome": "UNKNOWN",
                    "diagnostic": "analyzer_reported_incomplete_execution:private-token",
                },
            }
        ],
        "findings": [{"message": "private-token" + "x" * (2 * 1024 * 1024)}],
    }


def _oversized_report_payload(case):

    root = _large_report_fixture()
    if case == "nested":
        root = {
            "scope_evidence": {"analyzer_evidence": root["analyzer_evidence"]},
            "analyzer_evidence": [],
            "findings": root["findings"],
        }
    if case == "unicode":
        root["findings"] = [{"message": "private-token" + "é" * (2 * 1024 * 1024)}]
    overrides = {
        "duplicate": '{"analyzer_evidence":[],"analyzer_evidence":[],"findings":[',
        "malformed": "{private-token:",
        "incomplete": '{"analyzer_evidence":[',
        "wrong_findings_shape": '{"analyzer_evidence":[],"findings":{',
    }
    if case in overrides:
        return overrides[case] + "x" * (2 * 1024 * 1024 + 1)
    return json.dumps(root, ensure_ascii=False)


@pytest.mark.parametrize(
    "case", ["valid", "unicode", "nested", "duplicate", "malformed", "incomplete", "wrong_findings_shape"]
)
def test_oversized_independent_report_preserves_only_complete_root_header(tmp_path, monkeypatch, case):

    payload = _oversized_report_payload(case)
    report, log = _write_independent_failure_fixture(tmp_path, "missing")
    report.write_text(payload)
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(log))
    step = next(
        step
        for step in independent_review_job()["steps"]
        if step.get("name") == "Project independent review failure privately"
    )
    program = step["run"].split("<<'PY_REVIEW_FAILURE'\n", 1)[1].split("\nPY_REVIEW_FAILURE", 1)[0]
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    value = json.loads(result.stdout)
    assert value["report_outcome"] == "oversized_report"
    assert value["assurance_status"] == value["overall_verdict"] == "UNAVAILABLE"
    assert value["report_header_observed"] is (case in ("valid", "unicode", "nested"))
    assert (
        value["error_analyzers"]
        == value["unknown_analyzers"]
        == (["contracts"] if case in ("valid", "unicode") else [])
    )
    assert value["findings_present"] is False
    assert "private-token" not in result.stdout + result.stderr


def _literal_prefix_report(row, token, cut):

    prefix = '{"analyzer_evidence":[' + json.dumps(row) + ',{"target_execution":{"padding":"'
    middle = '","value":'
    padding = 2 * 1024 * 1024 - len((prefix + middle).encode()) - cut
    return prefix + "x" * padding + middle + token + '}}],"findings":[]}'


def _oversized_analyzer_payload(case):

    row = _large_report_fixture()["analyzer_evidence"][0]
    literals = {
        "cut_true": ("true", 3),
        "cut_false": ("false", 4),
        "cut_null": ("null", 3),
        "cut_exponent": ("1e2", 2),
        "cut_fraction": ("1.2", 2),
        "cut_negative": ("-1", 1),
        "cut_escape": ('"\\u1234"', 5),
        "invalid_literal": ("truX", 4),
        "invalid_exponent": ("1eX", 3),
        "invalid_escape": ('"\\u1Z"', 5),
    }
    if case in literals:
        return _literal_prefix_report(row, *literals[case])
    inventory = "é" if case == "unicode_inventory" else "x"
    large_row = {"id": "targeted-pytest-coverage", "target_execution": {"inventory": inventory * (2 * 1024 * 1024)}}
    payload = json.dumps({"analyzer_evidence": [row, large_row], "findings": []}, ensure_ascii=False)
    if case == "invalid_row":
        payload = '{"analyzer_evidence":[' + json.dumps(row) + ",private-token" + "x" * (2 * 1024 * 1024)
    if case == "duplicate_root":
        payload = '{"analyzer_evidence":[],"analyzer_evidence":[' + json.dumps(row) + "," + json.dumps(large_row)
    if case in ("trailing_comma", "trailing_comma_ten"):
        count = 10 if case == "trailing_comma_ten" else 1
        payload = (
            '{"analyzer_evidence":['
            + ",".join([json.dumps(row)] * count)
            + ',],"findings":["'
            + "x" * (2 * 1024 * 1024)
        )
    return payload


@pytest.mark.parametrize(
    "case",
    [
        "truncated_inventory",
        "unicode_inventory",
        "invalid_row",
        "duplicate_root",
        "trailing_comma",
        "trailing_comma_ten",
        "cut_true",
        "cut_false",
        "cut_null",
        "cut_exponent",
        "cut_fraction",
        "cut_negative",
        "cut_escape",
        "invalid_literal",
        "invalid_exponent",
        "invalid_escape",
    ],
)
def test_oversized_analyzer_inventory_preserves_complete_prior_rows(tmp_path, monkeypatch, case):

    payload = _oversized_analyzer_payload(case)
    report, log = _write_independent_failure_fixture(tmp_path, "missing")
    report.write_text(payload)
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(log))
    step = next(
        step
        for step in independent_review_job()["steps"]
        if step.get("name") == "Project independent review failure privately"
    )
    program = step["run"].split("<<'PY_REVIEW_FAILURE'\n", 1)[1].split("\nPY_REVIEW_FAILURE", 1)[0]
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    value = json.loads(result.stdout)
    assert value["report_outcome"] == "oversized_report"
    assert value["assurance_status"] == value["overall_verdict"] == "UNAVAILABLE"
    observed = case in (
        "truncated_inventory",
        "unicode_inventory",
        "cut_true",
        "cut_false",
        "cut_null",
        "cut_exponent",
        "cut_fraction",
        "cut_negative",
        "cut_escape",
    )
    assert value["report_header_observed"] is observed
    assert value["error_analyzers"] == value["unknown_analyzers"] == (["contracts"] if observed else [])
    assert value["findings_present"] is False
    assert "private-token" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "case,expected_sides,expected_classes",
    [
        (
            "contracts",
            {"contracts": ["base"]},
            ["crosshair_process_error_observed", "value_error_observed", "wrong_parameter_order_observed"],
        ),
        ("other_tool", {"contracts": ["base"]}, []),
        ("diagnostic_bound", {}, []),
    ],
)
def test_large_private_report_projects_contract_failure_classes_without_acceptance(
    tmp_path, monkeypatch, case, expected_sides, expected_classes
):

    root = _large_report_fixture()
    root["analyzer_evidence"][0]["head"] = {"execution_state": "ran", "evidence_outcome": "PASS"}
    root["analyzer_evidence"][0]["base"]["target_execution"] = {"inventory": "x" * (2 * 1024 * 1024)}
    root["findings"] = [
        {
            "category": "tool_error",
            "tool": "crosshair" if case == "contracts" else "ruff",
            "message": "CrossHair process error: ValueError: wrong parameter order: private-token",
        }
    ]
    if case == "diagnostic_bound":
        root["findings"][0]["message"] += "x" * (32 * 1024 * 1024)
    report, log = _write_independent_failure_fixture(tmp_path, "missing")
    report.write_text(json.dumps(root))
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(log))
    step = next(
        step
        for step in independent_review_job()["steps"]
        if step.get("name") == "Project independent review failure privately"
    )
    program = step["run"].split("<<'PY_REVIEW_FAILURE'\n", 1)[1].split("\nPY_REVIEW_FAILURE", 1)[0]
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    value = json.loads(result.stdout)
    policy = (value["report_outcome"], value["assurance_status"], value["overall_verdict"], value["findings_present"])
    assert policy == ("oversized_report", "UNAVAILABLE", "UNAVAILABLE", False)
    assert value["report_header_observed"] is bool(expected_sides)
    assert value["error_analyzer_sides"] == expected_sides
    assert value["crosshair_failure_observations"] == expected_classes
    assert "private-token" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "case,expected_classes",
    [
        ("contracts", ["value_error_observed", "wrong_parameter_order_observed"]),
        ("other_tool", None),
        ("diagnostic_bound", None),
    ],
)
def test_candidate_large_report_retains_unavailable_marker_and_fixed_failure_classes(tmp_path, case, expected_classes):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    program = (
        step["run"].split("<<'PY_CANDIDATE_FAILURE'", 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    )
    root = tmp_path / ".specfact"
    root.mkdir()
    size = 32 if case == "diagnostic_bound" else 2
    (root / "code-review.json").write_text(
        json.dumps(
            {
                "private_inventory": "x" * (size * 1024 * 1024),
                "analyzer_evidence": [],
                "findings": [
                    {
                        "category": "tool_error",
                        "tool": "ruff" if case == "other_tool" else "crosshair",
                        "message": "CrossHair process error: ValueError: wrong parameter order: private-token",
                    }
                ],
            }
        )
    )
    result = _run_projector(tmp_path, program)
    expected = [{"analyzer": "contracts", "diagnostic_class": "candidate_report_unavailable"}]
    if expected_classes is not None:
        expected.append(
            {
                "analyzer": "contracts",
                "diagnostic_class": "crosshair_process_error_observed",
                "exception_observations": expected_classes,
            }
        )
    assert result.returncode == 0
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[:-1] == expected
    assert rows[-1] == {"snapshot_observations": [], "enforcement_observation": {}, "finding_observations": []}
    assert "private-token" not in result.stdout + result.stderr


def test_candidate_projection_ignores_retired_sample_frames(tmp_path):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    program = (
        step["run"].split("<<'PY_CANDIDATE_FAILURE'", 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    )
    root = tmp_path / ".specfact"
    root.mkdir()
    (root / "code-review.json").write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "category": "tool_error",
                        "tool": "crosshair",
                        "message": (
                            "CrossHair timed out before mandatory evidence completed. "
                            "sampled_frames=argument_generation,PRIVATE_TOKEN,run_portable_pytest"
                        ),
                    }
                ]
            }
        )
    )
    result = _run_projector(tmp_path, program)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert result.returncode == 0
    assert "sampled_frame_observations" not in rows[-1]
    assert "PRIVATE_TOKEN" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "nested,expected",
    [
        ({"base": {"execution_state": "error", "diagnostic": "PRIVATE_TOKEN"}}, ["base"]),
        ({"head": {"evidence_outcome": "UNKNOWN"}}, ["head"]),
        ({"base": {"execution_state": "error"}, "head": {"evidence_outcome": "UNKNOWN"}}, ["base", "head"]),
        ({"base": {"execution_state": "ran", "evidence_outcome": "PASS"}}, []),
        ({"base": "PRIVATE_TOKEN", "unknown_side": {"execution_state": "error"}}, []),
    ],
)
def test_candidate_incomplete_snapshot_projection_is_finite(tmp_path, nested, expected):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    program = (
        step["run"].split("<<'PY_CANDIDATE_FAILURE'", 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    )
    root = tmp_path / ".specfact"
    root.mkdir()
    (root / "code-review.json").write_text(
        json.dumps(
            {
                "analyzer_evidence": [
                    {"id": "contracts", **nested},
                    {"id": "PRIVATE_TOKEN", "base": {"execution_state": "error"}},
                ]
            }
        )
    )
    result = _run_projector(tmp_path, program)
    assert result.returncode == 0
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    observations = [
        {
            "analyzer": "contracts",
            "side": side,
            **{key: nested[side][key] for key in ("execution_state", "evidence_outcome") if key in nested[side]},
        }
        for side in expected
    ]
    summary = {"snapshot_observations": observations, "enforcement_observation": {}, "finding_observations": []}
    assert rows == ([{"analyzer": "contracts", "incomplete_snapshot_sides": expected}] if expected else []) + [summary]
    assert "PRIVATE_TOKEN" not in result.stdout + result.stderr


def test_failed_candidate_diagnostics_expose_only_bounded_tracked_locations(tmp_path: Path) -> None:
    code = public_projector("customer")
    _git(tmp_path, "init", "-q")
    source = tmp_path / "public.py"
    source.write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "analyzer_evidence": [{"id": "PRIVATE_ANALYZER", "diagnostic": "PRIVATE_TOKEN"}],
                "findings": [
                    {"file": "public.py", "line": 12, "severity": "warning", "message": "PRIVATE_MESSAGE"},
                    {"file": "/private/SECRET.py", "line": 1, "severity": "error"},
                    {"file": "untracked_SECRET.py", "line": 1, "severity": "error"},
                    {"file": "public.py", "line": True, "severity": "error"},
                    {"file": "public.py", "line": 0, "severity": "error"},
                    {"file": "public.py", "line": 1, "severity": "PRIVATE_SEVERITY"},
                    *[{"file": "public.py", "line": line, "severity": "info"} for line in range(20, 225)],
                ],
            }
        )
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert len(rows) == 200
    assert rows[0] == {"file": "public.py", "line": 12, "severity": "warning"}
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
def test_both_failed_reviews_project_fixed_analyzer_identity_without_private_text(
    tmp_path: Path, job_name: str
) -> None:
    code = public_projector(job_name)
    _write_public_report(tmp_path, _FIXED_ANALYZER_FINDING_ROWS)
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert rows[1] == {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "clean_code",
        "tool": "radon",
        "rule": "CC34",
    }
    assert rows[0]["failure_class"] == "timeout"
    assert "PRIVATE" not in result.stdout


def _native_review_failure_step() -> dict:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/native-capsule-release.yml").read_text())
    steps = workflow["jobs"]["execute"]["steps"]
    matches = [step for step in steps if step.get("name") == "Project failed native review diagnostics"]
    assert len(matches) == 1, "native CI has no bounded failure diagnostic step"
    return matches[0]


def test_native_failure_projection_keeps_original_execution_blocking() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/native-capsule-release.yml").read_text())
    execute = workflow["jobs"]["execute"]
    original = next(
        step
        for step in execute["steps"]
        if step.get("name") == "Execute exact archive, real extensions, all analyzers and offline reuse"
    )
    assert original["id"] == "native_review"
    assert original["run"] == (
        "python -m scripts.native_release.acceptance --mode candidate "
        "\\"
        "\n"
        '  --artifact "$RUNNER_TEMP/archive" --work "$RUNNER_TEMP/acceptance" --runner "$PLATFORM_LABEL"\n'
    )
    assert "continue-on-error" not in original and "continue-on-error" not in execute
    assert execute["timeout-minutes"] == 60
    assert execute["strategy"]["matrix"]["runner"] == ["macos-14", "macos-15", "macos-26"]
    assert execute["strategy"]["matrix"]["python"] == ["3.11", "3.12", "3.13"]
    assert _native_review_failure_step()["if"] == "failure() && steps.native_review.outcome == 'failure'"


@pytest.mark.parametrize(
    "rows,errors,unknowns",
    [
        (
            [{"id": "contracts", "execution_state": "error", "evidence_outcome": "UNKNOWN"}],
            ["contracts"],
            ["contracts"],
        ),
        ([False, {"id": ["PRIVATE_ID"]}, {"id": "PRIVATE_ID", "evidence_outcome": "UNKNOWN"}], [], []),
        (
            [
                {"id": "contracts", "execution_state": "error", "evidence_outcome": "UNKNOWN"},
                {"id": "contracts", "execution_state": "ran", "evidence_outcome": "PASS"},
            ],
            ["contracts"],
            ["contracts"],
        ),
    ],
)
def test_native_ci_projector_retains_known_members_without_private_output(
    tmp_path, monkeypatch, rows, errors, unknowns
):
    report = tmp_path / "review.json"
    report.write_text(
        json.dumps(
            {
                "assurance_status": "UNKNOWN",
                "analyzer_evidence": rows,
                "message": "PRIVATE_CONTENT",
                "file": "PRIVATE_PATH",
            }
        )
    )
    monkeypatch.setenv("NATIVE_REVIEW_REPORT", str(report))
    recipe = _native_review_failure_step()["run"]
    code = recipe.split("<<'PY_NATIVE_DIAGNOSTIC'", 1)[1].split("\n", 1)[1].rsplit("\nPY_NATIVE_DIAGNOSTIC", 1)[0]
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and not result.stderr
    assert "PRIVATE" not in result.stdout and len(result.stdout.encode()) <= 4096
    assert json.loads(result.stdout) == {
        "phase": "native_review",
        "report_outcome": "structured_report",
        "assurance_status": "UNKNOWN",
        "error_analyzers": errors,
        "unknown_analyzers": unknowns,
    }


@pytest.mark.parametrize("kind", ["missing", "invalid", "oversized"])
def test_unavailable_native_report_diagnostic_is_bounded_without_acceptance(tmp_path, monkeypatch, kind):
    report = tmp_path / "review.json"
    if kind == "invalid":
        report.write_text("PRIVATE_INVALID_JSON")
    elif kind == "oversized":
        report.write_bytes(b" " * (32 * 1024 * 1024 + 1))
    monkeypatch.setenv("NATIVE_REVIEW_REPORT", str(report))
    recipe = _native_review_failure_step()["run"]
    code = recipe.split("<<'PY_NATIVE_DIAGNOSTIC'", 1)[1].split("\n", 1)[1].rsplit("\nPY_NATIVE_DIAGNOSTIC", 1)[0]
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and not result.stderr
    assert "PRIVATE" not in result.stdout and len(result.stdout.encode()) <= 4096
    assert json.loads(result.stdout) == {
        "phase": "native_review",
        "report_outcome": kind + "_report",
        "assurance_status": "UNAVAILABLE",
        "error_analyzers": [],
        "unknown_analyzers": [],
    }


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Unrecognized CrossHair output: PRIVATE_DETAIL", "crosshair_unrecognized_output_observed"),
        ("CrossHair process error: PRIVATE_DETAIL", "crosshair_process_error_observed"),
        ("CrossHair timed out before mandatory evidence completed.", "crosshair_timeout_observed"),
        ("Unable to execute CrossHair: PRIVATE_DETAIL", "crosshair_spawn_error_observed"),
    ],
)
def test_native_failure_projects_fixed_contract_codes_without_raw_messages(tmp_path, monkeypatch, message, expected):
    report = tmp_path / "review.json"
    report.write_text(
        json.dumps(
            {
                "assurance_status": "FAIL",
                "analyzer_evidence": [{"id": "contracts", "execution_state": "error", "evidence_outcome": "UNKNOWN"}],
                "findings": [
                    {"tool": "crosshair", "rule": "CROSSHAIR_INCOMPLETE_EVIDENCE", "message": message},
                    {"tool": "crosshair", "rule": "CROSSHAIR_INCOMPLETE_EVIDENCE", "message": message},
                    {"tool": "PRIVATE_TOOL", "rule": "CROSSHAIR_INCOMPLETE_EVIDENCE", "message": "PRIVATE_DETAIL"},
                ],
            }
        )
    )
    monkeypatch.setenv("NATIVE_REVIEW_REPORT", str(report))
    recipe = _native_review_failure_step()["run"]
    code = recipe.split("<<'PY_NATIVE_DIAGNOSTIC'", 1)[1].split("\n", 1)[1].rsplit("\nPY_NATIVE_DIAGNOSTIC", 1)[0]
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and not result.stderr
    record = json.loads(result.stdout)
    assert record["crosshair_failure_observations"] == [expected]
    assert record["error_analyzers"] == ["contracts"] and record["unknown_analyzers"] == ["contracts"]
    assert record["assurance_status"] == "FAIL"
    assert "PRIVATE" not in result.stdout and len(result.stdout.encode()) <= 4096


@pytest.mark.parametrize(
    "diagnostic,expected",
    [
        ("native_worker_request_invalid:PRIVATE_DETAIL", "native_worker_request_invalid_observed"),
        ("native_worker_result_invalid:PRIVATE_DETAIL", "native_worker_result_invalid_observed"),
        ("native_worker_result_size_exceeded", "native_worker_result_size_exceeded_observed"),
        ("managed_tool_replay_required", "managed_tool_replay_required_observed"),
    ],
)
def test_native_failure_projects_fixed_worker_codes_without_raw_messages(tmp_path, monkeypatch, diagnostic, expected):
    report = tmp_path / "review.json"
    report.write_text(
        json.dumps(
            {
                "assurance_status": "FAIL",
                "analyzer_evidence": [
                    {
                        "id": "contracts",
                        "execution_state": "error",
                        "evidence_outcome": "UNKNOWN",
                        "diagnostic": diagnostic,
                    },
                    {"id": "PRIVATE_TOOL", "execution_state": "error", "diagnostic": "PRIVATE_DETAIL"},
                ],
                "findings": [False, {"tool": "crosshair", "rule": "CROSSHAIR_INCOMPLETE_EVIDENCE", "message": []}],
            }
        )
    )
    monkeypatch.setenv("NATIVE_REVIEW_REPORT", str(report))
    recipe = _native_review_failure_step()["run"]
    code = recipe.split("<<'PY_NATIVE_DIAGNOSTIC'", 1)[1].split("\n", 1)[1].rsplit("\nPY_NATIVE_DIAGNOSTIC", 1)[0]
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and not result.stderr
    record = json.loads(result.stdout)
    assert record["crosshair_failure_observations"] == [expected]
    assert record["error_analyzers"] == ["contracts"] and record["unknown_analyzers"] == ["contracts"]
    assert "PRIVATE" not in result.stdout and len(result.stdout.encode()) <= 4096


@pytest.mark.parametrize(
    "rows,findings",
    [
        (
            [
                {"id": "contracts", "execution_state": "error"},
                {
                    "id": "contracts",
                    "execution_state": "ran",
                    "diagnostic": "native_worker_request_invalid:PRIVATE_DETAIL",
                },
            ],
            [],
        ),
        ([{"id": "contracts", "execution_state": "error", "diagnostic": []}], "PRIVATE_CONTENT"),
        (
            [{"id": "contracts", "execution_state": "error"}],
            [
                {
                    "tool": "PRIVATE_TOOL",
                    "rule": "CROSSHAIR_INCOMPLETE_EVIDENCE",
                    "message": "CrossHair process error: PRIVATE_DETAIL",
                },
                {"tool": "crosshair", "rule": "PRIVATE_RULE", "message": "CrossHair process error: PRIVATE_DETAIL"},
                {"tool": "crosshair", "rule": "CROSSHAIR_INCOMPLETE_EVIDENCE", "message": "PRIVATE_DETAIL"},
            ],
        ),
    ],
)
def test_native_failure_excludes_unrecognized_or_successful_diagnostic_rows(tmp_path, monkeypatch, rows, findings):
    report = tmp_path / "review.json"
    report.write_text(json.dumps({"analyzer_evidence": rows, "findings": findings}))
    monkeypatch.setenv("NATIVE_REVIEW_REPORT", str(report))
    recipe = _native_review_failure_step()["run"]
    code = recipe.split("<<'PY_NATIVE_DIAGNOSTIC'", 1)[1].split("\n", 1)[1].rsplit("\nPY_NATIVE_DIAGNOSTIC", 1)[0]
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and not result.stderr
    record = json.loads(result.stdout)
    assert "crosshair_failure_observations" not in record
    assert record["error_analyzers"] == ["contracts"]
    assert "PRIVATE" not in result.stdout and len(result.stdout.encode()) <= 4096


_FAILURE_MARKERS = ("PY_CANDIDATE_FAILURE", "PY_REVIEW_FAILURE")
_PRIVATE_CANARY = "PRIVATE_CLASSIFIER_PATH_TEST_ID"


def _actual_failure_observations(tmp_path, monkeypatch, marker, payload):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(
        step["run"] for job in workflow["jobs"].values() for step in job["steps"] if marker in step.get("run", "")
    )
    program = recipe.split("<<'" + marker + "'", 1)[1].split("\n", 1)[1].split("\n" + marker, 1)[0]
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(payload)
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(tmp_path / "missing"))
    path = tmp_path / "projector.py"
    path.write_text(program)
    result = subprocess.run(
        [sys.executable, str(path)], cwd=tmp_path, capture_output=True, text=True, timeout=4, check=False
    )
    assert result.returncode == 0 and not result.stderr
    assert _PRIVATE_CANARY not in result.stdout
    assert len(result.stdout.encode()) < 16384
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
def test_linux_failure_observations_preserve_side_and_required_unknown(tmp_path, monkeypatch, marker):
    node = {
        "execution_state": "error",
        "evidence_outcome": "UNKNOWN",
        "diagnostic": "project_pytest_coverage_missing; " + _PRIVATE_CANARY,
        "target_execution": {
            "exit_code": 1,
            "collected": [_PRIVATE_CANARY],
            "deselected": [],
            "coverage": {_PRIVATE_CANARY: _PRIVATE_CANARY},
            "internal_errors": [_PRIVATE_CANARY],
            "records": [{"nodeid": _PRIVATE_CANARY, "phase": "call", "outcome": "failed"}],
            "collection_errors": [{"nodeid": _PRIVATE_CANARY, "detail": _PRIVATE_CANARY}],
            "coverage_diagnostic": "project_pytest_coverage_missing:" + _PRIVATE_CANARY,
        },
    }
    data = {
        "findings": [],
        "analyzer_evidence": [{"id": "targeted-pytest-coverage", "base": node}],
        "enforcement_mode": "changed",
        "assurance_status": "UNKNOWN",
        "has_unknown_required_evidence": True,
        "enforcement_summary": "Changed enforcement cannot pass while required evidence is UNKNOWN.",
    }
    diagnostic = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    assert diagnostic["snapshot_observations"] == [
        {
            "analyzer": "targeted-pytest-coverage",
            "side": "base",
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "diagnostic_classes": ["project_pytest_coverage_missing"],
            "target_execution_observed": True,
            "coverage_object_observed": True,
            "exit_code": 1,
            "collected_count": 1,
            "deselected_count": 0,
            "internal_errors_count": 1,
            "records_count": 1,
            "call_identity_count": 1,
            "failed_setup_records_count": 0,
            "unexecuted_collected_count": 0,
            "collection_errors_count": 1,
            "coverage_diagnostic_classes": ["project_pytest_coverage_missing"],
        }
    ]
    assert diagnostic["enforcement_observation"] == {
        "enforcement_mode": "changed",
        "assurance_status": "UNKNOWN",
        "has_unknown_required_evidence": True,
        "advisory_projection_blocked_by_required_unknown": True,
        "summary_class": "changed_enforcement_required_unknown",
    }
    assert diagnostic["finding_observations"] == []


def _linux_boundary_payload(case):
    target = {
        "exit_code": True,
        "collected": [_PRIVATE_CANARY, 1],
        "coverage": _PRIVATE_CANARY,
        "records": [{"nodeid": _PRIVATE_CANARY, "phase": _PRIVATE_CANARY, "outcome": "passed"}],
        "collection_errors": [_PRIVATE_CANARY],
        "internal_errors": [False],
    }
    node = {"execution_state": "error", "evidence_outcome": "UNKNOWN", "target_execution": target}
    row = {"id": "targeted-pytest-coverage", "head": node}
    data = {"findings": [], "analyzer_evidence": [row]}
    if case == "duplicate_analyzer":
        data["analyzer_evidence"].append(row.copy())
    if case == "too_many_analyzers":
        data["analyzer_evidence"] = [row] + [{"id": _PRIVATE_CANARY}] * 10
    if case == "large":
        data["padding"] = "x" * (2 * 1024 * 1024)
    if case == "oversize":
        data["padding"] = "x" * (32 * 1024 * 1024)
    if case == "absent":
        data["analyzer_evidence"] = []
    if case == "count_bound":
        target["collected"] = [_PRIVATE_CANARY] * 100001
    payload = json.dumps(data)
    if case == "duplicate_side":
        payload = payload.replace('"head":', '"head":{},"head":', 1)
    if case == "invalid_json":
        payload = _PRIVATE_CANARY
    return payload


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
@pytest.mark.parametrize(
    "case",
    [
        "invalid_values",
        "duplicate_analyzer",
        "duplicate_side",
        "too_many_analyzers",
        "large",
        "oversize",
        "absent",
        "count_bound",
        "invalid_json",
    ],
)
def test_linux_failure_observations_omit_invalid_private_or_unavailable_fields(tmp_path, monkeypatch, marker, case):
    diagnostic = _actual_failure_observations(tmp_path, monkeypatch, marker, _linux_boundary_payload(case))
    expected = []
    if case in ("invalid_values", "large", "count_bound"):
        expected = [
            {
                "analyzer": "targeted-pytest-coverage",
                "side": "head",
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "target_execution_observed": True,
            }
        ]
    assert diagnostic["snapshot_observations"] == expected
    assert diagnostic["enforcement_observation"] == {}
    assert diagnostic["finding_observations"] == []


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
@pytest.mark.parametrize(
    "payload,expected",
    [
        ("hook...Passed; " + _PRIVATE_CANARY, "pre_commit_status"),
        ("hook...Failed\n" + _PRIVATE_CANARY, "pre_commit_status"),
        ("hook...Skipped\r\n" + _PRIVATE_CANARY, "pre_commit_status"),
        ("...Passed", "other_stdout"),
        ("   ...Passed", "other_stdout"),
        ("hook..Passed", "other_stdout"),
        ("hook...Passed" + _PRIVATE_CANARY, "other_stdout"),
        (_PRIVATE_CANARY + "; hook...Passed", "other_stdout"),
        ("smart-test status: ready (uses pytest tests/); " + _PRIVATE_CANARY, "smart_test_status"),
        ("smart-test check: configured (modules repo scoped); " + _PRIVATE_CANARY, "smart_test_status"),
        (_PRIVATE_CANARY + "." * 20000 + "unrecognized", "other_stdout"),
    ],
    ids=[
        "semicolon-passed",
        "newline-failed",
        "crlf-skipped",
        "no-label",
        "blank-label",
        "two-dots",
        "suffix",
        "later-segment",
        "smart-ready",
        "smart-configured",
        "long-dotted-stdout",
    ],
)
def test_linux_failure_global_crosshair_status_is_bounded_and_side_free(
    tmp_path, monkeypatch, marker, payload, expected
):
    data = {
        "analyzer_evidence": [],
        "findings": [
            {"tool": "crosshair", "category": "tool_error", "message": "Unrecognized CrossHair output: " + payload}
        ]
        * 32,
    }
    diagnostic = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    assert diagnostic["snapshot_observations"] == []
    assert diagnostic["finding_observations"] == [
        {"analyzer": "contracts", "diagnostic_class": "crosshair_rejected_" + expected}
    ]


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
def test_linux_failure_global_pylint_and_coverage_classes_do_not_infer_side(tmp_path, monkeypatch, marker):
    data = {
        "analyzer_evidence": [],
        "findings": [
            {
                "tool": "pylint",
                "category": "tool_error",
                "message": "Unable to parse pylint output: Command " + _PRIVATE_CANARY + " timed out after 30 seconds",
            },
            {
                "tool": "pytest",
                "category": "tool_error",
                "message": "project_pytest_coverage_missing; " + _PRIVATE_CANARY,
            },
        ],
    }
    diagnostic = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    assert diagnostic["snapshot_observations"] == []
    assert diagnostic["finding_observations"] == [
        {"analyzer": "pylint", "diagnostic_class": "pylint_timeout_observed"},
        {"analyzer": "targeted-pytest-coverage", "diagnostic_class": "project_pytest_coverage_missing"},
    ]


_DERIVED_OBSERVATION_FIELDS = {
    "call_identity_count",
    "unexecuted_collected_count",
    "failed_setup_records_count",
    "coverage_files_count",
}
_KNOWN_SKIP_PAYLOAD = (
    "No staged review-relevant files under packages/, registry/, scripts/, tools/, tests/, "
    "or openspec/changes/; skipping code review gate."
)
_PYTEST_PRODUCER_CODES = (
    "project_pytest_request_invalid",
    "project_pytest_collection_error",
    "project_pytest_internal_error",
    "project_pytest_configuration_or_collection_failed",
    "project_pytest_execution_incomplete",
    "project_pytest_unexecuted",
    "project_pytest_failure_without_observed_test",
    "project_pytest_installed_coverage",
    "project_pytest_installed_coverage_unavailable",
)


def _terminal_record_variant(case, target, expected):
    record = target["records"][0]
    nodeids = {
        "empty-identity": "",
        "long-identity": "x" * 65537,
        "record-budget": "x" * 65536,
        "boolean-nodeid": True,
    }
    if case in nodeids:
        record["nodeid"] = nodeids[case]
    if case == "missing-nodeid":
        record.pop("nodeid")
    if case == "bad-outcome":
        record["outcome"] = "PRIVATE_INVALID"
    if case == "bad-record":
        target["records"].append({"nodeid": _PRIVATE_CANARY, "phase": "unknown", "outcome": "passed"})
    if case == "missing-records":
        target.pop("records")
    replacements = {"null-records": None, "nonmapping-record": [False]}
    if case in replacements:
        target["records"] = replacements[case]
    counts = {"record-budget": 129, "record-bound": 100001, "at-record-bound": 100000}
    if case in counts:
        target["records"] *= counts[case]
    invalid = {
        *nodeids,
        *replacements,
        "missing-nodeid",
        "bad-outcome",
        "bad-record",
        "missing-records",
        "record-bound",
    }
    if case in invalid:
        expected.clear()
        expected["coverage_files_count"] = 1


def _terminal_collection_variant(case, target, expected):
    replacements = {
        "empty-collected": [""],
        "long-collected": ["x" * 65537],
        "collection-budget": ["x" * 65536] * 129,
        "bad-collected": [_PRIVATE_CANARY, False],
    }
    if case in replacements:
        target["collected"] = replacements[case]
    if case in ("combined-budget", "at-character-bound"):
        target["collected"] = ["x" * 65536] * 64
        target["records"][0]["nodeid"] = "x" * 65536
        target["records"] *= 64 if case == "at-character-bound" else 65
    counts = {"collection-bound": 100001, "at-collection-bound": 100000}
    if case in counts:
        target["collected"] *= counts[case]
    if case in {*replacements, "combined-budget", "collection-bound"}:
        expected.pop("unexecuted_collected_count")


def _terminal_coverage_variant(case, target, expected):
    variants = {
        "files-null": None,
        "files-list": [],
        "files-empty-key": {"": {}},
        "files-long-key": {"x" * 65537: {}},
    }
    if case in variants:
        target["coverage"]["files"] = variants[case]
    if case == "files-missing":
        target["coverage"] = {}
    if case == "files-bound":
        target["coverage"]["files"] = {str(index): {} for index in range(100001)}
    if case == "files-budget":
        target["coverage"]["files"] = {str(index) + "x" * 65530: {} for index in range(129)}
    if case == "files-at-bound":
        target["coverage"]["files"] = {str(index): None for index in range(100000)}
        expected["coverage_files_count"] = 100000
        return
    expected.pop("coverage_files_count")


def _terminal_observation_target(case):
    identity = _PRIVATE_CANARY
    record: dict[str, object] = {"nodeid": identity, "phase": "call", "outcome": "passed"}
    target = {"collected": [identity], "records": [record], "coverage": {"files": {identity: False}}}
    expected = {
        "call_identity_count": 1,
        "coverage_files_count": 1,
        "failed_setup_records_count": 0,
        "unexecuted_collected_count": 0,
    }
    if case == "failed-setup":
        target["collected"].append(identity + "_missing")
        target["records"].append({"nodeid": identity + "_missing", "phase": "setup", "outcome": "failed"})
        expected.update(unexecuted_collected_count=1, failed_setup_records_count=1)
    if case == "duplicates":
        target["collected"] *= 3
        target["records"] *= 4
    if case == "skipped-setup":
        record.update(phase="setup", outcome="skipped")
        expected["call_identity_count"] = 0
    if case == "failed-call":
        record["outcome"] = "failed"
    if case == "unrelated-record":
        record["nodeid"] = identity + "_other"
        expected["unexecuted_collected_count"] = 1
    if case == "empty":
        target.update(collected=[], records=[], coverage={"files": {}})
        return target, dict.fromkeys(_DERIVED_OBSERVATION_FIELDS, 0)
    _terminal_record_variant(case, target, expected)
    _terminal_collection_variant(case, target, expected)
    if case.startswith("files-"):
        _terminal_coverage_variant(case, target, expected)
    return target, expected


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
@pytest.mark.parametrize(
    "case",
    [
        "ordinary",
        "failed-setup",
        "duplicates",
        "skipped-setup",
        "failed-call",
        "unrelated-record",
        "empty",
        "empty-identity",
        "long-identity",
        "record-budget",
        "bad-record",
        "record-bound",
        "at-record-bound",
        "missing-records",
        "null-records",
        "nonmapping-record",
        "missing-nodeid",
        "boolean-nodeid",
        "bad-outcome",
        "at-character-bound",
        "empty-collected",
        "long-collected",
        "collection-budget",
        "combined-budget",
        "bad-collected",
        "collection-bound",
        "at-collection-bound",
        "files-null",
        "files-list",
        "files-empty-key",
        "files-long-key",
        "files-missing",
        "files-bound",
        "files-budget",
        "files-at-bound",
    ],
)
def test_linux_terminal_identity_counts_are_complete_bounded_observations(tmp_path, monkeypatch, marker, case):
    target, expected = _terminal_observation_target(case)
    data = {
        "findings": [],
        "analyzer_evidence": [
            {"id": "targeted-pytest-coverage", "base": {"execution_state": "error", "target_execution": target}}
        ],
    }
    result = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    row = result["snapshot_observations"][0]
    assert {key: value for key, value in row.items() if key in _DERIVED_OBSERVATION_FIELDS} == expected
    assert all(type(row[key]) is int and 0 <= row[key] <= 100000 for key in expected)
    assert row["side"] == "base" and result["finding_observations"] == []
    if case in ("empty-identity", "long-identity", "record-budget"):
        assert row["records_count"] == len(target["records"])
    if case in ("empty-collected", "long-collected", "collection-budget", "combined-budget"):
        assert row["collected_count"] == len(target["collected"])


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
@pytest.mark.parametrize("code", _PYTEST_PRODUCER_CODES)
@pytest.mark.parametrize("delimiter", ["", ":", ";"], ids=["exact", "colon", "semicolon"])
def test_linux_known_worker_classes_keep_side_and_global_provenance(tmp_path, monkeypatch, marker, code, delimiter):
    message = code + (delimiter + _PRIVATE_CANARY if delimiter else "")
    data = {
        "analyzer_evidence": [
            {"id": "targeted-pytest-coverage", "head": {"execution_state": "error", "diagnostic": message}}
        ],
        "findings": [{"tool": "pytest", "category": "tool_error", "message": message}],
    }
    result = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    assert result["snapshot_observations"] == [
        {
            "analyzer": "targeted-pytest-coverage",
            "side": "head",
            "execution_state": "error",
            "diagnostic_classes": [code],
        }
    ]
    assert result["finding_observations"] == [{"analyzer": "targeted-pytest-coverage", "diagnostic_class": code}]


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
@pytest.mark.parametrize(
    "case", ["directory", "module", "suffix", "space", "embedded", "missing-source", "empty-source", "wrong-tool"]
)
def test_linux_coverage_classes_require_exact_producer_boundaries(tmp_path, monkeypatch, marker, case):
    messages = {
        "directory": "project_pytest_installed_coverage_directory_invalid",
        "module": "project_pytest_installed_coverage_module_invalid",
        "suffix": "project_pytest_installed_coverage_evil",
        "space": "project_pytest_installed_coverage " + _PRIVATE_CANARY,
        "embedded": _PRIVATE_CANARY + "; project_pytest_installed_coverage",
        "missing-source": "Coverage data missing for " + _PRIVATE_CANARY,
        "empty-source": "Coverage data missing for ",
        "wrong-tool": "Coverage data missing for " + _PRIVATE_CANARY,
    }
    data = {
        "analyzer_evidence": [],
        "findings": [
            {"tool": "ruff" if case == "wrong-tool" else "pytest", "category": "tool_error", "message": messages[case]}
        ],
    }
    result = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    expected = (
        [{"analyzer": "targeted-pytest-coverage", "diagnostic_class": "coverage_source_entry_missing"}]
        if case == "missing-source"
        else []
    )
    assert result["finding_observations"] == expected
    assert result["snapshot_observations"] == []


@pytest.mark.parametrize("marker", _FAILURE_MARKERS)
@pytest.mark.parametrize(
    "case", ["exact", "joined", "suffix", "newline", "leading", "ansi", "punctuation", "semicolon", "unrelated"]
)
def test_linux_crosshair_known_skip_class_means_retained_prefix_only(tmp_path, monkeypatch, marker, case):
    payloads = {
        "exact": _KNOWN_SKIP_PAYLOAD,
        "joined": _KNOWN_SKIP_PAYLOAD + "; " + _PRIVATE_CANARY,
        "suffix": _KNOWN_SKIP_PAYLOAD + _PRIVATE_CANARY,
        "newline": _KNOWN_SKIP_PAYLOAD + "\n" + _PRIVATE_CANARY,
        "leading": _PRIVATE_CANARY + _KNOWN_SKIP_PAYLOAD,
        "ansi": "\x1b[0m" + _KNOWN_SKIP_PAYLOAD,
        "punctuation": _KNOWN_SKIP_PAYLOAD[:-1],
        "semicolon": _KNOWN_SKIP_PAYLOAD.replace(";", ","),
        "unrelated": "skipping " + _PRIVATE_CANARY,
    }
    data = {
        "analyzer_evidence": [],
        "findings": [
            {
                "tool": "crosshair",
                "category": "tool_error",
                "message": "Unrecognized CrossHair output: " + payloads[case],
            }
        ],
    }
    result = _actual_failure_observations(tmp_path, monkeypatch, marker, json.dumps(data))
    expected = (
        "crosshair_rejected_known_skip_prefix" if case in ("exact", "joined") else "crosshair_rejected_other_stdout"
    )
    assert result["finding_observations"] == [{"analyzer": "contracts", "diagnostic_class": expected}]
    assert result["snapshot_observations"] == []


@pytest.fixture(params=_FAILURE_MARKERS)
def observe_native_projection(request, tmp_path, monkeypatch):
    def project(target):
        payload = {
            "findings": [],
            "analyzer_evidence": [
                {
                    "id": "targeted-pytest-coverage",
                    "base": {
                        "execution_state": "error",
                        "target_execution": target,
                    },
                }
            ],
        }
        result = _actual_failure_observations(tmp_path, monkeypatch, request.param, json.dumps(payload))
        row = result["snapshot_observations"][0]
        return {key: value for key, value in row.items() if key not in {"analyzer", "side", "execution_state"}}

    return project


def _native_projection_record(node="private::test", phase="call", passed=True, skipped=False):
    return {"nodeid": node, "phase": phase, "passed": passed, "skipped": skipped, "wasxfail": "PRIVATE"}


@pytest.mark.parametrize(
    "records,expected",
    [
        ([_native_projection_record(phase="setup", passed=False)], (1, 0, 1, 1)),
        ([_native_projection_record(phase="setup", passed=False, skipped=True)], (1, 0, 0, 0)),
        ([_native_projection_record(), _native_projection_record(phase="teardown")], (2, 1, 0, 0)),
        ([_native_projection_record(passed=False)], (1, 1, 0, 0)),
        ([_native_projection_record(phase="collection")], (1, 0, 0, 1)),
        ([], (0, 0, 0, 1)),
    ],
)
def test_native_observer_native_records(observe_native_projection, records, expected):
    result = observe_native_projection({"process_exit": 1, "records": records, "collected": ["private::test"]})
    assert result["exit_code"] == 1
    assert (
        tuple(
            result[key]
            for key in (
                "records_count",
                "call_identity_count",
                "failed_setup_records_count",
                "unexecuted_collected_count",
            )
        )
        == expected
    )
    assert "PRIVATE" not in str(result) and "private::test" not in str(result)


_INVALID_RECORD_CASES = {
    "passed-int": [{**_native_projection_record(), "passed": 1}],
    "skipped-str": [{**_native_projection_record(), "skipped": "false"}],
    "missing": [{"nodeid": "private::test", "phase": "call", "passed": True, "wasxfail": "PRIVATE"}],
    "contradiction": [{**_native_projection_record(), "skipped": True}],
    "dual": [{**_native_projection_record(), "outcome": "passed"}],
    "mixed": [_native_projection_record(), {"nodeid": "b", "phase": "call", "outcome": "passed"}],
    "bad-phase": [{**_native_projection_record(), "phase": "unknown"}],
    "late-bad": [_native_projection_record()] * 100
    + [{"nodeid": "bad", "phase": "call", "passed": None, "skipped": False}],
}


@pytest.mark.parametrize("fault", _INVALID_RECORD_CASES)
def test_native_observer_native_invalid_records_omit_all_record_counts(observe_native_projection, fault):
    result = observe_native_projection({"records": _INVALID_RECORD_CASES[fault], "collected": ["private::test"]})
    assert (
        not {"records_count", "call_identity_count", "failed_setup_records_count", "unexecuted_collected_count"}
        & result.keys()
    )


@pytest.mark.parametrize(
    "fault", ["empty", "long", "record-budget", "combined-budget", "at-combined-budget", "entry-limit"]
)
def test_native_observer_native_identity_budgets(observe_native_projection, fault):
    record = _native_projection_record(
        node={"empty": "", "entry-limit": "x"}.get(fault, "x" * (65537 if fault == "long" else 65536))
    )
    records = [record] * (
        129
        if fault == "record-budget"
        else 64
        if fault in ("combined-budget", "at-combined-budget")
        else 100001
        if fault == "entry-limit"
        else 1
    )
    collected = ["x" * 65536] * (65 if fault == "combined-budget" else 64 if fault == "at-combined-budget" else 1)
    result = observe_native_projection({"records": records, "collected": collected})
    if fault == "entry-limit":
        assert "records_count" not in result
        return
    assert result["records_count"] == len(records)
    assert ("call_identity_count" in result) == (fault in ("combined-budget", "at-combined-budget"))
    assert ("unexecuted_collected_count" in result) == (fault == "at-combined-budget")


@pytest.mark.parametrize(
    "target,expected",
    [
        ({"process_exit": 0}, 0),
        ({"process_exit": 5}, 5),
        ({"process_exit": True}, None),
        ({"process_exit": -1}, None),
        ({"process_exit": 6}, None),
        ({"process_exit": "1"}, None),
        ({"exit_code": 2}, 2),
        ({"exit_code": 2, "process_exit": 2}, None),
        ({"exit_code": 2, "process_exit": 1}, None),
    ],
)
def test_native_observer_exit_schema(observe_native_projection, target, expected):
    assert observe_native_projection(target).get("exit_code") == expected


def test_native_observer_portable_counts_remain_exact(observe_native_projection):
    assert observe_native_projection(
        {
            "exit_code": 1,
            "records": [{"nodeid": "a", "phase": "setup", "outcome": "failed"}],
            "collected": ["a"],
            "coverage": {"files": {"src.py": {}}},
        }
    ) == {
        "target_execution_observed": True,
        "coverage_object_observed": True,
        "coverage_files_count": 1,
        "exit_code": 1,
        "collected_count": 1,
        "records_count": 1,
        "call_identity_count": 0,
        "failed_setup_records_count": 1,
        "unexecuted_collected_count": 1,
    }


def _actual_native_observer_class():
    runner = REPO_ROOT / "packages/specfact-code-review/src/specfact_code_review/run/runner.py"
    tree = ast.parse(runner.read_text())
    producer = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_pytest_observer_script"
    )
    namespace: dict[str, Any] = {
        "_SOURCE_ROOT": REPO_ROOT,
        "Path": Path,
        "sys": sys,
        "_pytest_in_capsule": lambda: False,
    }
    exec(compile(ast.Module(body=[producer], type_ignores=[]), str(runner), "exec"), namespace)
    generated = ast.parse(namespace["_pytest_observer_script"]())
    observer_class = next(node for node in generated.body if isinstance(node, ast.ClassDef) and node.name == "Observer")
    namespace = {"json": json, "pathlib": pathlib}
    exec(
        compile(ast.Module(body=[observer_class], type_ignores=[]), "<actual-native-observer>", "exec"),
        namespace,
    )
    return namespace["Observer"]


def test_native_observer_actual_native_producer_failed_setup_and_skip(observe_native_projection, tmp_path):
    observer_path = tmp_path / "observer.json"
    instance = _actual_native_observer_class()(observer_path)
    for nodeid, skipped in [("private::failed", False), ("private::skipped", True)]:
        instance.pytest_itemcollected(SimpleNamespace(nodeid=nodeid))
        instance.pytest_runtest_logreport(SimpleNamespace(nodeid=nodeid, when="setup", passed=False, skipped=skipped))
    instance.pytest_sessionfinish(None, 1)
    coverage = tmp_path / "coverage.json"
    coverage.write_text('{"files": {"private.py": {}}}')
    junit = tmp_path / "junit.xml"
    junit.write_text("<testsuite/>")
    path = REPO_ROOT / "packages/specfact-code-review/src/specfact_code_review/run/native_worker_evidence.py"
    spec = importlib.util.spec_from_file_location("native_evidence_proof", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = module._capture_pytest_observation(
        (SimpleNamespace(returncode=1), coverage, observer_path, junit), SimpleNamespace(temporary=tmp_path)
    )
    result = observe_native_projection(target)
    assert result == {
        "target_execution_observed": True,
        "coverage_object_observed": True,
        "coverage_files_count": 1,
        "exit_code": 1,
        "collected_count": 2,
        "records_count": 4,
        "call_identity_count": 0,
        "failed_setup_records_count": 1,
        "unexecuted_collected_count": 1,
    }
