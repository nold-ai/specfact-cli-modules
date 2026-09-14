"""Sanitized VCS context for version-aware private project builds."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from icontract import require

from specfact_code_review.run.runtime_models import ProjectRuntimeError


def _git_result(
    root: Path, *arguments: str, input_data: bytes | None = None, shallow_file: Path | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "core.hooksPath=/dev/null",
                *(["--shallow-file", str(shallow_file)] if shallow_file is not None else []),
                *arguments,
            ],
            env={
                "PATH": os.defpath,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_GRAFT_FILE": os.devnull,
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_ALLOW_PROTOCOL": "",
                "GIT_TERMINAL_PROMPT": "0",
            },
            input=input_data,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProjectRuntimeError(
            f"project_git_snapshot_failed:{arguments[0]}:{type(exc).__name__}; retry local metadata export"
        ) from exc


def _git_bytes(root: Path, *arguments: str, input_data: bytes | None = None, shallow_file: Path | None = None) -> bytes:
    result = _git_result(root, *arguments, input_data=input_data, shallow_file=shallow_file)
    if result.returncode:
        raise ProjectRuntimeError(
            "project_git_snapshot_failed:"
            + arguments[0]
            + "; ensure required Git objects are available locally; metadata export disables network acquisition"
        )
    return result.stdout


def _git(root: Path, *arguments: str) -> str:
    return _git_bytes(root, *arguments).decode("utf-8").strip()


def _unborn_head(root: Path) -> bool:
    reference = _git_result(root, "symbolic-ref", "--quiet", "HEAD")
    if reference.returncode:
        return False
    branch = reference.stdout.decode("utf-8").strip()
    return (
        branch.startswith("refs/heads/")
        and _git_result(root, "show-ref", "--verify", "--quiet", branch).returncode == 1
    )


@require(lambda root: root.is_dir())
def vcs_context(root: Path, commit: str = "HEAD", *, tree: str | None = None) -> dict[str, str]:
    """Bind commits, tags and shallow boundaries without importing user Git config."""
    if not (root / ".git").exists():
        return {}
    try:
        selected = _git(root, "rev-parse", "--verify", commit + "^{commit}")
    except ProjectRuntimeError as exc:
        if exc.__cause__ is None and commit == "HEAD" and tree is None and _unborn_head(root):
            return {}
        raise
    shallow = _git(root, "rev-parse", "--git-path", "shallow")
    boundary = Path(shallow)
    if not boundary.is_absolute():
        boundary = root / boundary
    return {
        "commit": selected,
        "tree": _git(root, "rev-parse", "--verify", (tree or selected) + "^{tree}"),
        "tags": _git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/tags"),
        "shallow": boundary.read_text(encoding="ascii") if boundary.is_file() else "",
    }


def _copy_bound_objects(source: Path, private: Path, selected: dict[str, str]) -> None:
    tags = dict(line.rsplit(" ", 1) for line in selected["tags"].splitlines())
    roots = {selected["commit"], selected["tree"], *tags.values()}
    objects = _git_bytes(
        source,
        "rev-list",
        "--objects",
        "--no-object-names",
        "--stdin",
        input_data=("\n".join(sorted(roots)) + "\n").encode("ascii"),
        shallow_file=private / ".git/shallow",
    )
    pack_prefix = private / ".git/objects/pack/pack"
    _git_bytes(
        source,
        "pack-objects",
        "--no-reuse-delta",
        str(pack_prefix),
        input_data=objects,
        shallow_file=private / ".git/shallow",
    )
    actual = _git(private, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)")
    if set(actual.splitlines()) != set(objects.decode("ascii").splitlines()):
        raise ProjectRuntimeError("project_git_snapshot_object_closure_mismatch")
    for name, identity in tags.items():
        _git(private, "update-ref", name, identity)


@require(lambda source, destination: source.is_dir() and destination.is_dir())
def copy_vcs_context(
    source: Path,
    destination: Path,
    commit: str = "HEAD",
    *,
    tree: str | None = None,
    bound_vcs: dict[str, str] | None = None,
) -> None:
    """Transfer only identity-bound history and staged objects into fresh metadata."""
    if not (source / ".git").exists():
        if bound_vcs:
            raise ProjectRuntimeError(
                "project_git_snapshot_origin_missing; restore captured repository metadata and retry"
            )
        return
    selected = dict(bound_vcs) if bound_vcs is not None else vcs_context(source, commit, tree=tree)
    if not selected:
        return
    with tempfile.TemporaryDirectory(prefix="specfact-build-git-", dir=destination.parent) as directory:
        private = Path(directory) / "repository"
        object_format = _git(source, "rev-parse", "--show-object-format")
        _git(source, "init", "--quiet", "--template=", f"--object-format={object_format}", str(private))
        _git(private, "config", "--local", "core.hooksPath", "/dev/null")
        (private / ".git/shallow").write_text(selected["shallow"], encoding="ascii")
        _copy_bound_objects(source, private, selected)
        if not selected["shallow"]:
            (private / ".git/shallow").unlink()
        (private / ".git/HEAD").write_text(selected["commit"] + "\n", encoding="ascii")
        _git(private, "read-tree", selected["tree"])
        shutil.move(str(private / ".git"), destination / ".git")
