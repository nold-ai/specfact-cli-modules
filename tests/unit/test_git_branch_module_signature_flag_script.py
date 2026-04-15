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


def test_git_branch_module_signature_flag_script_omits_for_non_main_base() -> None:
    env = {**os.environ, "GITHUB_BASE_REF": "feature/x"}
    result = subprocess.run([SCRIPT_PATH], capture_output=True, text=True, check=False, env=env)

    assert result.returncode == 0
    assert result.stdout.strip() == "omit"
