from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "git-branch-module-signature-flag.sh"


def test_git_branch_module_signature_flag_script_documents_cli_parity() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "specfact-cli" in text
    assert "GITHUB_BASE_REF" in text
    assert '"require"' in text
    assert "omit" in text


def test_git_branch_module_signature_flag_script_requires_for_main_base() -> None:
    env = {**os.environ, "GITHUB_BASE_REF": "main"}
    result = subprocess.run([SCRIPT_PATH], capture_output=True, text=True, check=False, env=env)

    assert result.returncode == 0
    assert result.stdout.strip() == "require"


def test_git_branch_module_signature_flag_script_omits_when_base_ref_unset(tmp_path: Path) -> None:
    # Without GITHUB_BASE_REF the script falls back to the current git branch; use an isolated
    # repo on a non-main branch so the outcome is "omit" regardless of the outer worktree branch.
    repo = (tmp_path / "repo").resolve()
    repo.mkdir(parents=True, exist_ok=True)
    # CI and some tooling set GIT_DIR / GIT_WORK_TREE; those override cwd and would mutate the
    # outer modules worktree if inherited by subprocess git calls.
    scrubbed_git_env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_COMMON_DIR",
            "GITHUB_BASE_REF",
        }
    }
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, env=scrubbed_git_env)
    subprocess.run(
        ["git", "config", "user.email", "omit-test@example.com"],
        cwd=repo,
        check=True,
        env=scrubbed_git_env,
    )
    subprocess.run(["git", "config", "user.name", "omit-test"], cwd=repo, check=True, env=scrubbed_git_env)
    (repo / "tracked").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "tracked"], cwd=repo, check=True, env=scrubbed_git_env)
    subprocess.run(
        ["git", "commit", "--no-verify", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=scrubbed_git_env,
    )
    subprocess.run(["git", "checkout", "-b", "side"], cwd=repo, check=True, env=scrubbed_git_env)
    assert (repo / ".git").exists()
    assert repo.is_relative_to(tmp_path.resolve()), f"nested repo must stay under pytest tmp dir ({repo=}, {tmp_path=})"
    result = subprocess.run(
        [SCRIPT_PATH],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=scrubbed_git_env,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "omit"


def test_git_branch_module_signature_flag_script_omits_for_non_main_base() -> None:
    env = {**os.environ, "GITHUB_BASE_REF": "feature/x"}
    result = subprocess.run([SCRIPT_PATH], capture_output=True, text=True, check=False, env=env)

    assert result.returncode == 0
    assert result.stdout.strip() == "omit"
