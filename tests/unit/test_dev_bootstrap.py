from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_cli_modules.dev_bootstrap import ensure_core_dependency, resolve_core_repo


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


def test_ensure_core_dependency_allows_preinstalled_core(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "isolated-modules-repo"
    repo_root.mkdir(parents=True)

    monkeypatch.delenv("SPECFACT_CLI_REPO", raising=False)
    monkeypatch.setattr(
        "specfact_cli_modules.dev_bootstrap.importlib.util.find_spec",
        lambda name: (
            SimpleNamespace(submodule_search_locations=["/tmp/site-packages/specfact_cli"])
            if name == "specfact_cli"
            else None
        ),
    )

    assert ensure_core_dependency(repo_root) == 0
