"""Helpers for resolving and installing the local specfact-cli dependency."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def _is_core_repo(path: Path) -> bool:
    return (path / "src" / "specfact_cli" / "__init__.py").exists()


def _configured_core_repo() -> Path | None:
    configured = os.environ.get("SPECFACT_CLI_REPO")
    if not configured:
        return None
    candidate = Path(configured).expanduser().resolve()
    if _is_core_repo(candidate):
        return candidate
    return None


def _paired_worktree_core_repo(repo_root: Path) -> Path | None:
    parts = repo_root.resolve().parts
    for index, part in enumerate(parts):
        if part != "specfact-cli-modules-worktrees":
            continue
        paired_root = Path(*parts[:index], "specfact-cli-worktrees", *parts[index + 1 :])
        if _is_core_repo(paired_root):
            return paired_root.resolve()
    return None


def _walk_parent_siblings(repo_root: Path) -> Path | None:
    for parent in repo_root.resolve().parents:
        sibling = (parent / "specfact-cli").resolve()
        if _is_core_repo(sibling):
            return sibling
    return None


def resolve_core_repo(repo_root: Path) -> Path | None:
    """Resolve the specfact-cli checkout that this modules repo should use."""
    return _configured_core_repo() or _paired_worktree_core_repo(repo_root) or _walk_parent_siblings(repo_root)


def apply_specfact_workspace_env(repo_root: Path) -> None:
    """Default SPECFACT_* workspace env for this checkout (matches specfact-cli test/CI patterns).

    Pins ``SPECFACT_MODULES_REPO`` to the modules repo root and ``SPECFACT_REPO_ROOT`` to the resolved
    sibling/core specfact-cli checkout when known. Discovery then agrees with ``specfact module list
    --show-origin`` expectations; project ``.specfact/modules`` still wins over ``~/.specfact/modules``
    when both exist—remove stale user copies with ``specfact module uninstall <name> --scope user``.
    """
    resolved = repo_root.resolve()
    os.environ.setdefault("SPECFACT_MODULES_REPO", str(resolved))
    core = resolve_core_repo(repo_root)
    if core is not None:
        os.environ.setdefault("SPECFACT_REPO_ROOT", str(core))


def _installed_core_exists() -> bool:
    return importlib.util.find_spec("specfact_cli") is not None


def ensure_core_dependency(repo_root: Path) -> int:
    """Install specfact-cli editable dependency if the active environment is not aligned."""
    apply_specfact_workspace_env(repo_root)
    if _installed_core_exists():
        return 0
    core_repo = resolve_core_repo(repo_root)
    if core_repo is None:
        print("Unable to resolve specfact-cli checkout. Set SPECFACT_CLI_REPO.", file=sys.stderr)
        return 1
    command = [sys.executable, "-m", "pip", "install", "-e", str(core_repo)]
    return subprocess.run(command, cwd=repo_root, check=False).returncode


def main() -> int:
    return ensure_core_dependency(Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    raise SystemExit(main())
