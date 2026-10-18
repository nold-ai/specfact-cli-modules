"""Trust-boundary contracts for paired core workflow checkouts."""

from __future__ import annotations

import json
import os
import re
import subprocess
from importlib import import_module
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = (
    (
        "docs-review.yml",
        "docs-review",
        "Resolve paired core command sources ref",
        "Checkout paired core command sources",
    ),
    (
        "pr-orchestrator.yml",
        "quality",
        "Resolve paired core CLI ref",
        "Checkout paired core CLI",
    ),
    (
        "requirements-evidence.yml",
        "requirements-evidence",
        "Resolve paired core CLI ref",
        "Checkout paired core CLI",
    ),
)
EXPECTED_TRIGGERS: dict[str, set[str]] = {
    "docs-review.yml": {"pull_request", "push"},
    "pr-orchestrator.yml": {"pull_request", "push"},
    "requirements-evidence.yml": {"pull_request"},
}


def _step_text(workflow_name: str, job_name: str, step_name: str) -> str:
    workflow = (REPO_ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
    job_match = re.search(
        rf"(?ms)^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)",
        workflow,
    )
    assert job_match is not None, f"missing workflow job: {workflow_name}:{job_name}"
    step_match = re.search(
        rf"(?ms)^      - name: {re.escape(step_name)}\n(?P<body>.*?)(?=^      - (?:name|uses): |\Z)",
        job_match.group("body"),
    )
    assert step_match is not None, f"missing workflow step: {workflow_name}:{job_name}:{step_name}"
    return step_match.group(0)


def _workflow_events(workflow_name: str) -> set[str]:
    yaml = import_module("yaml")

    workflow_path = REPO_ROOT / ".github" / "workflows" / workflow_name
    parsed = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict), f"invalid workflow mapping: {workflow_name}"
    events = parsed.get("on")
    assert isinstance(events, dict), f"invalid workflow trigger mapping: {workflow_name}"
    return {str(event) for event in events}


def test_dynamic_paired_core_workflows_exclude_manual_dispatch() -> None:
    for workflow_name, job_name, resolver_name, checkout_name in WORKFLOWS:
        resolver = _step_text(workflow_name, job_name, resolver_name)
        dynamic_checkout = _step_text(workflow_name, job_name, checkout_name)

        assert _workflow_events(workflow_name) == EXPECTED_TRIGGERS[workflow_name]
        assert "github.event_name != 'workflow_dispatch'" not in resolver
        assert "github.event_name != 'workflow_dispatch'" not in dynamic_checkout
        assert "ref: ${{ steps.core-ref.outputs.ref }}" in dynamic_checkout
        assert "persist-credentials: false" in dynamic_checkout


