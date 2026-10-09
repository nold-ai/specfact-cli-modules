from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest
import yaml

from tests.support.capsule_review_fixtures import (
    _BLOCK2_HATCH_FIXTURE,
    _TRUSTED_BOOTSTRAP_LAUNCHER,
    REPO_ROOT,
    STEP_NAME,
    _git,
    assert_block2_trace,
    assert_incomplete_preparation,
    assert_installed_review_arguments,
    create_isolated_reviewer,
    deferral_worktree,
    deferred_review_repository,
)


@pytest.mark.parametrize("gate_exit", [0, 7])
@pytest.mark.parametrize("advanced_dev", [False, True])
def test_deferred_gate_reviews_exact_staged_tree_and_propagates_failure(
    tmp_path: Path, gate_exit: int, advanced_dev: bool
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    steps = workflow["jobs"]["customer"]["steps"]
    step = next((item for item in steps if item.get("name") == STEP_NAME), None)
    assert step is not None, "No blocking candidate commit review runs in hosted Linux CI"
    assert step["if"] == "github.event_name == 'pull_request' && matrix.python == '3.12'"
    assert not step.get("continue-on-error", False)
    assert steps.index(step) > next(
        i for i, item in enumerate(steps) if item.get("name", "").startswith("Allow user namespaces")
    )
    repository, base, head = deferred_review_repository(tmp_path, advanced_dev)
    customer = tmp_path / "customer"
    (customer / "cache").mkdir(parents=True)
    venv.create(customer / "venv", with_pip=False)
    environment = os.environ | {
        "CUSTOMER_ROOT": str(customer),
        "GITHUB_WORKSPACE": str(repository),
        "CANDIDATE_HEAD": head,
        "CANDIDATE_BASE": base,
        "FIXTURE_GATE_EXIT": str(gate_exit),
        "GITHUB_TOKEN": "fixture-unused",
        "GH_TOKEN": "fixture-unused",
    }
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=repository, env=environment, capture_output=True, text=True, check=False
    )
    assert result.returncode == gate_exit, result.stdout + result.stderr
    from specfact_code_review.run.runtime_discovery import discover_project

    plan = discover_project(REPO_ROOT, config_path=customer / "commit-review-project.toml")
    assert (plan.manager, plan.environment) == ("hatch", "default")
    assert not list((customer / "cache").iterdir())
    assert _git(repository, "rev-parse", "HEAD") == head
    assert not _git(repository, "status", "--porcelain")


@pytest.mark.parametrize(
    "scenario",
    [
        ("Darwin", "", "github-linux", "specfact-code-review", False, True, 0),
        ("Darwin", "", "github-linux", "specfact-code-review", False, False, 1),
        ("Darwin", "", "github-linux", "specfact-code-review", False, "unstaged_restore", 1),
        ("Darwin", "true", "github-linux", "specfact-code-review", False, True, 1),
        ("Linux", "", "github-linux", "specfact-code-review", False, True, 1),
        ("Darwin", "", "invalid", "specfact-code-review", False, True, 1),
        ("Darwin", "", "github-linux", "specfact-project", False, True, 1),
        ("Darwin", "", "github-linux", "specfact-project", True, True, 1),
    ],
)
def test_narrow_local_deferral_retains_block2_and_cannot_run_in_ci(tmp_path: Path, scenario) -> None:
    platform, ci, deferral, _bundle, _advanced_dev, _independent_review, expected = scenario
    worktree = deferral_worktree(tmp_path, scenario)
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    recipe = script + _BLOCK2_HATCH_FIXTURE
    environment = os.environ | {
        "FIXTURE_PLATFORM": platform,
        "FIXTURE_CALLS": str(calls),
        "GITHUB_ACTIONS": ci,
        "CI": ci,
        "SPECFACT_CODE_REVIEW_DEFER_TO_CI": deferral,
    }
    result = subprocess.run(
        ["bash", "-c", recipe], cwd=worktree, env=environment, capture_output=True, text=True, check=False
    )
    assert result.returncode == expected, result.stdout + result.stderr
    invoked = calls.read_text()
    assert_block2_trace(invoked, expected, result.stderr)


