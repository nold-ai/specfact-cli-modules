from __future__ import annotations

import json
import os
import shlex
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
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text(encoding="utf-8")
    )
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
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text(encoding="utf-8").rsplit('main "$@"', 1)[0]
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
    invoked = calls.read_text(encoding="utf-8")
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
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text(encoding="utf-8")
    )
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

    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text(encoding="utf-8")
    )
    step = workflow["jobs"]["independent-review"]["steps"][2]
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    marker = tmp_path / "host-code-executed"
    (candidate / "venv.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise SystemExit(9)\n", encoding="utf-8"
    )
    launcher_dir = tmp_path / "launcher"
    launcher_dir.mkdir()
    launcher = launcher_dir / "python"
    launcher.write_text(f"#!{sys.executable}\n" + textwrap.dedent(_TRUSTED_BOOTSTRAP_LAUNCHER), encoding="utf-8")
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
    managed.write_text("#!/bin/sh\nexit 78\n", encoding="utf-8")
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
    source = path.read_text(encoding="utf-8")
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
    source = _indexed_customer_source_variant(worktree, source, mutation)
    path.write_text(source, encoding="utf-8")
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text(encoding="utf-8").rsplit('main "$@"', 1)[0]
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
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
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
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text(encoding="utf-8").rsplit('main "$@"', 1)[0]
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
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text(encoding="utf-8").rsplit('main "$@"', 1)[0]
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
    assert_block2_trace(calls.read_text(encoding="utf-8"), expected, result.stderr, prompt_required=False)


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
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
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
    path.write_text(serialized, encoding="utf-8")
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
    path.write_text("unrelated = 1\n", encoding="utf-8")
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
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    customer = document["jobs"]["customer"]
    commands = {
        "candidate_echo": ("customer", "deferred_review"),
        "independent_echo": ("independent-review", "independent_review"),
        "early_exit": ("customer", "deferred_review"),
    }
    _mutate_reusable_review_execution(document, customer, commands, mutation)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize("control", ["formatting", "detector_formatting", "unrelated_generated_docs"])
def test_deferral_retains_exact_review_contract_controls(tmp_path: Path, control: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 0)
    worktree = deferral_worktree(tmp_path, scenario)
    if control != "unrelated_generated_docs":
        filename = "pr-orchestrator.yml" if control == "detector_formatting" else "capsule-customer-execution.yml"
        path = worktree / ".github/workflows" / filename
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["on"] = document.pop(True)
        if control == "detector_formatting":
            step = next(step for step in document["jobs"]["changes"]["steps"] if step.get("id") == "filter")
            step["with"]["filters"] = "# Equivalent embedded filter formatting\n" + yaml.safe_dump(
                yaml.safe_load(step["with"]["filters"])
            )
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    else:
        path = worktree / "docs/generated.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text("Generated command reference.\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 0)


