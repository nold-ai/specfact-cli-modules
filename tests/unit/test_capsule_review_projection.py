from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.support.capsule_review_fixtures import (
    _DEPTH_FAILURE_FINDING_ROWS,
    _FIXED_ANALYZER_FINDING_ROWS,
    REPO_ROOT,
    STEP_NAME,
    _git,
    _write_public_report,
    independent_review_job,
    public_projector,
    write_public_phase_record_report,
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
    import subprocess
    import sys

    path = tmp_path / "projector.py"
    path.write_text(program)
    return subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=False, cwd=tmp_path)


def _write_preparation_fixture(tmp_path, case):
    import json

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
    import json

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
    import json

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
    import json

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
    import json

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
    import json

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
    assert json.loads(result.stdout) == _expected_review_projection(expected)
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
    import json

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
    import json

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
    import json

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
    import json

    prefix = '{"analyzer_evidence":[' + json.dumps(row) + ',{"target_execution":{"padding":"'
    middle = '","value":'
    padding = 2 * 1024 * 1024 - len((prefix + middle).encode()) - cut
    return prefix + "x" * padding + middle + token + '}}],"findings":[]}'


def _oversized_analyzer_payload(case):
    import json

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
    import json

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
    import json

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
    import json

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
    assert [json.loads(line) for line in result.stdout.splitlines()] == expected
    assert "private-token" not in result.stdout + result.stderr


def test_candidate_projection_ignores_retired_sample_frames(tmp_path):
    import json

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
                        "message": "CrossHair timed out before mandatory evidence completed. sampled_frames=argument_generation,PRIVATE_TOKEN,run_portable_pytest",
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
    import json

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
    assert rows == ([{"analyzer": "contracts", "incomplete_snapshot_sides": expected}] if expected else [])
    assert "PRIVATE_TOKEN" not in result.stdout + result.stderr


def _write_preparation_interpreter(tmp_path):
    import sys

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


@pytest.fixture
def preparation_shell(tmp_path, monkeypatch):
    import subprocess

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = "# Provisioning" + step["run"].split("# Provisioning", 1)[1].split("review_exit=0", 1)[0]
    _write_preparation_interpreter(tmp_path)

    def invoke(preparation):
        preparation_exit, report_case = preparation
        report = _write_preparation_fixture(tmp_path, "prepared" if report_case == "missing" else report_case)
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
    import json

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
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {"file": "public.py", "line": 1, "severity": "error", "category": "tool_error", "message": message}
                ]
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "-c", public_projector(job_name)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert row["failure_class"] == failure_class
    assert "PRIVATE" not in result.stdout


def test_trusted_review_budget_timeout_retains_thirty_minutes_and_fixed_exit(monkeypatch, tmp_path):
    import re
    import runpy

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
        "message": f"Test public.py::test_public_case[PRIVATE_PARAMETER::test_inner[PRIVATE_NESTED]] {outcome} during {phase}{suffix}",
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
        fault = "from pathlib import Path\ndef denied_open(*args, **kwargs):\n    raise OSError('PRIVATE_SECRET')\nPath.open = denied_open\n"
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


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_projector_crash_preserves_original_review_exit(tmp_path: Path, job_name, review_exit):
    import shlex

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    invocation = next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)
    guard = invocation.split("<<'PY'", 1)[1]
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text('{"analyzer_evidence":42}')
    program = public_projector(job_name)
    shell = (
        f"set -e\nreview_exit={review_exit}\nREVIEW_PUBLIC_EXIT=$review_exit {shlex.quote(sys.executable)} - <<'PY'{guard}\n"
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
    import shlex

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
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    invocation = next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)
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
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\nraise RuntimeError('UNTRUSTED_IMPORT')\n"
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
