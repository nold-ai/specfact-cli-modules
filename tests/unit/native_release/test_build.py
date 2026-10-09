import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.native_release import build


def test_native_build_refuses_ambiguous_designated_requirements(tmp_path, monkeypatch):
    monkeypatch.setattr(
        build.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="# designated => first\n# designated => second\n", stderr=""),
    )
    output = tmp_path / "requirement"
    with pytest.raises(ValueError, match="unique"):
        build.requirement_file(tmp_path / "image", output)
    assert not output.exists()


def test_unsupported_abi_cannot_create_or_download_inputs(tmp_path):
    script = Path(__file__).resolve().parents[3] / "scripts/native_release/prepare-ci.sh"
    root = tmp_path / "input"
    result = subprocess.run(["/bin/bash", str(script), "cp314", str(root)], capture_output=True, check=False)
    assert result.returncode == 2
    assert not root.exists()


def test_transport_recipe_restores_immutable_inventory_without_changing_bytes(tmp_path):
    import yaml

    from scripts import build_macos_native_capsule as validator

    tools = tmp_path / "tools"
    for name, image in (("managed-uv", "uv"), ("managed-git", "git")):
        root = tools / name
        (root / "bin").mkdir(parents=True)
        (root / "bin" / image).write_bytes(b"declared executable")
        (root / "provenance.json").write_bytes(b"public provenance")
    git = tools / "managed-git"
    files = {"bin/git": git / "bin/git", "provenance.json": git / "provenance.json"}
    before = {name: path.read_bytes() for name, path in files.items()}
    with pytest.raises(ValueError, match="immutable"):
        validator._git_file_records(files, set(files), executable="bin/git")
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load((root / ".github/workflows/native-capsule-release.yml").read_text())
    restore = next(
        step for step in workflow["jobs"]["build"]["steps"] if step.get("name", "").startswith("Restore the fixed")
    )
    subprocess.run(["bash", "-c", restore["run"]], env={"RUNNER_TEMP": str(tmp_path)}, check=True)
    assert validator._git_file_records(files, set(files), executable="bin/git")
    assert {name: path.read_bytes() for name, path in files.items()} == before
    files["provenance.json"].chmod(0o555)
    with pytest.raises(ValueError, match="one executable"):
        validator._git_file_records(files, set(files), executable="bin/git")


def test_cp311_preparation_removes_only_bootstrap_setuptools_before_pinned_install():
    root = Path(__file__).resolve().parents[3]
    recipe = (root / "scripts/native_release/prepare-ci.sh").read_text()
    bootstrap_removal = '"$INPUT_ROOT/venv/bin/python" -m pip uninstall --yes setuptools'
    assert bootstrap_removal in recipe
    assert recipe.index('-m venv "$INPUT_ROOT/venv"') < recipe.index(bootstrap_removal)
    assert recipe.index(bootstrap_removal) < recipe.index("-m pip install --require-hashes")
    lock = (root / "scripts/native_analyzer_inputs/darwin-arm64-cp311.txt").read_text()
    assert "setuptools==" not in lock
