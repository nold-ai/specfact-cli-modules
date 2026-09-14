"""Identify the exact source inputs copied into a disposable project build."""

from __future__ import annotations

import os
from pathlib import Path

from icontract import ensure, require

from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError, content_digest, document_digest
from specfact_code_review.run.runtime_vcs import vcs_context


IGNORED_INPUTS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".tox",
        ".specfact",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".env",
        ".coverage",
    }
)


@ensure(lambda result, root: result.is_relative_to(root))
def source_link_target(path: Path, root: Path) -> Path:
    """Apply the same exclusion boundary to aliases and ordinary source paths."""
    relative = path.relative_to(root).as_posix()
    try:
        target = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ProjectRuntimeError(f"project_source_symlink_invalid:{relative}") from exc
    if not target.is_relative_to(root) or target == root or path.is_relative_to(target):
        raise ProjectRuntimeError(f"project_source_symlink_escape:{relative}")
    if set(target.relative_to(root).parts) & IGNORED_INPUTS:
        raise ProjectRuntimeError(f"project_source_symlink_excluded:{relative}")
    return target


def _source_entry(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root).as_posix()
    if path.is_symlink():
        return "link:" + source_link_target(path, root).relative_to(root).as_posix()
    if path.is_file():
        return content_digest(path.read_bytes())
    if not path.is_dir():
        raise ProjectRuntimeError(f"project_source_special_file:{relative}")
    return None


@ensure(lambda result: result.startswith("sha256:") and len(result) == 71)
def source_identity(root: Path) -> str:
    """Bind locally built packages and workspace members to their actual bytes."""
    entries = {}
    for directory, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORED_INPUTS)
        names = [*directories, *(name for name in sorted(files) if name not in IGNORED_INPUTS)]
        for name in names:
            path = Path(directory) / name
            identity = _source_entry(path, root)
            if identity is not None:
                entries[path.relative_to(root).as_posix()] = identity
    return document_digest(entries)


@require(lambda plan: plan.root.is_dir())
def verify_inputs(plan: ProjectPlan) -> None:
    """Verify the selected input set without rediscovering a different environment."""
    for name, expected in plan.inputs.items():
        path = plan.root / name
        if path.is_symlink() or not path.is_file() or content_digest(path.read_bytes()) != expected:
            raise ProjectRuntimeError(f"project_runtime_inputs_changed_during_build:{name}")
    if vcs_context(plan.vcs_repository or plan.root, plan.vcs.get("commit", "HEAD")) != plan.vcs:
        raise ProjectRuntimeError("project_runtime_vcs_changed_during_build")
    if source_identity(plan.root) != plan.source_identity:
        raise ProjectRuntimeError("project_runtime_source_changed_during_build")
