"""Dynamic package versions bind to sanitized, exact source VCS context."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from specfact_code_review.run import portable_snapshot, runner, runtime_builder, scope
from specfact_code_review.run.portable_snapshot import discover_snapshot
from specfact_code_review.run.runtime_builder import copy_project
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_sources import verify_inputs
from specfact_code_review.run.runtime_vcs import copy_vcs_context, vcs_context


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


@pytest.fixture(name="staged_project")
def staged_project_fixture(tmp_path: Path):
    root = tmp_path / "project"
    _repository(root)
    _git(root, "mv", "app.py", "renamed.py")
    resolution = scope.resolve_scope(scope.ScopeRequest(repository=root, scope="index", portable_project_runtime=True))
    assert resolution.status == "PASS"
    try:
        yield root, resolution
    finally:
        scope.cleanup_scope_resolution(resolution)


def test_staged_snapshot_binds_captured_tree_independently_of_live_index(staged_project) -> None:
    root, resolution = staged_project
    snapshot = resolution.head_snapshot
    plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
    assert plan.vcs["tree"] == snapshot.tree
    assert plan.vcs["tree"] != resolution.base_snapshot.tree
    _git(root, "read-tree", "HEAD")
    verify_inputs(plan)
    assert vcs_context(root, plan.vcs["commit"], tree=snapshot.tree) == plan.vcs


def test_private_build_index_retains_staged_rename_and_head(staged_project, tmp_path: Path) -> None:
    root, resolution = staged_project
    snapshot = resolution.head_snapshot
    copied = tmp_path / "build-copy"
    copy_project(snapshot.root, copied, include_vcs=False)
    copy_vcs_context(root, copied, resolution.base_snapshot.commit, tree=snapshot.tree)
    assert _git(copied, "rev-parse", "HEAD") == resolution.base_snapshot.commit
    assert _git(copied, "write-tree") == snapshot.tree
    assert _git(copied, "ls-files") == "renamed.py"
    assert _git(copied, "diff", "--name-only") == ""
    assert "renamed.py" in _git(copied, "diff", "--cached", "--name-only")


def test_index_snapshot_keeps_captured_commit_when_repository_head_moves(staged_project) -> None:
    root, resolution = staged_project
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
        "advance HEAD",
    )
    assert _git(root, "rev-parse", "HEAD") != resolution.base_snapshot.commit
    snapshot = resolution.head_snapshot
    plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
    assert plan.vcs["commit"] == resolution.base_snapshot.commit
    assert plan.vcs["tree"] == snapshot.tree


def test_builder_attaches_captured_tree_before_dependency_installation(
    staged_project, tmp_path: Path, monkeypatch
) -> None:
    _root, resolution = staged_project
    snapshot = resolution.head_snapshot
    plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
    staging = tmp_path / "staging"
    staging.mkdir()

    def stop_after_vcs(*_args, **_kwargs):
        raise RuntimeError("stop before dependency acquisition")

    monkeypatch.setattr(runtime_builder, "stage_git", stop_after_vcs)
    with pytest.raises(RuntimeError, match="stop before dependency acquisition"):
        runtime_builder._build(plan, object(), staging)
    assert _git(staging / "project", "write-tree") == snapshot.tree
    assert _git(staging / "project", "ls-files") == "renamed.py"


@pytest.mark.parametrize("changed_state", ["head", "index"])
def test_real_cached_analysis_snapshot_preserves_portable_vcs_provenance(
    staged_project, tmp_path: Path, monkeypatch, changed_state: str
) -> None:
    root, resolution = staged_project
    monkeypatch.chdir(root)
    destination = tmp_path / "cached"
    destination.mkdir()
    snapshot = runner._cached_analysis_snapshot([Path("renamed.py")], destination)
    assert snapshot is not None
    if changed_state == "head":
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
            "advance HEAD",
        )
    else:
        _git(root, "read-tree", "HEAD")
    plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
    assert plan.vcs["commit"] == resolution.base_snapshot.commit
    assert plan.vcs["tree"] == resolution.head_snapshot.tree
    assert plan.vcs["tree"] == snapshot.diff.index_tree
    copied = tmp_path / "cached-build"
    copy_project(snapshot.root, copied, include_vcs=False)
    copy_vcs_context(root, copied, plan.vcs["commit"], tree=plan.vcs["tree"])
    assert _git(copied, "write-tree") == snapshot.diff.index_tree
    assert _git(copied, "ls-files") == "renamed.py"


def test_cached_capture_rejects_head_commit_change_with_identical_tree(
    staged_project, tmp_path: Path, monkeypatch
) -> None:
    root, _resolution = staged_project
    monkeypatch.chdir(root)
    destination = tmp_path / "cached-race"
    destination.mkdir()
    original = runner._git_tree_identity

    def move_head_after_index(repository: Path, revision: str):
        result = original(repository, revision)
        if revision == "index":
            previous = _git(root, "rev-parse", "HEAD")
            tree = _git(root, "rev-parse", "HEAD^{tree}")
            commit = _git(
                root,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.test",
                "commit-tree",
                tree,
                "-p",
                previous,
                "-m",
                "same tree new commit",
            )
            _git(root, "update-ref", "HEAD", commit)
        return result

    monkeypatch.setattr(runner, "_git_tree_identity", move_head_after_index)
    assert runner._cached_analysis_snapshot([Path("renamed.py")], destination) is None
