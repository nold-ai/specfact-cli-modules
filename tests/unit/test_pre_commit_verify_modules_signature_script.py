from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pre_commit_verify_modules_signature_script_matches_ci_branch_policy() -> None:
    text = (REPO_ROOT / "scripts" / "pre-commit-verify-modules-signature.sh").read_text(encoding="utf-8")
    assert "git rev-parse --abbrev-ref HEAD" in text
    assert "GITHUB_BASE_REF" in text
    assert "_branch" in text
    assert "_require_signature" in text
    assert '== "main"' in text
    assert "--payload-from-filesystem" in text
    assert "--enforce-version-bump" in text
    assert "verify-modules-signature.py" in text

    marker = 'if [[ "$_require_signature" == true ]]; then'
    assert marker in text
    _head, tail = text.split(marker, 1)
    assert "--require-signature" not in _head
    true_part, from_else = tail.split("else", 1)
    false_part = from_else.split("fi", 1)[0]
    assert "--require-signature" in true_part
    assert "--require-signature" not in false_part
