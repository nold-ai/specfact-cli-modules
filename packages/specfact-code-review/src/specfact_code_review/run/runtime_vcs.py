"""Sanitized VCS context for version-aware private project builds."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from icontract import require

from specfact_code_review.run.runtime_models import ProjectRuntimeError


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "core.hooksPath=/dev/null", *arguments],
        env={"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode:
        raise ProjectRuntimeError("project_git_snapshot_failed:" + arguments[0])
    return result.stdout.strip()


@require(lambda root: root.is_dir())
def vcs_context(root: Path, commit: str = "HEAD") -> dict[str, str]:
    """Bind commits, tags and shallow boundaries without importing user Git config."""
    if not (root / ".git").exists():
        return {}
    selected = _git(root, "rev-parse", "--verify", commit + "^{commit}")
    shallow = _git(root, "rev-parse", "--git-path", "shallow")
    boundary = Path(shallow)
    if not boundary.is_absolute():
        boundary = root / boundary
    return {
        "commit": selected,
        "tags": _git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/tags"),
        "shallow": boundary.read_text(encoding="ascii") if boundary.is_file() else "",
    }


@require(lambda source, destination: source.is_dir() and destination.is_dir())
def copy_vcs_context(source: Path, destination: Path, commit: str = "HEAD") -> None:
    """Copy metadata, remove local configuration, and populate the selected index."""
    if not (source / ".git").exists():
        return
    selected = vcs_context(source, commit)["commit"]
    with tempfile.TemporaryDirectory(prefix="specfact-build-git-", dir=destination.parent) as directory:
        clone = Path(directory) / "clone"
        _git(source, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(source), str(clone))
        shutil.move(str(clone / ".git"), destination / ".git")
    (destination / ".git/config").write_text(
        "[core]\nrepositoryformatversion = 0\nbare = false\nhooksPath = /dev/null\n", encoding="utf-8"
    )
    shutil.rmtree(destination / ".git/hooks", ignore_errors=True)
    (destination / ".git/HEAD").write_text(selected + "\n", encoding="ascii")
    _git(destination, "read-tree", selected)
