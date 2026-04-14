from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pre_commit_verify_modules_signature_script_matches_cli_shape() -> None:
    text = (REPO_ROOT / "scripts/pre-commit-verify-modules-signature.sh").read_text(encoding="utf-8")
    assert "git-branch-module-signature-flag.sh" in text
    assert 'case "${sig_policy}" in' in text
    assert "require)" in text
    assert "omit)" in text
    assert "--payload-from-filesystem" in text
    assert "--enforce-version-bump" in text
    assert "verify-modules-signature.py" in text
    assert "--metadata-only" in text

    marker = 'case "${sig_policy}" in'
    assert marker in text
    _head, tail = text.split(marker, 1)
    assert "--require-signature" not in _head
    require_block = tail.split("omit)", 1)[0]
    assert "--require-signature" in require_block
    omit_block = tail.split("omit)", 1)[1].split("*)", 1)[0]
    assert "--require-signature" not in omit_block
    assert "--metadata-only" in omit_block
