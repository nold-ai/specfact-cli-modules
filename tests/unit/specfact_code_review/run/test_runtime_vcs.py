"""Dynamic package versions bind to sanitized, exact source VCS context."""

import os
import shutil
import subprocess
from pathlib import Path

from specfact_code_review.run import portable_snapshot, runner, scope
from specfact_code_review.run.portable_snapshot import discover_snapshot
from specfact_code_review.run.runtime_builder import copy_project
from specfact_code_review.run.runtime_discovery import discover_project


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    ).strip()


def _repository(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "-q")
    (root / "app.py").write_text("VALUE = 1\n")
    _git(root, "add", "app.py")
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


def test_private_copy_has_correct_index_and_retains_source_modifications(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _repository(root)
    copy_project(root, tmp_path / "clean")
    assert _git(tmp_path / "clean", "status", "--porcelain") == ""
    (root / "app.py").write_text("VALUE = 2\n")
    copy_project(root, tmp_path / "dirty")
    assert _git(tmp_path / "dirty", "diff", "--name-only") == "app.py"


def test_tag_change_invalidates_runtime_without_source_byte_changes(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _repository(root)
    before = discover_project(root)
    _git(root, "tag", "v1.0.0")
    after = discover_project(root)
    assert before.source_identity == after.source_identity
    assert before.identity != after.identity


def test_immutable_snapshot_retains_selected_commit_context(tmp_path: Path) -> None:

    root = tmp_path / "project"
    _repository(root)
    commit = _git(root, "rev-parse", "HEAD")
    snapshot = scope._materialize_commit(root, commit)
    try:
        plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
        assert plan.vcs_repository == root
        assert plan.vcs["commit"] == commit
        assert "vcs_repository" not in plan.document()
        assert not (snapshot.root / ".git").exists()
    finally:
        shutil.rmtree(snapshot.root)


def test_vcs_fixtures_never_change_the_calling_hooks_index(tmp_path: Path, monkeypatch) -> None:
    parent = tmp_path / "parent"
    _repository(parent)
    index = parent / ".git/index"
    before = index.read_bytes()
    monkeypatch.setenv("GIT_INDEX_FILE", str(index))
    _repository(tmp_path / "child")
    assert index.read_bytes() == before


def test_analyzer_copy_excludes_reachable_git_history(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "project"
    _repository(root)
    observed = []

    def analyze(_runtime, *, snapshot_root, **_kwargs):
        assert not (snapshot_root / ".git").exists()
        assert (snapshot_root / "app.py").read_text() == "VALUE = 1\n"
        observed.append(snapshot_root)

    monkeypatch.setattr(runner, "_run_capsule_snapshot", analyze)
    request = portable_snapshot.ProjectSnapshotRequest(
        root, [root / "app.py"], runner.ReviewOptions(), "explicit_files"
    )
    portable_snapshot._run_in_private_source(object(), request, runner.CapsuleSnapshotSettings())
    assert observed and (root / ".git/objects").is_dir()
