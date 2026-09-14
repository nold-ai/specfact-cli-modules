"""Dynamic package versions bind to sanitized, exact source VCS context."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from specfact_code_review.run import portable_snapshot, runner, runtime_builder, runtime_vcs, scope
from specfact_code_review.run.portable_snapshot import discover_snapshot
from specfact_code_review.run.runtime_builder import copy_project
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError
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


def _commit_fixture(root: Path, message: str) -> str:
    _git(root, "add", "-A")
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
        message,
    )
    return _git(root, "rev-parse", "HEAD")


def _annotated_tag(root: Path, name: str, message: str) -> None:
    _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "tag",
        "-a",
        name,
        "-m",
        message,
    )


@pytest.mark.parametrize("packed", [False, True])
def test_private_git_contains_only_bound_objects_and_tag_refs(tmp_path: Path, packed: bool) -> None:
    root = tmp_path / "source"
    _repository(root)
    _annotated_tag(root, "v1", "bound annotated tag")
    _git(root, "tag", "lightweight")
    (root / "app.py").write_text("VALUE = 2\n")
    selected = _commit_fixture(root, "selected ancestry")
    _git(root, "checkout", "--orphan", "unrelated")
    _git(root, "rm", "-rf", ".")
    (root / "private.txt").write_text("unbound branch data")
    unrelated = _commit_fixture(root, "unrelated branch")
    _git(root, "update-ref", "refs/remotes/origin/private", unrelated)
    _git(root, "checkout", "--detach", selected)
    if packed:
        _git(root, "repack", "-ad")
    secret = tmp_path / "unreachable.txt"
    secret.write_text("unreachable object data")
    unreachable = _git(root, "hash-object", "-w", str(secret))
    before = vcs_context(root, selected)
    copied = tmp_path / "copy"
    copied.mkdir()
    copy_vcs_context(root, copied, selected)
    expected = set(
        _git(
            root, "rev-list", "--objects", "--no-object-names", selected, "refs/tags/v1", "refs/tags/lightweight"
        ).splitlines()
    )
    actual = set(_git(copied, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").splitlines())
    assert actual == expected
    assert unrelated not in actual and unreachable not in actual
    assert _git(copied, "for-each-ref", "--format=%(refname)") == "refs/tags/lightweight\nrefs/tags/v1"
    assert _git(copied, "describe", "--tags", "HEAD") == _git(root, "describe", "--tags", selected)
    assert _git(copied, "rev-list", "--count", "HEAD") == "2"
    assert vcs_context(root, selected) == before


def test_private_git_preserves_bound_shallow_history_and_annotated_tag(tmp_path: Path) -> None:
    original = tmp_path / "original"
    _repository(original)
    ancestor = _git(original, "rev-parse", "HEAD")
    (original / "app.py").write_text("VALUE = 2\n")
    selected = _commit_fixture(original, "shallow tip")
    _annotated_tag(original, "v2", "tip tag")
    source = tmp_path / "shallow"
    _git(original, "clone", "--quiet", "--depth=1", original.as_uri(), str(source))
    copied = tmp_path / "copy"
    copied.mkdir()
    copy_vcs_context(source, copied)
    assert _git(copied, "rev-parse", "HEAD") == selected
    assert _git(copied, "describe", "--tags", "HEAD") == "v2"
    assert _git(copied, "rev-parse", "--is-shallow-repository") == "true"
    assert _git(copied, "rev-list", "--count", "HEAD") == "1"
    assert vcs_context(copied) == vcs_context(source)
    objects = _git(copied, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").splitlines()
    assert ancestor not in objects


def test_unbound_replacement_ref_cannot_change_selected_vcs_context(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _repository(root)
    ancestor = _git(root, "rev-parse", "HEAD")
    (root / "app.py").write_text("VALUE = 2\n")
    selected = _commit_fixture(root, "selected")
    before = vcs_context(root)
    _git(root, "replace", selected, ancestor)
    assert vcs_context(root) == before
    copied = tmp_path / "copy"
    copied.mkdir()
    copy_vcs_context(root, copied)
    assert _git(copied, "rev-parse", "HEAD^{tree}") == before["tree"]
    assert not _git(copied, "for-each-ref", "--format=%(refname)", "refs/replace")


def test_missing_promisor_object_does_not_run_host_transport(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _repository(root)
    blob = _git(root, "rev-parse", "HEAD:app.py")
    marker = tmp_path / "transport-executed"
    transport = tmp_path / "transport.sh"
    transport.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n")
    transport.chmod(0o700)
    _git(root, "config", "core.repositoryformatversion", "1")
    _git(root, "config", "extensions.partialClone", "origin")
    _git(root, "config", "remote.origin.promisor", "true")
    _git(root, "config", "remote.origin.url", "ssh://example.invalid/project")
    _git(root, "config", "core.sshCommand", str(transport))
    (root / ".git/objects" / blob[:2] / blob[2:]).unlink()
    copied = tmp_path / "copy"
    copied.mkdir()
    with pytest.raises(ValueError, match="project_git_snapshot_failed"):
        copy_vcs_context(root, copied)
    assert not marker.exists()
    assert not (copied / ".git").exists()


def test_unbound_grafts_cannot_remove_selected_ancestry(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _repository(root)
    (root / "app.py").write_text("VALUE = 2\n")
    selected = _commit_fixture(root, "selected")
    before = vcs_context(root)
    (root / ".git/info/grafts").write_text(selected + "\n")
    assert vcs_context(root) == before
    copied = tmp_path / "copy"
    copied.mkdir()
    copy_vcs_context(root, copied)
    assert _git(copied, "rev-list", "--count", "HEAD") == "2"
    assert not (copied / ".git/info/grafts").exists()


@pytest.mark.parametrize(
    "failure",
    [subprocess.TimeoutExpired("git", 120, stderr=b"private transport detail"), OSError("private filesystem detail")],
)
def test_git_export_failure_uses_runtime_diagnostic(tmp_path: Path, monkeypatch, failure: Exception) -> None:
    def raise_export_failure(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(runtime_vcs.subprocess, "run", raise_export_failure)
    with pytest.raises(ProjectRuntimeError, match="project_git_snapshot_failed:rev-list") as caught:
        runtime_vcs._git_bytes(tmp_path, "rev-list", "--objects", "HEAD")
    assert caught.value.__cause__ is failure
    assert "private" not in str(caught.value)


def test_frozen_vcs_tags_exclude_newly_added_tag_history(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _repository(root)
    bound = vcs_context(root)
    unrelated = _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit-tree",
        bound["tree"],
        "-m",
        "unbound commit",
    )
    _git(root, "tag", "late", unrelated)
    copied = tmp_path / "copy"
    copied.mkdir()
    copy_vcs_context(root, copied, bound_vcs=bound)
    assert not _git(copied, "for-each-ref", "--format=%(refname)")
    assert unrelated not in _git(copied, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").splitlines()


def test_frozen_shallow_boundary_controls_object_traversal(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _repository(root)
    (root / "app.py").write_text("VALUE = 2\n")
    selected = _commit_fixture(root, "selected")
    bound = vcs_context(root)
    (root / ".git/shallow").write_text(selected + "\n")
    copied = tmp_path / "copy"
    copied.mkdir()
    copy_vcs_context(root, copied, bound_vcs=bound)
    assert _git(copied, "rev-parse", "--is-shallow-repository") == "false"
    assert _git(copied, "rev-list", "--count", "HEAD") == "2"


def test_builder_copies_frozen_plan_refs_after_input_verification(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "source"
    _repository(root)
    plan = discover_project(root)
    unrelated = _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit-tree",
        plan.vcs["tree"],
        "-m",
        "unbound commit",
    )
    staging = tmp_path / "staging"
    staging.mkdir()

    def change_tags_after_verification(selected_plan):
        verify_inputs(selected_plan)
        _git(root, "tag", "late", unrelated)

    def stop_before_acquisition(*_args, **_kwargs):
        raise RuntimeError("stop before acquisition")

    monkeypatch.setattr(runtime_builder, "verify_inputs", change_tags_after_verification)
    monkeypatch.setattr(runtime_builder, "stage_git", stop_before_acquisition)
    with pytest.raises(RuntimeError, match="stop before acquisition"):
        runtime_builder._build(plan, object(), staging)
    assert not _git(staging / "project", "for-each-ref", "--format=%(refname)")


@pytest.mark.parametrize("immutable", [False, True])
@pytest.mark.parametrize("remove_origin", [False, True])
def test_builder_requires_captured_git_origin_after_verification(
    tmp_path: Path, monkeypatch, immutable: bool, remove_origin: bool
) -> None:
    root = tmp_path / "source"
    _repository(root)
    snapshot = scope._materialize_commit(root, _git(root, "rev-parse", "HEAD")) if immutable else None
    try:
        plan = (
            discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
            if snapshot is not None
            else discover_project(root)
        )
        staging = tmp_path / "staging"
        staging.mkdir()
        acquisition = []

        def remove_git_after_verification(selected_plan):
            verify_inputs(selected_plan)
            if remove_origin:
                (root / ".git").rename(tmp_path / "removed-git")

        def stop_before_acquisition(*_args, **_kwargs):
            acquisition.append(True)
            assert _git(staging / "project", "rev-parse", "HEAD") == plan.vcs["commit"]
            raise RuntimeError("stop before acquisition")

        monkeypatch.setattr(runtime_builder, "verify_inputs", remove_git_after_verification)
        monkeypatch.setattr(runtime_builder, "stage_git", stop_before_acquisition)
        expected = ProjectRuntimeError if remove_origin else RuntimeError
        diagnostic = "project_git_snapshot_origin_missing" if remove_origin else "stop before acquisition"
        with pytest.raises(expected, match=diagnostic):
            runtime_builder._build(plan, object(), staging)
        assert bool(acquisition) is not remove_origin
        if remove_origin:
            assert not (staging / "project/.git").exists()
    finally:
        if snapshot is not None:
            shutil.rmtree(snapshot.root)
