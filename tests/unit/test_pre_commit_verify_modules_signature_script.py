from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.unit._script_test_utils import block_contract_imports, load_module_from_path


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
    required = {
        "--allow-missing-public-key",
        "sign-modules.py",
        "--staged-only",
        "--bump-version patch",
        "--allow-unsigned",
        "_stage_manifests_from_sign_output",
    }
    forbidden = {"--require-signature", "--metadata-only", "HEAD~1", "_failed_manifests", "set +e"}

    assert all(fragment in omit_block for fragment in required)
    assert all(fragment not in omit_block for fragment in forbidden)
    assert "git diff --cached" in text


def test_pre_commit_verify_uses_target_branch_version_baseline() -> None:
    text = _pre_commit_verify_script_text()

    assert '_target_branch="${GITHUB_BASE_REF:-dev}"' in text
    assert '_version_check_base="refs/remotes/origin/${_target_branch}"' in text
    assert 'git rev-parse --verify --quiet "${_version_check_base}^{commit}"' in text
    assert '--version-check-base "${_version_check_base}"' in text


def test_sign_modules_loads_without_icontract(monkeypatch) -> None:
    block_contract_imports(monkeypatch)

    sign_script = load_module_from_path("sign_modules_without_icontract", SIGN_SCRIPT_PATH)

    assert callable(sign_script.main)
    assert callable(sign_script.ensure)
    assert callable(sign_script.require)


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


def test_sign_modules_fails_closed_when_staged_change_detection_cannot_run(monkeypatch) -> None:
    sign_script = load_module_from_path("sign_modules_staged_failure", SIGN_SCRIPT_PATH)

    def failed_git(*_args, **_kwargs):
        raise subprocess.CalledProcessError(128, ["git", "diff"])

    monkeypatch.setattr(sign_script.subprocess, "run", failed_git)

    with pytest.raises(ValueError, match="Unable to inspect staged module changes"):
        sign_script._module_has_staged_changes(Path("packages/specfact-example"))  # pylint: disable=protected-access


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _index_payload(repo_root: Path, module_relative: Path) -> bytes:
    listed = _git(repo_root, "ls-files", "--cached", "-z", "--", module_relative.as_posix()).stdout.split("\0")
    entries: list[str] = []
    for relative in sorted(path for path in listed if path):
        content = subprocess.run(
            ["git", "show", f":{relative}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
        module_path = Path(relative).relative_to(module_relative).as_posix()
        if module_path in {"module-package.yaml", "metadata.yaml"}:
            manifest = yaml.safe_load(content)
            assert isinstance(manifest, dict)
            manifest.pop("integrity", None)
            content = yaml.safe_dump(manifest, sort_keys=True, allow_unicode=False).encode("utf-8")
        entries.append(f"{module_path}:{hashlib.sha256(content).hexdigest()}")
    return "\n".join(entries).encode("utf-8")


def test_staged_only_signing_hashes_the_index_not_unstaged_module_content(tmp_path: Path) -> None:
    module_relative = Path("packages/specfact-example")
    module_dir = tmp_path / module_relative
    module_dir.mkdir(parents=True)
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text("name: nold-ai/specfact-example\nversion: 0.1.0\n", encoding="utf-8")
    source_path = module_dir / "src.py"
    source_path.write_text("VALUE = 'base'\n", encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "tests@example.invalid")
    _git(tmp_path, "config", "user.name", "SpecFact tests")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")

    source_path.write_text("VALUE = 'staged'\n", encoding="utf-8")
    _git(tmp_path, "add", source_path.relative_to(tmp_path).as_posix())
    source_path.write_text("VALUE = 'unstaged'\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SIGN_SCRIPT_PATH),
            "--staged-only",
            "--allow-unsigned",
            "--allow-same-version",
            "--payload-from-filesystem",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    written_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(written_manifest, dict)
    assert (
        written_manifest["integrity"]["checksum"]
        == f"sha256:{hashlib.sha256(_index_payload(tmp_path, module_relative)).hexdigest()}"
    )


def test_staged_only_auto_bump_signs_the_staged_snapshot(tmp_path: Path) -> None:
    module_relative = Path("packages/specfact-example")
    module_dir = tmp_path / module_relative
    module_dir.mkdir(parents=True)
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text("name: nold-ai/specfact-example\nversion: 0.1.0\n", encoding="utf-8")
    source_path = module_dir / "src.py"
    source_path.write_text("VALUE = 'base'\n", encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "tests@example.invalid")
    _git(tmp_path, "config", "user.name", "SpecFact tests")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")

    source_path.write_text("VALUE = 'staged'\n", encoding="utf-8")
    _git(tmp_path, "add", source_path.relative_to(tmp_path).as_posix())
    source_path.write_text("VALUE = 'unstaged'\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SIGN_SCRIPT_PATH),
            "--staged-only",
            "--bump-version",
            "patch",
            "--allow-unsigned",
            "--payload-from-filesystem",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    written_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    staged_manifest = yaml.safe_load(_git(tmp_path, "show", f":{manifest_path.relative_to(tmp_path)}").stdout)
    assert isinstance(written_manifest, dict)
    assert isinstance(staged_manifest, dict)
    assert written_manifest["version"] == staged_manifest["version"] == "0.1.1"
    assert (
        written_manifest["integrity"]["checksum"]
        == f"sha256:{hashlib.sha256(_index_payload(tmp_path, module_relative)).hexdigest()}"
    )