@pytest.mark.parametrize(
    "review_exit,preparation_status,fixture_reason",
    [
        (0, "PASS", "policy_parse_failure"),
        (2, "PASS", "policy_parse_failure"),
        (7, "PASS", "policy_parse_failure"),
        (0, "UNKNOWN", "policy_parse_failure"),
        (0, "UNKNOWN", "private/path\nsecret"),
    ],
)
def test_isolated_reviewer_preloads_trusted_code_and_never_accepts_incomplete_preparation(
    tmp_path: Path, review_exit: int, preparation_status: str, fixture_reason: str
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    job = workflow["jobs"]["independent-review"]
    step = next(
        item
        for item in job["steps"]
        if item.get("name") == "Prepare and review through the authenticated installed controller"
    )
    trusted, environment = create_isolated_reviewer(tmp_path, (review_exit, preparation_status, fixture_reason))
    result = subprocess.run(["bash", "-c", step["run"]], env=environment, text=True, capture_output=True, check=False)
    expected = review_exit if preparation_status == "PASS" else 1
    assert result.returncode == expected, result.stdout + result.stderr
    assert (trusted / "preloaded").exists()
    if preparation_status != "PASS":
        assert_incomplete_preparation(trusted, result, fixture_reason)
    else:
        assert_installed_review_arguments(trusted)


def test_trusted_bootstrap_cannot_import_candidate_venv_module(tmp_path: Path) -> None:
    import textwrap

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = workflow["jobs"]["independent-review"]["steps"][2]
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    marker = tmp_path / "host-code-executed"
    (candidate / "venv.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise SystemExit(9)\n"
    )
    launcher_dir = tmp_path / "launcher"
    launcher_dir.mkdir()
    launcher = launcher_dir / "python"
    launcher.write_text(f"#!{sys.executable}\n" + textwrap.dedent(_TRUSTED_BOOTSTRAP_LAUNCHER))
    launcher.chmod(0o700)
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    environment = os.environ | {
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_ENV": str(tmp_path / "job.env"),
        "PATH": str(launcher_dir) + os.pathsep + os.environ["PATH"],
    }
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=candidate, env=environment, text=True, capture_output=True, check=False
    )
    assert not marker.exists(), "Candidate code executed on the trusted bootstrap host"
    assert result.returncode == 0, result.stdout + result.stderr


def test_deferred_host_fixture_does_not_alias_managed_caller_python(tmp_path: Path, monkeypatch):
    managed = tmp_path / "managed-python"
    managed.write_text("#!/bin/sh\nexit 78\n")
    managed.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(managed))
    test_deferred_gate_reviews_exact_staged_tree_and_propagates_failure(tmp_path, 0, False)


@pytest.mark.parametrize("review_exit", [0, 2, 7])
def test_independent_no_impact_still_reviews_and_cleans_resolution(tmp_path: Path, review_exit: int) -> None:
    from tests.support.capsule_review_fixtures import independent_review_job

    step = next(item for item in independent_review_job()["steps"] if item.get("id") == "independent_review")
    trusted, environment = create_isolated_reviewer(tmp_path, (review_exit, "NOT_APPLICABLE", "no_governed_impact"))
    result = subprocess.run(["bash", "-c", step["run"]], env=environment, text=True, capture_output=True, check=False)
    assert result.returncode == review_exit, result.stdout + result.stderr
    assert (trusted / "preloaded").exists()
    assert (trusted / "cleaned").exists()
    assert_installed_review_arguments(trusted, prepared=False)


@pytest.mark.parametrize(
    "status,reason,selected,scope_exit",
    [
        ("NOT_APPLICABLE", "private-reason", [], 0),
        ("NOT_APPLICABLE", "no_governed_impact", ["governed.py"], 0),
        ("NOT_APPLICABLE", "no_governed_impact", [], 7),
        ("UNKNOWN", "no_governed_impact", [], 0),
        ("FAIL", "no_governed_impact", [], 0),
    ],
)
def test_independent_invalid_no_impact_stops_before_review(
    tmp_path: Path, status, reason, selected, scope_exit
) -> None:
    from tests.support.capsule_review_fixtures import independent_review_job

    step = next(item for item in independent_review_job()["steps"] if item.get("id") == "independent_review")
    trusted, environment = create_isolated_reviewer(
        tmp_path, (0, status, reason), selected_paths=selected, scope_exit=scope_exit
    )
    result = subprocess.run(["bash", "-c", step["run"]], env=environment, text=True, capture_output=True, check=False)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not (trusted / "argv.json").exists()
    assert not (trusted / "prepared").exists()
    assert (trusted / "cleaned").exists()
    assert "private-reason" not in result.stdout
