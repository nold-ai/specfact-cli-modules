from __future__ import annotations

import pytest
import yaml

from tests.support.capsule_review_fixtures import REPO_ROOT, STEP_NAME, independent_review_job


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
    assert "--version 0.51.0" in recipe
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
    assert "timeout=300" in recipe and "timeout=1800" in recipe
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
    return subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=False)


def _write_preparation_fixture(tmp_path, case):
    import json

    descriptor = tmp_path / "descriptor.json"
    descriptor.write_text("{}")
    payload = {"runtimes": {side: {"descriptor": str(descriptor)} for side in ("base", "head")}}
    if case == "not_applicable":
        payload = {"status": "NOT_APPLICABLE", "runtimes": {}}
    elif case == "missing_base":
        payload["runtimes"].pop("base")
    report = tmp_path / "preparation.private.json"
    report.write_text("not-json/private" if case == "invalid" else json.dumps(payload))
    return report


@pytest.mark.parametrize(
    "case,expected",
    [
        ("prepared", (0, "PREPARED", True, True)),
        ("not_applicable", (1, "INCOMPLETE", False, False)),
        ("missing_base", (1, "INCOMPLETE", False, True)),
        ("invalid", (1, "INCOMPLETE", False, False)),
    ],
)
def test_successful_index_preparation_requires_both_descriptors(tmp_path, monkeypatch, case, expected):
    import json

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    assert "PY_PREPARATION" in step["run"]
    program = step["run"].split("<<'PY_PREPARATION'\n", 1)[1].split("\nPY_PREPARATION", 1)[0]
    monkeypatch.setenv("PREPARATION_REPORT", str(_write_preparation_fixture(tmp_path, case)))
    result = _run_projector(tmp_path, program)
    code, status, base, head = expected
    assert result.returncode == code
    assert json.loads(result.stdout) == {
        "status": status,
        "phase": "index_preparation",
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
    assert public.pop("phase") == "namespace_audit"
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
