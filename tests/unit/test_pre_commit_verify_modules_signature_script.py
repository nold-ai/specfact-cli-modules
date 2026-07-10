from __future__ import annotations

from pathlib import Path

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SIGN_SCRIPT_PATH = REPO_ROOT / "scripts" / "sign-modules.py"


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
    assert "--allow-missing-public-key" in omit_block
    assert "sign-modules.py" in omit_block
    assert "--staged-only" in omit_block
    assert "--bump-version patch" in omit_block
    assert "--allow-unsigned" in omit_block
    assert "_stage_manifests_from_sign_output" in omit_block
    assert "git diff --cached" in text
    assert "HEAD~1" not in omit_block
    assert "_failed_manifests" not in omit_block


def test_sign_modules_staged_change_detection_reads_only_the_index(monkeypatch) -> None:
    sign_script = load_module_from_path("sign_modules_staged_only", SIGN_SCRIPT_PATH)
    commands: list[list[str]] = []

    class _Result:
        stdout = "packages/specfact-example/src/example.py\n"

    def fake_run(command: list[str], **_kwargs) -> _Result:
        commands.append(command)
        return _Result()

    monkeypatch.setattr(sign_script.subprocess, "run", fake_run)

    assert sign_script._module_has_staged_changes(Path("packages/specfact-example"))  # pylint: disable=protected-access
    assert commands == [["git", "diff", "--cached", "--name-only", "--", "packages/specfact-example"]]
