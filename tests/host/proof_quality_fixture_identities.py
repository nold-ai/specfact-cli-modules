"""Host-owned Bash proofs for quality fixture authentication."""

from __future__ import annotations

import json
import os
import subprocess
from importlib import import_module
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_smoke_lock(tmp_path: Path, invalid: str | None) -> dict[str, str]:
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
    return lock


@pytest.mark.parametrize("invalid", [None, "json", "repository", "commit", "tree", "missing", "shape"])
def test_quality_smoke_lock_is_validated_before_outputs(tmp_path: Path, invalid: str | None) -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    assert "Read runtime smoke fixture identity" in steps, "quality job does not read the paired core smoke lock"
    reader = steps["Read runtime smoke fixture identity"]
    lock = _write_smoke_lock(tmp_path, invalid)
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


def _smoke_checkout(tmp_path: Path, mismatch: str | None):
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
    return fixture, git_env, commit, tree


@pytest.mark.parametrize("mismatch", [None, "commit", "tree", "tracked", "untracked"])
def test_quality_smoke_verifies_git_checkout_before_export(tmp_path: Path, mismatch: str | None) -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    assert "Verify runtime smoke fixture" in steps, "quality job does not authenticate a separate smoke fixture"
    verification = steps["Verify runtime smoke fixture"]
    fixture, git_env, commit, tree = _smoke_checkout(tmp_path, mismatch)
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
    _assert_smoke_checkout_result(result, mismatch, output, runner_temp, fixture, commit)


def _assert_smoke_checkout_result(result, mismatch, output, runner_temp, fixture, commit):
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