@pytest.mark.parametrize("event", [False, 0, [], ""])
def test_deferral_rejects_falsey_malformed_pr_events(tmp_path: Path, event: object) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    document["on"]["pull_request"] = event
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_runner",
        "nonlinux",
        "conditional_dependency",
        "missing_dependency",
        "empty_matrix",
        "skip_checkout",
        "wrong_checkout_ref",
        "filter_base",
        "filter_ref",
        "remove_baseline_rule",
        "duplicate_filter",
    ],
)
def test_deferral_requires_integrated_change_detector_execution(tmp_path: Path, mutation: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    changes = document["jobs"]["changes"]
    updates = {
        "nonlinux": {"runs-on": "unavailable-capsule-detector-runner"},
        "missing_dependency": {"needs": ["absent_precheck"]},
        "empty_matrix": {"strategy": {"matrix": {"include": []}}},
    }
    _mutate_detector_execution(document, changes, updates, mutation)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


def _mutate_detector_filter(changes: dict, mutation: str) -> None:
    step = next(step for step in changes["steps"] if step.get("id") == "filter")
    if mutation == "remove_baseline_rule":
        filters = yaml.safe_load(step["with"]["filters"])
        filters["capsule"].remove("registry/**")
        step["with"]["filters"] = yaml.safe_dump(filters)
    elif mutation == "duplicate_filter":
        step["with"]["filters"] = "capsule: []\n" + step["with"]["filters"]
    else:
        step["with"]["base" if mutation == "filter_base" else "ref"] = "unrelated-source"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("continue-on-error", False),
        ("runs-on", "ubuntu-latest"),
        ("steps", []),
        ("env", {}),
        ("timeout-minutes", 90),
        ("with", {"unverified_input": True}),
        ("permissions", {}),
        ("strategy", {"matrix": {"include": []}}),
        ("concurrency", {"group": "unverified-review", "cancel-in-progress": True}),
    ],
)
def test_deferral_requires_integrated_reusable_review_caller(tmp_path: Path, key: str, value: object) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    document["jobs"]["customer-capsules"][key] = value
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_dependency",
        "missing_prerequisite",
        "ignored_prerequisite",
        "skipped_prerequisite",
        "skipped_quality",
        "nonblocking_quality",
        "empty_matrix",
        "root_environment",
        "root_defaults",
        "root_permissions",
        "root_concurrency",
    ],
)
def test_deferral_requires_integrated_quality_consumer(tmp_path: Path, mutation: str) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/pr-orchestrator.yml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    quality = document["jobs"]["quality"]
    mutations = {
        "missing_dependency": lambda: quality["needs"].remove("customer-capsules"),
        "missing_prerequisite": lambda: quality["steps"].pop(0),
        "ignored_prerequisite": lambda: quality["steps"][0].update(run="exit 0"),
        "skipped_prerequisite": lambda: quality["steps"][0].update(**{"if": False}),
        "skipped_quality": lambda: quality.update(**{"if": False}),
        "nonblocking_quality": lambda: quality.update(**{"continue-on-error": True}),
        "empty_matrix": lambda: quality.update(strategy={"matrix": {"include": []}}),
    }
    mutations.get(mutation, lambda: _mutate_orchestration_execution(document, mutation))()
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


def _mutate_orchestration_execution(document: dict, mutation: str) -> None:
    updates = {
        "root_environment": ("env", {"CAPSULE_REQUIRED": "false"}),
        "root_defaults": ("defaults", {"run": {"working-directory": "unavailable-directory"}}),
        "root_permissions": ("permissions", {}),
        "root_concurrency": ("concurrency", {"group": "unverified-review", "cancel-in-progress": True}),
    }
    key, value = updates[mutation]
    document[key] = value


@pytest.mark.parametrize("budget,expected", [(1800, 0), (300, 1), (0, 1), (3600, 1)])
def test_deferral_admits_only_owner_approved_budget(tmp_path: Path, budget: int, expected: int) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, expected)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/capsule-customer-execution.yml"
    old = "subprocess.run(sys.argv[1:],timeout=300,check=False)"
    new = "subprocess.run(sys.argv[1:],timeout=1800,check=False)"
    current = path.read_text(encoding="utf-8")
    assert old in current or new in current
    prefix, suffix = current.rsplit(new, 1)
    integrated = prefix + old + suffix
    _git(worktree, "checkout", "origin/dev")
    path.write_text(integrated, encoding="utf-8")
    _git(worktree, "add", str(path))
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture integrated review budget")
    _git(worktree, "update-ref", "refs/remotes/origin/dev", "HEAD")
    _git(worktree, "checkout", "codex/fixture")
    _git(worktree, "merge", "--ff-only", "origin/dev")
    (worktree / "tests/native/proof_macos_native_broker_wait.py").write_text(
        "candidate budget proof\n", encoding="utf-8"
    )
    (worktree / "openspec/changes/code-review-native-platform-execution/spec.md").write_text(
        "budget candidate\n", encoding="utf-8"
    )
    path.write_text(
        integrated.replace(old, f"subprocess.run(sys.argv[1:],timeout={budget},check=False)"), encoding="utf-8"
    )
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", expected)


@pytest.mark.parametrize("job_minutes,expected", [(75, 0), (45, 1), (60, 1), (90, 1)])
def test_indexed_deferral_admits_only_complete_approved_job_budget(
    tmp_path: Path, job_minutes: int, expected: int
) -> None:
    scenario = ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, expected)
    worktree = deferral_worktree(tmp_path, scenario)
    path = worktree / ".github/workflows/capsule-customer-execution.yml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    document["jobs"]["independent-review"]["timeout-minutes"] = 45
    integrated = yaml.safe_dump(document, sort_keys=False)
    _git(worktree, "checkout", "origin/dev")
    path.write_text(integrated, encoding="utf-8")
    _git(worktree, "add", str(path))
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture integrated independent job budget")
    _git(worktree, "update-ref", "refs/remotes/origin/dev", "HEAD")
    _git(worktree, "checkout", "codex/fixture")
    _git(worktree, "merge", "--ff-only", "origin/dev")
    (worktree / "tests/native/proof_macos_native_broker_wait.py").write_text(
        "candidate job budget proof\n", encoding="utf-8"
    )
    (worktree / "openspec/changes/code-review-native-platform-execution/spec.md").write_text(
        "job budget candidate\n", encoding="utf-8"
    )
    document["jobs"]["independent-review"]["timeout-minutes"] = job_minutes
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", expected)


