"""Execute the hosted gate recipe against a real isolated Git index."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
STEP_NAME = "Run deferred candidate commit review without weakening enforcement"


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.mark.parametrize("gate_exit", [0, 7])
def test_deferred_gate_reviews_exact_staged_tree_and_propagates_failure(tmp_path: Path, gate_exit: int) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    steps = workflow["jobs"]["customer"]["steps"]
    step = next((item for item in steps if item.get("name") == STEP_NAME), None)
    assert step is not None, "No blocking candidate commit review runs in hosted Linux CI"
    assert step["if"] == "github.event_name == 'pull_request' && matrix.python == '3.12'"
    assert not step.get("continue-on-error", False)
    assert steps.index(step) > next(
        i for i, item in enumerate(steps) if item.get("name", "").startswith("Allow user namespaces")
    )
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    target = repository / "packages/example/src/example.py"
    target.parent.mkdir(parents=True)
    target.write_text("value = 1\n")
    script = repository / "scripts/pre_commit_code_review.py"
    script.parent.mkdir()
    script.write_text(
        "import os, subprocess, sys\n"
        "assert os.environ['SPECFACT_CODE_REVIEW_ENFORCEMENT'] == 'changed'\n"
        "assert not {'GITHUB_TOKEN', 'GH_TOKEN', 'PYTHONPATH'} & os.environ.keys()\n"
        "assert sys.argv[1:] == ['packages/example/src/example.py']\n"
        "assert open(sys.argv[1]).read() == 'value = 2\\n'\n"
        "assert subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).strip() == sys.argv[1]\n"
        "assert not subprocess.check_output(['git', 'diff', '--name-only'])\n"
        "raise SystemExit(int(os.environ['FIXTURE_GATE_EXIT']))\n"
    )
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture base")
    base = _git(repository, "rev-parse", "HEAD")
    target.write_text("value = 2\n")
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture candidate")
    head = _git(repository, "rev-parse", "HEAD")
    customer = tmp_path / "customer"
    (customer / "venv/bin").mkdir(parents=True)
    (customer / "venv/bin/python").symlink_to(sys.executable)
    environment = os.environ | {
        "CUSTOMER_ROOT": str(customer),
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
    assert _git(repository, "rev-parse", "HEAD") == head
    assert not _git(repository, "status", "--porcelain")


@pytest.mark.parametrize(
    "platform,ci,deferral,expected",
    [
        ("Darwin", "", "github-linux", 0),
        ("Darwin", "true", "github-linux", 1),
        ("Linux", "", "github-linux", 1),
        ("Darwin", "", "invalid", 1),
    ],
)
def test_narrow_local_deferral_retains_block2_and_cannot_run_in_ci(
    tmp_path: Path, platform: str, ci: str, deferral: str, expected: int
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    workflow = repository / ".github/workflows/capsule-customer-execution.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    files = [
        "llms.txt",
        "docs/reference/commands.generated.json",
        "docs/reference/commands.generated.md",
        "packages/example/resources/example.py",
        "openspec/changes/example/spec.md",
    ]
    for relative in files:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("baseline\n")
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture base")
    worktree = tmp_path / "worktree"
    _git(repository, "worktree", "add", "-qb", "codex/fixture", str(worktree))
    for relative in files[-2:]:
        (worktree / relative).write_text("candidate\n")
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    recipe = (
        script
        + r"""
uname() { if [[ "${1:-}" == "-m" ]]; then echo arm64; else echo "$FIXTURE_PLATFORM"; fi; }
hatch() {
  printf '%s\n' "$*" >> "$FIXTURE_CALLS"
  if [[ "$*" == *pre_commit_code_review.py* ]]; then return 99; fi
  if [[ "$*" == *contract-test-status* ]]; then return 1; fi
  return 0
}
run_block2
"""
    )
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
    for command in [
        "generate-command-overview",
        "check-command-overview",
        "check-command-contract",
        "check-core-documentation-accountability",
        "check-docs-commands.py",
        "check-prompt-commands.py",
        "requirements_evidence_gate.py --staged",
    ]:
        assert command in invoked
    assert "pre_commit_code_review.py" not in invoked
    if expected == 0:
        assert "DEFERRED" in result.stderr
        assert "contract-test-contracts" in invoked
    else:
        assert "Capsule review deferral is restricted" in result.stderr
