from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specfact_code_review.run import runner


def _project(tmp_path: Path, *, environment: bool) -> tuple[Path, Path]:
    project = tmp_path / "project"
    nested = project / ".local" / "verify-py311"
    nested.mkdir(parents=True)
    (project / "app.py").write_text("VALUE = 1\n")
    (project / ".gitignore").write_text("/.local/\n")
    if environment:
        (nested / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (nested / "dependency.py").write_text("VALUE = 2\n")
    (nested / "python").symlink_to(tmp_path / "outside-python")
    (tmp_path / "outside-python").write_text("external interpreter\n")
    env = runner._candidate_git_environment()
    subprocess.run(["git", "init", "-q"], cwd=project, env=env, check=True)
    return project, nested


def test_ignored_nested_environment_is_excluded_from_worktree_identity(tmp_path: Path) -> None:
    project, _ = _project(tmp_path, environment=True)
    identity = runner._worktree_analysis_identity(project, {"app.py": project / "app.py"})
    assert identity is not None
    assert not any(path.path.startswith(".local/verify-py311/") for path in identity.paths)


def test_ignored_nested_environment_is_excluded_from_native_snapshot(tmp_path: Path) -> None:
    project, _ = _project(tmp_path, environment=True)
    snapshot = dict(runner._capture_native_snapshot(project))
    assert snapshot["app.py"] == b"VALUE = 1\n"
    assert not any(path.startswith(".local/verify-py311/") for path in snapshot)


def test_same_directory_without_environment_marker_keeps_alias_rejection(tmp_path: Path) -> None:
    project, _ = _project(tmp_path, environment=False)
    assert runner._worktree_analysis_identity(project, {"app.py": project / "app.py"}) is None
    with pytest.raises(ValueError, match="native_snapshot_alias_escape"):
        runner._capture_native_snapshot(project)


@pytest.mark.parametrize("selected", [False, True])
def test_tracked_or_selected_environment_input_cannot_disappear(tmp_path: Path, selected: bool) -> None:
    project, nested = _project(tmp_path, environment=True)
    (nested / "python").unlink()
    relative = nested.relative_to(project).as_posix() + "/dependency.py"
    files = {"app.py": project / "app.py"}
    if selected:
        files[relative] = nested / "dependency.py"
    else:
        subprocess.run(["git", "add", "-f", relative], cwd=project, env=runner._candidate_git_environment(), check=True)
    assert runner._worktree_analysis_identity(project, files) is None


def test_environment_alias_cannot_make_excluded_dependencies_visible(tmp_path: Path) -> None:
    project, nested = _project(tmp_path, environment=True)
    (project / "linked").symlink_to(nested, target_is_directory=True)
    assert runner._worktree_analysis_identity(project, {"app.py": project / "app.py"}) is None
    with pytest.raises(ValueError, match="native_snapshot_directory_alias_excluded"):
        runner._capture_native_snapshot(project)


def test_native_snapshot_preserves_ordinary_venv_package(tmp_path: Path) -> None:
    package = tmp_path / "src/customer/venv"
    package.mkdir(parents=True)
    (package / "core.py").write_bytes(b"VALUE=7\n")
    assert dict(runner._capture_native_snapshot(tmp_path))["src/customer/venv/core.py"] == b"VALUE=7\n"
    (package / "pyvenv.cfg").write_text("home = /usr/bin\n")
    assert "src/customer/venv/core.py" not in dict(runner._capture_native_snapshot(tmp_path))