_PINNED_VALIDATOR_COMMIT = "c65a41e61a6b4e61e8dd2b69526a1cfc8650b3ad"
_PINNED_VALIDATOR_BLOB = "cc549b5bbd945b64d055afe111bcaeeb059d585a"


def _tampered_deferral_candidate(tmp_path, *, staged_checker, missing_caller, bootstrap=False):
    worktree = deferral_worktree(
        tmp_path,
        ("Darwin", "", "github-linux", "tests/native/proof_native_canonical_path.py", False, True, 0),
        validator_present=not bootstrap,
    )
    marker = tmp_path / "candidate-validator-executed"
    checker = worktree / "scripts/check_capsule_deferral.py"
    checker.parent.mkdir(exist_ok=True)
    checker.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8")
    if staged_checker:
        _git(worktree, "add", "scripts/check_capsule_deferral.py")
    if missing_caller:
        path = worktree / ".github/workflows/pr-orchestrator.yml"
        workflow = yaml.safe_load(path.read_text())
        del workflow["jobs"]["customer-capsules"]
        path.write_text(yaml.safe_dump(workflow))
        _git(worktree, "add", str(path))
    return worktree, marker


@pytest.mark.parametrize("staged_checker", [False, True])
@pytest.mark.parametrize("missing_caller", [False, True])
def test_local_deferral_never_executes_candidate_validator(tmp_path, staged_checker, missing_caller):
    worktree, marker = _tampered_deferral_candidate(
        tmp_path, staged_checker=staged_checker, missing_caller=missing_caller
    )
    _assert_local_deferral(worktree, tmp_path / "calls", int(missing_caller))
    assert not marker.exists(), "Candidate checker bytes executed on the hook host"


def _advance_validator_authority(tmp_path, mode):
    repository = tmp_path / "repository"
    checker = repository / "scripts/check_capsule_deferral.py"
    if mode == "integrated_reject":
        checker.write_text("raise SystemExit(9)\n", encoding="utf-8")
    elif checker.exists():
        checker.unlink()
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-qm", "fixture integrated authority")
    integrated = _git(repository, "rev-parse", "HEAD")
    if mode != "missing_object":
        # Local transport from the full-history checkout; no network, candidate ref or synthesized authority.
        _git(repository, "fetch", "--quiet", str(REPO_ROOT), _PINNED_VALIDATOR_COMMIT)
        assert _git(repository, "rev-parse", f"{_PINNED_VALIDATOR_COMMIT}:scripts/check_capsule_deferral.py") == (
            _PINNED_VALIDATOR_BLOB
        )
    if mode == "expired":
        integrated = _git(
            repository,
            "commit-tree",
            _git(repository, "rev-parse", "HEAD^{tree}"),
            "-p",
            integrated,
            "-p",
            _PINNED_VALIDATOR_COMMIT,
            "-m",
            "fixture integrated bootstrap ancestor",
        )
    if mode == "replacement":
        _git(repository, "replace", _PINNED_VALIDATOR_COMMIT, integrated)
    _git(repository, "update-ref", "refs/remotes/origin/dev", integrated)
    if mode == "shallow":
        # Retain a common fixture merge-base while deliberately withholding older dev history.
        (repository / ".git/shallow").write_text(_git(repository, "rev-parse", "HEAD^") + "\n")


