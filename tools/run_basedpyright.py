"""Run basedpyright with a usable virtualenv root for modules-repo worktrees."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dev_bootstrap_support import ROOT as REPO_ROOT, ensure_core_dependency


REQUIRED_IMPORTS = ("pydantic", "specfact_cli")


def _candidate_env_roots(repo_root: Path) -> list[Path]:
    candidates: list[Path] = [repo_root]
    for parent in repo_root.parents:
        sibling = parent / "specfact-cli-modules"
        if sibling == repo_root or sibling in candidates:
            continue
        candidates.append(sibling)
    return candidates


def _venv_python(env_root: Path) -> Path:
    return env_root / ".venv" / "bin" / "python"


def _venv_basedpyright(env_root: Path) -> Path:
    return env_root / ".venv" / "bin" / "basedpyright"


def _is_usable_env(env_root: Path) -> bool:
    python_bin = _venv_python(env_root)
    basedpyright_bin = _venv_basedpyright(env_root)
    if not python_bin.exists() or not basedpyright_bin.exists():
        return False
    probe = [
        str(python_bin),
        "-c",
        "import " + ", ".join(REQUIRED_IMPORTS),
    ]
    result = subprocess.run(probe, check=False, capture_output=True, text=True)
    return result.returncode == 0


def _resolve_env_root(repo_root: Path) -> Path:
    for candidate in _candidate_env_roots(repo_root):
        if _is_usable_env(candidate):
            return candidate
    return repo_root


def main() -> int:
    repo_root = REPO_ROOT
    bootstrap_result = ensure_core_dependency(repo_root)
    if bootstrap_result != 0:
        return bootstrap_result
    env_root = _resolve_env_root(repo_root)
    basedpyright_bin = _venv_basedpyright(env_root)
    targets = sys.argv[1:] or ["src", "tests", "tools"]
    command = [
        str(basedpyright_bin) if basedpyright_bin.exists() else "basedpyright",
        "--project",
        str(repo_root / "pyproject.toml"),
        "--venvpath",
        str(env_root),
        *targets,
    ]
    completed = subprocess.run(command, check=False, cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
