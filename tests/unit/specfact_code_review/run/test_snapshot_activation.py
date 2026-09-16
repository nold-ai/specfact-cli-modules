"""Immutable snapshot discovery retains verified activation, never live dependencies."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from specfact_code_review.run import runner, runtime_discovery, scope
from specfact_code_review.run.portable_snapshot import discover_snapshot
from specfact_code_review.run.runtime_models import ProjectRuntimeError, content_digest


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        timeout=30,
    )


@pytest.fixture(name="activated_repository")
def activated_repository_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Capture a real index whose dependency bytes differ from the live checkout."""
    root = tmp_path / "project"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "app.py").write_text("VALUE = 1\n")
    (root / ".gitignore").write_text(".venv/\n")
    metadata = (
        '[project]\nname="customer"\n[tool.hatch.envs.review]\n'
        'dependencies=["requests==2.32.3"]\n[tool.hatch.envs.other]\n'
    )
    (root / "pyproject.toml").write_text(metadata)
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "fixture",
    )
    (root / "pyproject.toml").write_text(metadata.replace("2.32.3", "2.32.4"))
    _git(root, "add", "pyproject.toml")
    (root / "pyproject.toml").write_text(metadata.replace("2.32.3", "2.32.5"))
    environment = root / ".venv"
    environment.mkdir()
    (environment / "pyvenv.cfg").write_text("home=/fixture/python\n")
    monkeypatch.setenv("VIRTUAL_ENV", str(environment))
    monkeypatch.setenv("HATCH_ENV_ACTIVE", "review")
    monkeypatch.setattr(runtime_discovery.sys, "prefix", str(environment))
    monkeypatch.chdir(root)
    return root


@pytest.mark.parametrize("active", ["review", "default"])
def test_index_activation_keeps_snapshot_dependency_identity(
    activated_repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, active: str
) -> None:
    """The actual cached review path selects activation without importing live inputs."""
    monkeypatch.setenv("HATCH_ENV_ACTIVE", active)
    (tmp_path / "snapshot").mkdir()
    snapshot = runner._cached_analysis_snapshot([Path("app.py")], tmp_path / "snapshot")
    assert snapshot is not None
    plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
    assert plan.environment == active
    assert plan.root == snapshot.root.resolve()
    content = (snapshot.root / "pyproject.toml").read_bytes()
    assert b"2.32.4" in content and b"2.32.5" not in content
    assert plan.inputs["pyproject.toml"] == content_digest(content)
    assert plan.inputs["pyproject.toml"] != content_digest((activated_repository / "pyproject.toml").read_bytes())


@pytest.mark.parametrize("context", ["unrelated", "spoofed"])
@pytest.mark.parametrize("active", ["review", "default"])
def test_snapshot_rejects_unverified_activation(
    activated_repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    context: str,
    active: str,
) -> None:
    """Only the actual repository-local running interpreter can select an environment."""
    monkeypatch.setenv("HATCH_ENV_ACTIVE", active)
    environment = tmp_path / "unrelated"
    environment.mkdir()
    (environment / "pyvenv.cfg").write_text("home=/fixture/python\n")
    monkeypatch.setenv("VIRTUAL_ENV", str(environment))
    if context == "unrelated":
        monkeypatch.setattr(runtime_discovery.sys, "prefix", str(environment))
    (tmp_path / "snapshot").mkdir()
    snapshot = runner._cached_analysis_snapshot([activated_repository / "app.py"], tmp_path / "snapshot")
    assert snapshot is not None
    with pytest.raises(ProjectRuntimeError, match="project_environment_ambiguous"):
        discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)


@pytest.mark.parametrize("manager", ['manager="hatch"\n', ""])
@pytest.mark.parametrize("active", ["review", "default"])
def test_snapshot_explicit_selection_overrides_activation(
    activated_repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manager: str, active: str
) -> None:
    """An explicit environment continues to outrank valid ambient activation."""
    monkeypatch.setenv("HATCH_ENV_ACTIVE", active)
    metadata = activated_repository / "pyproject.toml"
    original = metadata.read_text()
    metadata.write_text('[project]\nname="customer"\n[tool.hatch.envs.other]\n')
    _git(activated_repository, "add", "pyproject.toml")
    metadata.write_text(original)
    config = tmp_path / "review.toml"
    config.write_text(manager + 'environment="other"\n')
    (tmp_path / "snapshot").mkdir()
    snapshot = runner._cached_analysis_snapshot([activated_repository / "app.py"], tmp_path / "snapshot")
    assert snapshot is not None
    assert discover_snapshot(snapshot.root, config_path=config, source_snapshot=snapshot).environment == "other"


def test_removed_active_environment_is_not_substituted(activated_repository: Path, tmp_path: Path) -> None:
    """Each selected revision must contain the verified active environment itself."""
    metadata = activated_repository / "pyproject.toml"
    metadata.write_text('[project]\nname="customer"\n[tool.hatch.envs.other]\n')
    _git(activated_repository, "add", "pyproject.toml")
    metadata.write_text('[project]\nname="customer"\n[tool.hatch.envs.review]\n[tool.hatch.envs.other]\n')
    (tmp_path / "snapshot").mkdir()
    snapshot = runner._cached_analysis_snapshot([activated_repository / "app.py"], tmp_path / "snapshot")
    assert snapshot is not None
    with pytest.raises(ProjectRuntimeError, match="project_active_environment_missing:review"):
        discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)


@pytest.mark.parametrize("active", ["review", "default"])
def test_revision_activation_binds_its_own_dependency_inputs(
    activated_repository: Path, monkeypatch: pytest.MonkeyPatch, active: str
) -> None:
    """A revision side reuses only verified selection, never another side's dependency bytes."""
    monkeypatch.setenv("HATCH_ENV_ACTIVE", active)
    commit = subprocess.check_output(["git", "-C", str(activated_repository), "rev-parse", "HEAD"], text=True).strip()
    snapshot = scope._materialize_commit(activated_repository, commit)
    try:
        plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
        assert plan.environment == active
        content = (snapshot.root / "pyproject.toml").read_bytes()
        assert b"2.32.3" in content and b"2.32.5" not in content
        assert plan.inputs["pyproject.toml"] == content_digest(content)
        assert plan.vcs["commit"] == commit
    finally:
        shutil.rmtree(snapshot.root)


def test_live_activation_recognizes_implicit_hatch_default(
    activated_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hatch defines default even when only custom environment tables exist."""
    monkeypatch.setenv("HATCH_ENV_ACTIVE", "default")
    plan = runtime_discovery.discover_project(activated_repository)
    assert (plan.manager, plan.environment) == ("hatch", "default")
    content = (activated_repository / "pyproject.toml").read_bytes()
    assert b"[tool.hatch.envs.default]" not in content
    assert plan.inputs["pyproject.toml"] == content_digest(content)
