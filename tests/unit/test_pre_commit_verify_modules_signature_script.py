from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _pre_commit_verify_script_text() -> str:
    return (REPO_ROOT / "scripts/pre-commit-verify-modules-signature.sh").read_text(encoding="utf-8")


def test_pre_commit_verify_modules_signature_script_has_expected_entrypoints() -> None:
    text = _pre_commit_verify_script_text()
    assert "git-branch-module-signature-flag.sh" in text
    assert 'case "${sig_policy}" in' in text
    assert "require)" in text
    assert "omit)" in text
    assert "--payload-from-filesystem" in text
    assert "--enforce-version-bump" in text
    assert "verify-modules-signature.py" in text


def test_pre_commit_verify_modules_signature_script_require_branch_uses_strict_verify() -> None:
    text = _pre_commit_verify_script_text()
    marker = 'case "${sig_policy}" in'
    _head, tail = text.split(marker, 1)
    assert "--require-signature" not in _head
    require_block = tail.split("omit)", 1)[0]
    assert "--require-signature" in require_block


def test_pre_commit_verify_modules_signature_script_omit_branch_remediation_shape() -> None:
    text = _pre_commit_verify_script_text()
    marker = 'case "${sig_policy}" in'
    _tail = text.split(marker, 1)[1]
    omit_block = _tail.split("omit)", 1)[1].split("*)", 1)[0]
    assert "--require-signature" not in omit_block
    assert "--metadata-only" not in omit_block
    assert '"${_base[@]}"' in omit_block
    assert "sign-modules.py" in omit_block
    assert "--changed-only" in omit_block
    assert "--bump-version patch" in omit_block
    assert "--allow-unsigned" in omit_block
    assert "_stage_manifests_from_sign_output" in omit_block
    assert "HEAD~1" in omit_block
    assert "_failed_manifests" in omit_block