def test_dynamic_paired_core_workflows_have_no_dead_manual_checkout_paths() -> None:
    for workflow_name, _job_name, _resolver_name, checkout_name in WORKFLOWS:
        workflow = (REPO_ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")

        assert f"{checkout_name} (manual main)" not in workflow
        assert f"{checkout_name} (manual dev)" not in workflow


def test_lean_docs_workflow_keeps_serial_suite_and_failure_propagation() -> None:
    suite = _step_text("docs-review.yml", "docs-review", "Run docs review suite")
    assert '-o "addopts=-ra -v --import-mode=importlib"' in suite
    expected = {
        "tests/unit/docs/test_docs_review.py",
        "tests/unit/docs/test_code_review_docs_parity.py",
        "tests/unit/test_core_documentation_accountability.py",
        "tests/unit/test_pre_commit_quality_parity.py",
        "tests/unit/docs/test_llms_overview_freshness.py",
    }
    assert set(re.findall(r"tests/[^\s]+\.py", suite)) == expected
    assert 'exit "${PIPESTATUS[0]:-$?}"' in suite


def test_quality_full_suite_selects_only_declared_baseline() -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    quality = workflow["jobs"]["quality"]
    steps = {step.get("name"): step for step in quality["steps"]}
    suite = steps["Full Test Suite"]
    assert suite.get("env", {}).get("SPECFACT_CLI_REPO") == "${{ github.workspace }}/baseline-core"
    assert suite["run"] == "hatch run test"
    checkout = steps["Checkout declared core baseline"]
    assert checkout["with"] == {
        "repository": "nold-ai/specfact-cli",
        "path": "baseline-core",
        "ref": "d579970565530c3fd7b98bad4de90cf874c2a99d",
        "persist-credentials": False,
    }
    verification = steps["Verify declared core baseline"]["run"]
    assert "d579970565530c3fd7b98bad4de90cf874c2a99d" in verification
    assert "f49667f21e4a20a432ad80032a01a5c6894b0c91" in verification
    assert "SPECFACT_CLI_REPO=${GITHUB_WORKSPACE}/specfact-cli" in steps["Export paired core CLI path"]["run"]
    assert "SPECFACT_CLI_REPO" not in quality.get("env", {})
    for name, step in steps.items():
        if name != "Full Test Suite":
            assert "SPECFACT_CLI_REPO" not in step.get("env", {})
    names = list(steps)
    assert names.index("Smart Test Configuration") < names.index("Checkout declared core baseline")
    assert names.index("Verify declared core baseline") < names.index("Full Test Suite")


@pytest.mark.parametrize("invalid", [None, "json", "repository", "commit", "tree", "missing", "shape"])
def test_quality_smoke_lock_is_validated_before_outputs(tmp_path: Path, invalid: str | None) -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    assert "Read runtime smoke fixture identity" in steps, "quality job does not read the paired core smoke lock"
    reader = steps["Read runtime smoke fixture identity"]
    lock: dict[str, str] = {
        "repository": "nold-ai/specfact-cli-modules",
        "commit": "a" * 40,
        "tree": "b" * 40,
    }
    if invalid in {"repository", "commit", "tree"}:
        lock[invalid] = "unexpected\nvalue"
    if invalid == "missing":
        del lock["tree"]
    lock_path = tmp_path / "specfact-cli/ci/runtime-smoke-fixture.lock.json"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("{" if invalid == "json" else "[]" if invalid == "shape" else json.dumps(lock))
    output = tmp_path / "outputs"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", reader["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if invalid is not None:
        assert result.returncode != 0
        assert not output.exists() or not output.read_text()
    else:
        assert result.returncode == 0, result.stderr
        assert dict(line.split("=", 1) for line in output.read_text().splitlines()) == {
            "commit": lock["commit"],
            "tree": lock["tree"],
        }


@pytest.mark.parametrize("mismatch", [None, "commit", "tree", "tracked", "untracked"])
def test_quality_smoke_verifies_git_checkout_before_export(tmp_path: Path, mismatch: str | None) -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    assert "Verify runtime smoke fixture" in steps, "quality job does not authenticate a separate smoke fixture"
    verification = steps["Verify runtime smoke fixture"]
    fixture = tmp_path / "runtime-smoke-modules"
    fixture.mkdir()
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.test",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.test",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    for args in (["init"], ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=fixture, env=git_env, check=True, capture_output=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=fixture, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=fixture, text=True).strip()
    if mismatch == "tracked":
        (fixture / "staged.txt").write_text("dirty")
        subprocess.run(["git", "add", "staged.txt"], cwd=fixture, check=True, capture_output=True)
    if mismatch == "untracked":
        (fixture / "extra.txt").write_text("dirty")
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    output = tmp_path / "environment"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", verification["run"]],
        cwd=tmp_path,
        env={
            **git_env,
            "GITHUB_WORKSPACE": str(tmp_path),
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_ENV": str(output),
            "FIXTURE_COMMIT": "0" * 40 if mismatch == "commit" else commit,
            "FIXTURE_TREE": "0" * 40 if mismatch == "tree" else tree,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if mismatch is not None:
        assert result.returncode != 0
        assert not output.exists() or not output.read_text()
    else:
        assert result.returncode == 0, result.stderr
        relocated = runner_temp / "runtime-smoke-modules"
        assert output.read_text().strip() == f"SPECFACT_SMOKE_MODULES_REPO={relocated}"
        assert not fixture.exists()
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=relocated, text=True).strip() == commit
        assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=relocated, text=True).strip()


def test_quality_smoke_preserves_all_launchers_with_separate_checkout() -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    smoke = steps["Runtime discovery smoke across package managers"]
    assert '--modules-repo "${SPECFACT_SMOKE_MODULES_REPO}"' in smoke["run"]
    assert re.findall(r"--launcher ([a-z-]+)", smoke["run"]) == [
        "direct",
        "hatch-source",
        "pip-editable",
        "pipx",
        "uv-run",
        "uvx",
    ]
    checkout = steps["Checkout runtime smoke modules"]
    assert checkout["with"] == {
        "repository": "nold-ai/specfact-cli-modules",
        "path": "runtime-smoke-modules",
        "ref": "${{ steps.smoke-fixture.outputs.commit }}",
        "persist-credentials": False,
    }
    verification = steps["Verify runtime smoke fixture"]
    assert verification["env"] == {
        "FIXTURE_COMMIT": "${{ steps.smoke-fixture.outputs.commit }}",
        "FIXTURE_TREE": "${{ steps.smoke-fixture.outputs.tree }}",
    }
    assert steps["Read runtime smoke fixture identity"]["id"] == "smoke-fixture"
    names = list(steps)
    preparation = [
        "Read runtime smoke fixture identity",
        "Checkout runtime smoke modules",
        "Verify runtime smoke fixture",
    ]
    assert [names.index(name) for name in preparation] == sorted(names.index(name) for name in preparation)
    for name in preparation:
        assert steps[name]["if"] == smoke["if"]
        assert names.index(name) < names.index("Runtime discovery smoke across package managers")
