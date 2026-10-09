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
        ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 0),
        ("Darwin", "", "github-linux", "tests/unit/test_native_broker_cleanup.py", False, True, 0),
        ("Darwin", "", "github-linux", "tests/native/proof_native_canonical_path.py", False, True, 0),
        (
            "Darwin",
            "",
            "github-linux",
            "tests/unit/specfact_code_review/run/test_native_project_runtime.py",
            False,
            True,
            0,
        ),
        ("Darwin", "", "github-linux", "tests/unit/specfact_project/unrelated.py", False, True, 1),
        ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, "missing_trigger", 1),
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
    assert_block2_trace(invoked, expected, result.stderr, prompt_required=not _bundle.startswith("tests/"))


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


@pytest.mark.parametrize(
    "mutation",
    [
        "self_trigger",
        "missing_job",
        "disabled_job",
        "wrong_filter",
        "wrong_target",
        "nonblocking",
        "decoy_rule",
        "missing_filter_output",
        "conditional_filter",
        "negated_filter",
        "wrong_detection",
        "filter_every",
        "malformed",
    ],
)
def test_local_deferral_rejects_unscheduled_indexed_customer_review(tmp_path: Path, mutation: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    source = path.read_text()
    replacements = {
        "filter_every": (
            "        with:\n          filters: |",
            "        with:\n          predicate-quantifier: every\n          filters: |",
        ),
        "self_trigger": ('              - ".github/workflows/pr-orchestrator.yml"\n', ""),
        "disabled_job": (
            "if: github.event_name == 'pull_request' && needs.changes.outputs.capsule_changed == 'true'",
            "if: false",
        ),
        "wrong_filter": ("needs.changes.outputs.capsule_changed == 'true'", "needs.changes.outputs.other == 'true'"),
        "wrong_target": (
            "uses: ./.github/workflows/capsule-customer-execution.yml",
            "uses: ./.github/workflows/docs.yml",
        ),
        "nonblocking": ("  customer-capsules:\n", "  customer-capsules:\n    continue-on-error: true\n"),
        "decoy_rule": ('              - "tests/native/**"\n', ""),
        "missing_filter_output": ("capsule_changed: ${{ steps.filter.outputs.capsule }}", "capsule_changed: false"),
        "conditional_filter": ("        id: filter", "        if: false\n        id: filter"),
        "negated_filter": ("            capsule:\n", '            capsule:\n              - "!tests/native/**"\n'),
        "wrong_detection": ("  changes:\n", "  changes:\n    if: false\n"),
    }
    if mutation in replacements:
        source = source.replace(*replacements[mutation])
    if mutation == "self_trigger":
        # Only the orchestrator qualifies; unrelated code cannot schedule review.
        _git(worktree, "reset", "HEAD", "tests/native/proof_macos_native_broker_wait.py")
        unrelated = worktree / "tools/unrelated.py"
        unrelated.parent.mkdir()
        unrelated.write_text("value = 1\n")
    elif mutation == "missing_job":
        start = source.index("\n  customer-capsules:")
        end = source.index("\n  quality:", start)
        source = source[:start] + source[end:]
    elif mutation == "decoy_rule":
        source += '\n# - "tests/native/**"\n'
    elif mutation == "malformed":
        source = "jobs: [unterminated"
    path.write_text(source)
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    result = subprocess.run(
        ["bash", "-c", script + _BLOCK2_HATCH_FIXTURE],
        cwd=worktree,
        env=os.environ
        | {
            "FIXTURE_PLATFORM": "Darwin",
            "FIXTURE_CALLS": str(calls),
            "CI": "",
            "GITHUB_ACTIONS": "",
            "SPECFACT_CODE_REVIEW_DEFER_TO_CI": "github-linux",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Capsule review deferral" in result.stderr
    assert "DEFERRED" not in result.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate_step",
        "candidate_job",
        "candidate_condition",
        "independent_job",
        "independent_step",
        "independent_condition",
    ],
)
def test_local_deferral_rejects_nonblocking_reusable_review(tmp_path: Path, mutation: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/capsule-customer-execution.yml"
    document = yaml.safe_load(path.read_text())
    document["on"] = document.pop(True)
    job = document["jobs"]["independent-review" if mutation.startswith("independent") else "customer"]
    if mutation.endswith("job"):
        job["continue-on-error"] = True
    else:
        step = next(
            item
            for item in job["steps"]
            if item.get("id") == ("independent_review" if mutation.startswith("independent") else "deferred_review")
        )
        if mutation.endswith("condition"):
            step["if"] = False
        else:
            step["continue-on-error"] = True
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    result = subprocess.run(
        ["bash", "-c", script + _BLOCK2_HATCH_FIXTURE],
        cwd=worktree,
        env=os.environ
        | {
            "FIXTURE_PLATFORM": "Darwin",
            "FIXTURE_CALLS": str(calls),
            "CI": "",
            "GITHUB_ACTIONS": "",
            "SPECFACT_CODE_REVIEW_DEFER_TO_CI": "github-linux",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Capsule review deferral" in result.stderr
    assert "DEFERRED" not in result.stderr


def _assert_local_deferral(worktree: Path, calls: Path, expected: int) -> None:
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    result = subprocess.run(
        ["bash", "-c", script + _BLOCK2_HATCH_FIXTURE],
        cwd=worktree,
        env=os.environ
        | {
            "FIXTURE_PLATFORM": "Darwin",
            "FIXTURE_CALLS": str(calls),
            "CI": "",
            "GITHUB_ACTIONS": "",
            "SPECFACT_CODE_REVIEW_DEFER_TO_CI": "github-linux",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    assert_block2_trace(calls.read_text(), expected, result.stderr, prompt_required=False)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_pr",
        "literal_true",
        "excluded_dev",
        "excluded_main",
        "excluded_paths",
        "selected_paths",
        "closed_only",
        "extra_boolean_root",
        "duplicate_on",
    ],
)
def test_deferral_requires_effective_literal_pr_event(tmp_path: Path, mutation: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    document = yaml.safe_load(path.read_text())
    events = document.pop(True)
    document["on"] = events
    if mutation == "literal_true":
        document[True] = document.pop("on")
    elif mutation == "missing_pr":
        events.pop("pull_request")
    elif mutation in {"extra_boolean_root", "duplicate_on"}:
        document[True] = events if mutation == "extra_boolean_root" else {}
    else:
        changes = {
            "excluded_dev": {"branches": ["main"]},
            "excluded_main": {"branches": ["dev"]},
            "excluded_paths": {"paths-ignore": ["**"]},
            "selected_paths": {"paths": ["docs/**"]},
            "closed_only": {"types": ["closed"]},
        }
        events["pull_request"].update(changes[mutation])
    serialized = yaml.safe_dump(document, sort_keys=False)
    if mutation == "duplicate_on":
        serialized = (
            serialized.replace("true: {}\n", "")
            + "\non:\n"
            + '  pull_request:\n    branches: [main, dev]\n    paths-ignore: ["**/*.md", "docs/**"]\n'
        )
    path.write_text(serialized)
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize(
    "unrelated",
    [
        "tests/unit/specfact_project/unrelated.py",
        "tools/unrelated.py",
        "packages/specfact-project/src/unrelated.py",
        "openspec/changes/unrelated/spec.md",
    ],
)
def test_deferral_rejects_mixed_unrelated_reviewable_paths(tmp_path: Path, unrelated: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / unrelated
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("unrelated = 1\n")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize(
    "mutation",
    [
        "literal_true",
        "excluded_cp312",
        "nonlinux",
        "candidate_echo",
        "independent_echo",
        "early_exit",
        "root_environment",
    ],
)
def test_deferral_requires_integrated_review_execution_contract(tmp_path: Path, mutation: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/capsule-customer-execution.yml"
    document = yaml.safe_load(path.read_text())
    document["on"] = document.pop(True)
    customer = document["jobs"]["customer"]
    commands = {
        "candidate_echo": ("customer", "deferred_review"),
        "independent_echo": ("independent-review", "independent_review"),
        "early_exit": ("customer", "deferred_review"),
    }
    if mutation in commands:
        job_name, identity = commands[mutation]
        job = document["jobs"][job_name]
        step = next(step for step in job["steps"] if step.get("id") == identity)
        step["run"] = "exit 0\n" + step["run"] if mutation == "early_exit" else "echo skipped"
    elif mutation == "literal_true":
        document[True] = document.pop("on")
    elif mutation == "excluded_cp312":
        customer["strategy"]["matrix"]["exclude"] = [{"python": "3.12"}]
    elif mutation == "nonlinux":
        customer["runs-on"] = "macos-14"
    else:
        document["env"] = {"SPECFACT_CODE_REVIEW_ENFORCEMENT": "none"}
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize("control", ["formatting", "unrelated_generated_docs"])
def test_deferral_retains_exact_review_contract_controls(tmp_path: Path, control: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 0)
    worktree = deferral_worktree(tmp_path, scenario)
    if control == "formatting":
        path = worktree / ".github/workflows/capsule-customer-execution.yml"
        document = yaml.safe_load(path.read_text())
        document["on"] = document.pop(True)
        path.write_text(yaml.safe_dump(document, sort_keys=False))
    else:
        path = worktree / "docs/generated.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text("Generated command reference.\n")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 0)


@pytest.mark.parametrize("event", [False, 0, [], ""])
def test_deferral_rejects_falsey_malformed_pr_events(tmp_path: Path, event: object) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    document = yaml.safe_load(path.read_text())
    document["on"] = document.pop(True)
    document["on"]["pull_request"] = event
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)
