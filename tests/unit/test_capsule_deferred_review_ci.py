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
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    target = repository / "packages/example/src/example.py"
    target.parent.mkdir(parents=True)
    target.write_text("value = 1\n")
    unrelated = target.with_name("unrelated.py")
    unrelated.write_text("value = 1\n")
    script = repository / "scripts/pre_commit_code_review.py"
    script.parent.mkdir()
    script.write_text(
        "import os, subprocess, sys\n"
        "from pathlib import Path\n"
        "assert os.environ['SPECFACT_CODE_REVIEW_ENFORCEMENT'] == 'changed'\n"
        "import tomllib\n"
        "config = Path(os.environ['SPECFACT_CODE_REVIEW_PROJECT_CONFIG'])\n"
        "assert tomllib.loads(config.read_text()) == {'manager': 'hatch', 'environment': 'default'}\n"
        "assert Path(os.environ['SPECFACT_CODE_REVIEW_SUBJECT_ROOT']).resolve() == Path.cwd()\n"
        "assert not {'GITHUB_TOKEN', 'GH_TOKEN', 'PYTHONPATH'} & os.environ.keys()\n"
        "from pathlib import Path\n"
        "cache = Path(os.environ['SPECFACT_CODE_REVIEW_CAPSULE_CACHE'])\n"
        "assert cache == Path(os.environ['CUSTOMER_ROOT']) / 'commit-review-cache'\n"
        "cache.mkdir(parents=True, exist_ok=True)\n"
        "(cache / 'verified-fixture-blob').write_text('fixture')\n"
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
    if advanced_dev:
        _git(repository, "checkout", "-qb", "dev", base)
        unrelated.write_text("value = 3\n")
        _git(repository, "add", ".")
        _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture advanced dev")
        base = _git(repository, "rev-parse", "HEAD")
        _git(repository, "checkout", "--detach", head)
    customer = tmp_path / "customer"
    (customer / "cache").mkdir(parents=True)
    (customer / "venv/bin").mkdir(parents=True)
    (customer / "venv/bin/python").symlink_to(sys.executable)
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
    "platform,ci,deferral,bundle,advanced_dev,expected",
    [
        ("Darwin", "", "github-linux", "specfact-code-review", False, 0),
        ("Darwin", "true", "github-linux", "specfact-code-review", False, 1),
        ("Linux", "", "github-linux", "specfact-code-review", False, 1),
        ("Darwin", "", "invalid", "specfact-code-review", False, 1),
        ("Darwin", "", "github-linux", "specfact-project", False, 1),
        ("Darwin", "", "github-linux", "specfact-project", True, 1),
    ],
)
def test_narrow_local_deferral_retains_block2_and_cannot_run_in_ci(
    tmp_path: Path, platform: str, ci: str, deferral: str, bundle: str, advanced_dev: bool, expected: int
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
        f"packages/{bundle}/resources/example.py",
        "openspec/changes/example/spec.md",
    ]
    for relative in files:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("baseline\n")
    capsule_manifest = repository / "packages/specfact-code-review/module-package.yaml"
    capsule_manifest.parent.mkdir(parents=True, exist_ok=True)
    capsule_manifest.write_text("version: 1\n")
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture base")
    _git(repository, "update-ref", "refs/remotes/origin/dev", "HEAD")
    worktree = tmp_path / "worktree"
    _git(repository, "worktree", "add", "-qb", "codex/fixture", str(worktree))
    if advanced_dev:
        capsule_manifest.write_text("version: 2\n")
        _git(repository, "add", ".")
        _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture advanced dev")
        _git(repository, "update-ref", "refs/remotes/origin/dev", "HEAD")
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
        assert "Capsule review deferral" in result.stderr
