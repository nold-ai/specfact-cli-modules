from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_cli_modules.dev_bootstrap import apply_specfact_workspace_env, ensure_core_dependency, resolve_core_repo


def _make_core_repo(path: Path) -> Path:
    core_package = path / "src" / "specfact_cli"
    core_package.mkdir(parents=True)
    (core_package / "__init__.py").write_text("", encoding="utf-8")
    return path


def test_resolve_core_repo_prefers_matching_worktree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "specfact-cli-modules-worktrees" / "feature" / "demo-change"
    repo_root.mkdir(parents=True)
    expected = _make_core_repo(tmp_path / "specfact-cli-worktrees" / "feature" / "demo-change")

    monkeypatch.delenv("SPECFACT_CLI_REPO", raising=False)

    assert resolve_core_repo(repo_root) == expected.resolve()


def test_resolve_core_repo_falls_back_to_primary_checkout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "specfact-cli-modules-worktrees" / "feature" / "demo-change"
    repo_root.mkdir(parents=True)
    expected = _make_core_repo(tmp_path / "specfact-cli")

    monkeypatch.delenv("SPECFACT_CLI_REPO", raising=False)

    assert resolve_core_repo(repo_root) == expected.resolve()


def test_resolve_core_repo_prefers_explicit_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "specfact-cli-modules"
    repo_root.mkdir(parents=True)
    expected = _make_core_repo(tmp_path / "custom-core")

    monkeypatch.setenv("SPECFACT_CLI_REPO", str(expected))

    assert resolve_core_repo(repo_root) == expected.resolve()


def test_apply_specfact_workspace_env_sets_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "modules-repo"
    repo_root.mkdir()
    core = _make_core_repo(tmp_path / "core")

    monkeypatch.delenv("SPECFACT_MODULES_REPO", raising=False)
    monkeypatch.delenv("SPECFACT_REPO_ROOT", raising=False)
    monkeypatch.delenv("SPECFACT_CLI_REPO", raising=False)
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap.resolve_core_repo",
        lambda _root: core.resolve(),
    )

    apply_specfact_workspace_env(repo_root)

    assert os.environ["SPECFACT_MODULES_REPO"] == str(repo_root.resolve())
    assert os.environ["SPECFACT_REPO_ROOT"] == str(core.resolve())


def test_apply_specfact_workspace_env_without_core_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "modules-repo"
    repo_root.mkdir()

    monkeypatch.delenv("SPECFACT_MODULES_REPO", raising=False)
    monkeypatch.delenv("SPECFACT_REPO_ROOT", raising=False)
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap.resolve_core_repo",
        lambda _root: None,
    )

    apply_specfact_workspace_env(repo_root)

    assert os.environ["SPECFACT_MODULES_REPO"] == str(repo_root.resolve())
    assert "SPECFACT_REPO_ROOT" not in os.environ


def test_apply_specfact_workspace_env_overwrites_stale_exports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "modules-repo"
    repo_root.mkdir()
    core = _make_core_repo(tmp_path / "core")
    monkeypatch.setenv("SPECFACT_MODULES_REPO", "/stale/modules")
    monkeypatch.setenv("SPECFACT_REPO_ROOT", "/stale/core")
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap.resolve_core_repo",
        lambda _root: core.resolve(),
    )
    apply_specfact_workspace_env(repo_root)
    assert os.environ["SPECFACT_MODULES_REPO"] == str(repo_root.resolve())
    assert os.environ["SPECFACT_REPO_ROOT"] == str(core.resolve())


def test_ensure_core_dependency_allows_matching_editable_core(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "isolated-modules-repo"
    repo_root.mkdir(parents=True)
    core = _make_core_repo(tmp_path / "paired-core")

    monkeypatch.setenv("SPECFACT_CLI_REPO", str(core))
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap._installed_core_root",
        lambda: core.resolve(),
    )

    assert ensure_core_dependency(repo_root) == 0


def test_ensure_core_dependency_reinstalls_when_editable_core_mismatches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "isolated-modules-repo"
    repo_root.mkdir(parents=True)
    core_wrong = _make_core_repo(tmp_path / "core-wrong")
    core_wanted = _make_core_repo(tmp_path / "core-wanted")

    monkeypatch.setenv("SPECFACT_CLI_REPO", str(core_wanted))
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap._installed_core_root",
        lambda: core_wrong.resolve(),
    )

    recorded: list[list[str]] = []

    def _fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        recorded.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("specfact_cli_modules.dev_bootstrap.subprocess.run", _fake_run)

    assert ensure_core_dependency(repo_root) == 0
    assert recorded, "pip install -e should run when resolved core differs from installed root"
    pip_cmd = recorded[0]
    assert "-e" in pip_cmd
    assert str(core_wanted.resolve()) in pip_cmd


def test_ensure_core_dependency_allows_site_packages_when_core_unresolved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PyPI (or unknown-path) install: no resolved sibling core, but specfact_cli imports."""
    repo_root = tmp_path / "isolated-modules-repo"
    repo_root.mkdir(parents=True)

    monkeypatch.delenv("SPECFACT_CLI_REPO", raising=False)
    monkeypatch.setattr("specfact_cli_modules.dev_bootstrap.resolve_core_repo", lambda _root: None)
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap.importlib.util.find_spec",
        lambda name: SimpleNamespace() if name == "specfact_cli" else None,
    )

    assert ensure_core_dependency(repo_root) == 0
