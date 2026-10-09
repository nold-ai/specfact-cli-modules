from __future__ import annotations

from pathlib import Path

import pytest

from specfact_code_review.run import native_project_runtime, runner
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError
from specfact_code_review.run.runtime_sources import source_identity


def _project(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "fixtures" / "actual" / "empty").mkdir(parents=True)
    (source / "fixtures" / "actual" / "data.pem").write_bytes(b"fixture data")
    (source / "fixtures" / "alias").symlink_to("actual", target_is_directory=True)
    (source / "fixture.pem").symlink_to("fixtures/actual/data.pem")
    (source / "venv").mkdir()
    (source / "venv/ordinary.py").write_bytes(b"ordinary source")
    return source


def test_native_source_aliases_are_materialized_before_runtime_sealing(tmp_path: Path) -> None:
    source = _project(tmp_path)
    before = source_identity(source)
    copied = tmp_path / "snapshot"
    native_project_runtime._copy_native_snapshot(discover_project(source), copied)
    native_project_runtime._runtime_tree(copied)
    assert (copied / "fixtures/alias/data.pem").read_bytes() == b"fixture data"
    assert (copied / "fixtures/alias/empty").is_dir()
    assert (copied / "fixture.pem").read_bytes() == b"fixture data"
    assert (copied / "venv/ordinary.py").read_bytes() == b"ordinary source"
    assert not any(path.is_symlink() for path in copied.rglob("*"))
    assert source_identity(source) == before
    assert (source / "fixtures/alias").is_symlink()


def test_native_source_directory_cycle_rejects_before_sealing(tmp_path: Path) -> None:
    source = _project(tmp_path)
    (source / "other").mkdir()
    (source / "other/back").symlink_to("../fixtures/actual", target_is_directory=True)
    (source / "fixtures/actual/back").symlink_to("../../other", target_is_directory=True)
    with pytest.raises(ValueError, match="native_snapshot_directory_alias_cycle"):
        native_project_runtime._copy_native_snapshot(discover_project(source), tmp_path / "snapshot")


def test_native_source_alias_capture_detects_private_snapshot_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _project(tmp_path)
    capture = runner._capture_native_snapshot

    def changed(root, **kwargs):
        entries = capture(root, **kwargs)
        (root / "fixtures/actual/data.pem").write_bytes(b"substituted")
        return entries

    monkeypatch.setattr(runner, "_capture_native_snapshot", changed)
    with pytest.raises(ProjectRuntimeError, match="project_runtime_source_changed_during_copy"):
        native_project_runtime._copy_native_snapshot(discover_project(source), tmp_path / "snapshot")


@pytest.mark.parametrize("bad", ["external", "excluded"])
def test_native_source_alias_rejects_outside_or_environment_targets(tmp_path: Path, bad: str) -> None:
    source = _project(tmp_path)
    target = tmp_path / "outside" if bad == "external" else source / "environment"
    target.mkdir()
    (target / "data.pem").write_bytes(b"excluded")
    if bad == "excluded":
        (target / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (source / "bad").symlink_to(target, target_is_directory=True)
    if bad == "external":
        with pytest.raises(ProjectRuntimeError, match="project_source_symlink_escape"):
            discover_project(source)
    else:
        copied = tmp_path / "snapshot"
        native_project_runtime._copy_native_snapshot(discover_project(source), copied)
        assert not (copied / "bad").exists()
        assert not (copied / "environment").exists()


def test_alias_projection_preserves_executable_source_and_alias_target(tmp_path: Path) -> None:
    source = _project(tmp_path)
    helper = source / "helper.py"
    helper.write_text("#!/usr/bin/env python3\n")
    helper.chmod(0o755)
    (source / "helper-alias.py").symlink_to("helper.py")
    copied = tmp_path / "snapshot"
    native_project_runtime._copy_native_snapshot(discover_project(source), copied)
    assert (copied / "helper.py").stat().st_mode & 0o100
    assert (copied / "helper-alias.py").stat().st_mode & 0o100
    assert not (copied / "fixture.pem").stat().st_mode & 0o111


def test_alias_projection_cleans_owned_read_only_original_directories(tmp_path: Path) -> None:
    source = _project(tmp_path)
    locked = source / "fixtures/actual"
    locked.chmod(0o555)
    copied = tmp_path / "snapshot"
    try:
        native_project_runtime._copy_native_snapshot(discover_project(source), copied)
        assert (copied / "fixtures/alias/data.pem").read_bytes() == b"fixture data"
        assert not list(tmp_path.glob(".materializing-*"))
        assert locked.stat().st_mode & 0o777 == 0o555
    finally:
        locked.chmod(0o755)