@pytest.mark.parametrize(
    "mode,missing_caller,expected",
    [
        ("bootstrap", False, 0),
        ("bootstrap", True, 1),
        ("replacement", False, 0),
        ("replacement", True, 1),
        ("missing_object", False, 1),
        ("shallow", False, 1),
        ("expired", False, 1),
        ("squash_deleted", False, 1),
        ("integrated_reject", False, 1),
    ],
)
def test_local_deferral_pinned_authority_lifecycle(tmp_path, monkeypatch, mode, missing_caller, expected):
    worktree, marker = _tampered_deferral_candidate(
        tmp_path,
        staged_checker=True,
        missing_caller=missing_caller,
        bootstrap=mode not in {"integrated_reject", "squash_deleted"},
    )
    _advance_validator_authority(tmp_path, mode)
    private_tmp = tmp_path / "validator-temporaries"
    private_tmp.mkdir(mode=0o700)
    monkeypatch.setenv("TMPDIR", str(private_tmp))
    _assert_local_deferral(worktree, tmp_path / "calls", expected)
    assert not marker.exists(), "Candidate checker executed instead of the trusted authority"
    assert not list(private_tmp.iterdir()), "Extracted trusted checker leaked after validation"


@pytest.mark.parametrize("missing_caller", [False, True])
@pytest.mark.parametrize("missing_interpreter", [False, True])
def test_local_deferral_ignores_real_candidate_hatch_python_alias(tmp_path, missing_caller, missing_interpreter):
    worktree, candidate_marker = _tampered_deferral_candidate(
        tmp_path, staged_checker=True, missing_caller=missing_caller
    )
    alias_marker = tmp_path / "candidate-hatch-alias-executed"
    config = worktree / "pyproject.toml"
    command = f"sh -c 'touch {shlex.quote(str(alias_marker))}; exit 0' --"
    config.write_text(
        '[project]\nname="owned-hatch-alias-proof"\nversion="0.0.0"\n'
        '[tool.hatch.envs.default]\ndetached=true\npath=".hatch-alias-env"\n'
        "[tool.hatch.envs.default.scripts]\npython=" + json.dumps(command) + "\n"
    )
    _git(worktree, "add", "pyproject.toml")
    if missing_interpreter:
        (worktree / ".venv").unlink()
    shell = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    paths = _git(worktree, "diff", "--cached", "--name-only", "origin/dev")
    capsule_paths = "\n".join(path for path in paths.splitlines() if not path.startswith("openspec/"))
    result = subprocess.run(
        [
            "bash",
            "-c",
            shell + '\nrun_trusted_capsule_deferral "$@"',
            "owned-hatch-proof",
            capsule_paths,
            paths,
            "origin/dev",
        ],
        cwd=worktree,
        env=os.environ | {"HATCH_ENV": "default"},
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    expected = 127 if missing_interpreter else int(missing_caller)
    assert result.returncode == expected, result.stderr
    assert not alias_marker.exists(), "Candidate Hatch script replaced trusted validation"
    assert not candidate_marker.exists(), "Candidate checker replaced trusted validation"


def _advance_deferral_workflow_contract(tmp_path: Path, mutation: str) -> Path:
    repository = tmp_path / "repository"
    filename = "capsule-customer-execution.yml" if mutation == "reusable" else "pr-orchestrator.yml"
    path = repository / ".github/workflows" / filename
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["on"] = document.pop(True)
    enforcement = {"SPECFACT_CODE_REVIEW_ENFORCEMENT": "full"}
    _mutate_advanced_dev_contract(document, enforcement, mutation)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    _git(repository, "add", str(path))
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture current integrated workflow contract")
    _git(repository, "update-ref", "refs/remotes/origin/dev", "HEAD")
    return path


@pytest.mark.parametrize("mutation", ["detector", "caller", "reusable", "quality", "root_environment"])
@pytest.mark.parametrize("current_index", [False, True])
def test_behind_dev_deferral_binds_current_integrated_contract(
    tmp_path: Path, mutation: str, current_index: bool
) -> None:
    worktree = deferral_worktree(
        tmp_path,
        ("Darwin", "", "github-linux", "tests/native/proof_native_canonical_path.py", False, True, 0),
    )
    original_base = _git(worktree, "merge-base", "HEAD", "origin/dev")
    integrated_path = _advance_deferral_workflow_contract(tmp_path, mutation)
    assert _git(worktree, "merge-base", "HEAD", "origin/dev") == original_base
    assert _git(worktree, "rev-parse", "origin/dev") != original_base
    if current_index:
        candidate_path = worktree / ".github/workflows" / integrated_path.name
        candidate_path.write_bytes(integrated_path.read_bytes())
        _git(worktree, "add", str(candidate_path))
    _assert_local_deferral(worktree, tmp_path / "calls", 0 if current_index else 1)


def _indexed_customer_source_variant(worktree: Path, source: str, mutation: str) -> str:
    if mutation == "self_trigger":
        # Only the orchestrator qualifies; unrelated code cannot schedule review.
        _git(worktree, "reset", "HEAD", "tests/native/proof_macos_native_broker_wait.py")
        unrelated = worktree / "tools/unrelated.py"
        unrelated.parent.mkdir()
        unrelated.write_text("value = 1\n", encoding="utf-8")
        return source
    if mutation == "missing_job":
        start = source.index("\n  customer-capsules:")
        end = source.index("\n  quality:", start)
        return source[:start] + source[end:]
    if mutation == "decoy_rule":
        source += '\n# - "tests/native/**"\n'
        return source
    if mutation == "malformed":
        return "jobs: [unterminated"
    return source


def _mutate_reusable_review_execution(document: dict, customer: dict, commands: dict, mutation: str) -> None:
    if mutation in commands:
        job_name, identity = commands[mutation]
        job = document["jobs"][job_name]
        step = next(step for step in job["steps"] if step.get("id") == identity)
        step["run"] = "exit 0\n" + step["run"] if mutation == "early_exit" else "echo skipped"
        return
    if mutation == "literal_true":
        document[True] = document.pop("on")
        return
    if mutation == "excluded_cp312":
        customer["strategy"]["matrix"]["exclude"] = [{"python": "3.12"}]
        return
    if mutation == "nonlinux":
        customer["runs-on"] = "macos-14"
        return
    document["env"] = {"SPECFACT_CODE_REVIEW_ENFORCEMENT": "none"}


def _mutate_detector_execution(document: dict, changes: dict, updates: dict, mutation: str) -> None:
    if mutation in updates:
        changes.update(updates[mutation])
        return
    if mutation == "missing_runner":
        changes.pop("runs-on")
        return
    if mutation == "conditional_dependency":
        changes["needs"] = ["precheck"]
        document["jobs"]["precheck"] = {"runs-on": "ubuntu-latest", "if": False, "steps": [{"run": "exit 0"}]}
        return
    if mutation == "skip_checkout":
        changes["steps"][0]["if"] = False
        return
    if mutation == "wrong_checkout_ref":
        changes["steps"][0]["with"]["ref"] = "unrelated-source"
        return
    _mutate_detector_filter(changes, mutation)


def _mutate_advanced_dev_contract(document: dict, enforcement: dict, mutation: str) -> None:
    if mutation == "detector":
        document["jobs"]["changes"]["env"] = enforcement
        return
    if mutation == "caller":
        document["jobs"]["customer-capsules"]["secrets"] = "inherit"
        return
    if mutation == "reusable":
        document["jobs"]["independent-review"]["env"] = enforcement
        return
    if mutation == "quality":
        document["jobs"]["quality"]["env"] = enforcement
        return
    if mutation == "root_environment":
        document["env"] = enforcement
        return


@pytest.mark.parametrize("suffix", ["\n", "\r", "\t", '"', "\\", "\u2028"])
def test_deferral_rejects_unrelated_quoted_pathnames(tmp_path: Path, suffix: str) -> None:
    worktree = deferral_worktree(
        tmp_path, ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 1)
    )
    path = worktree / ("tests/unit/unrelated" + suffix + ".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("unrelated = 1\n")
    _git(worktree, "add", ".")
    _assert_local_deferral(worktree, tmp_path / "calls", 1)


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "disabled",
        "filtered",
        "nonblocking",
        "live-index",
        "live-dev-ref",
        "checker-decoy",
        "payload",
        "mixed",
        "committed-invalid-live-valid",
    ],
)
def test_committed_ci_check_uses_final_tree_and_preserves_caller(tmp_path: Path, case: str) -> None:
    worktree, base, head, workflow = _prepare_committed_ci_subject(tmp_path, case)
    before = (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain"), workflow.read_bytes())
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    result = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "scripts/owner_commit_entry.py"), "--head", head, "--base", base],
        cwd=worktree,
        env=os.environ | {"TMPDIR": str(scratch)},
        text=True,
        capture_output=True,
        check=False,
    )
    rejected = case in {"disabled", "filtered", "nonblocking", "mixed", "committed-invalid-live-valid"}
    assert result.returncode == (1 if rejected else 0), result.stdout + result.stderr
    assert _git(worktree, "rev-parse", "HEAD") == head
    assert (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain"), workflow.read_bytes()) == before
    assert not list(scratch.iterdir())
    if result.returncode == 0:
        assert head in result.stderr
    else:
        assert "committed scheduling rejected" in result.stderr


@pytest.mark.parametrize("case", ["valid", "missing-bootstrap", "shallow", "squash-deleted"])
def test_committed_ci_check_retains_actual_bootstrap_expiry(tmp_path: Path, case: str) -> None:
    worktree = deferral_worktree(
        tmp_path,
        ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 0),
        validator_present=False,
    )
    if case != "missing-bootstrap":
        _git(worktree, "fetch", "--no-tags", str(REPO_ROOT), "c65a41e61a6b4e61e8dd2b69526a1cfc8650b3ad")
    base = _git(worktree, "rev-parse", "origin/dev")
    if case == "squash-deleted":
        repository = tmp_path / "repository"
        checker = repository / "scripts/check_capsule_deferral.py"
        checker.write_text("raise SystemExit(0)\n")
        _git(repository, "add", ".")
        _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture checker history")
        checker.unlink()
        _git(repository, "add", ".")
        _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture checker removal")
        base = _git(repository, "rev-parse", "HEAD")
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture committed scheduling")
    head = _git(worktree, "rev-parse", "HEAD")
    if case == "shallow":
        common = Path(_git(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        (common / "shallow").write_text(base + "\n")
    result = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "scripts/owner_commit_entry.py"), "--head", head, "--base", base],
        cwd=worktree,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == (0 if case == "valid" else 1), result.stdout + result.stderr
    assert _git(worktree, "rev-parse", "HEAD") == head


