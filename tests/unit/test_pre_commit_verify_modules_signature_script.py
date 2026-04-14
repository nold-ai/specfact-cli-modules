from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pre_commit_verify_modules_signature_script_matches_ci_branch_policy() -> None:
    text = (REPO_ROOT / "scripts" / "pre-commit-verify-modules-signature.sh").read_text(encoding="utf-8")
    assert "git rev-parse --abbrev-ref HEAD" in text
    assert "GITHUB_REF_NAME" in text
    assert '== "main"' in text
    assert "--payload-from-filesystem" in text
    assert "--enforce-version-bump" in text
    assert "--require-signature" in text
    assert "verify-modules-signature.py" in text