def test_committed_ci_check_non_capsule_delta_keeps_ordinary_gates(tmp_path: Path) -> None:
    worktree = deferral_worktree(
        tmp_path, ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 0)
    )
    base = _git(worktree, "rev-parse", "origin/dev")
    _git(worktree, "read-tree", base)
    path = worktree / "llms.txt"
    path.write_text("ordinary docs change\n")
    _git(worktree, "add", "llms.txt")
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture ordinary change")
    head = _git(worktree, "rev-parse", "HEAD")
    result = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "scripts/owner_commit_entry.py"), "--head", head, "--base", base],
        cwd=worktree,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no capsule delta" in result.stderr


def _prepare_committed_ci_subject(tmp_path: Path, case: str) -> tuple[Path, str, str, Path]:
    worktree = deferral_worktree(
        tmp_path, ("Darwin", "", "github-linux", "tests/native/proof_macos_native_broker_wait.py", False, True, 0)
    )
    base = _git(worktree, "rev-parse", "origin/dev")
    workflow = worktree / ".github/workflows/pr-orchestrator.yml"
    source = workflow.read_text()
    replacements = {
        "committed-invalid-live-valid": (
            "if: github.event_name == 'pull_request' && needs.changes.outputs.capsule_changed == 'true'",
            "if: false",
        ),
        "disabled": (
            "if: github.event_name == 'pull_request' && needs.changes.outputs.capsule_changed == 'true'",
            "if: false",
        ),
        "filtered": ('              - "tests/native/**"\n', ""),
        "nonblocking": ("  customer-capsules:\n", "  customer-capsules:\n    continue-on-error: true\n"),
    }
    if case in replacements:
        workflow.write_text(source.replace(*replacements[case]))
    payload = worktree / "tests/native/proof_macos_native_broker_wait.py"
    if case == "payload":
        payload.write_text("actual committed payload\n")
    if case == "mixed":
        unrelated = worktree / "packages/specfact-project/resources/example.py"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("unrelated committed source\n")
    if case == "checker-decoy":
        (worktree / "scripts/check_capsule_deferral.py").write_text("raise SystemExit(97)\n")
    _git(worktree, "add", ".")
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture final subject")
    head = _git(worktree, "rev-parse", "HEAD")
    if case == "live-index":
        workflow.write_text(
            source.replace("  customer-capsules:\n", "  customer-capsules:\n    continue-on-error: true\n")
        )
        _git(worktree, "add", ".")
    if case == "committed-invalid-live-valid":
        workflow.write_text(source)
        _git(worktree, "add", ".")
    if case == "live-dev-ref":
        _git(worktree, "update-ref", "refs/remotes/origin/dev", head)
    return worktree, base, head, workflow
