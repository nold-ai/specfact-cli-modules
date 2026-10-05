"""Sealed uv launch plans preserve project selections without a host command."""

import json
from pathlib import Path

import pytest

from specfact_code_review.run import native_project_uv
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def test_uv_request_preserves_selection_and_lock(tmp_path: Path):
    value = {
        "schema": "native-uv-request-v1",
        "environment": "default",
        "groups": ["tests"],
        "extras": ["native"],
        "locked": True,
    }
    (tmp_path / ".specfact-uv.json").write_text(json.dumps(value))
    assert native_project_uv.read_request(tmp_path) == value


@pytest.mark.parametrize(
    "changes",
    [{"groups": ["--index=http://host"]}, {"environment": "../host"}, {"locked": "yes"}, {"command": "run sh"}],
)
def test_uv_request_cannot_select_arbitrary_command_or_environment(tmp_path: Path, changes):
    value = {
        "schema": "native-uv-request-v1",
        "environment": "default",
        "groups": [],
        "extras": [],
        "locked": False,
        **changes,
    }
    (tmp_path / ".specfact-uv.json").write_text(json.dumps(value))
    with pytest.raises(ProjectRuntimeError, match="uv_request"):
        native_project_uv.read_request(tmp_path)


def test_uv_sync_uses_fixed_python_and_preserves_existing_lock(tmp_path: Path):
    request = {"groups": ["tests"], "extras": ["native"], "locked": True}
    command = native_project_uv.sync_command(tmp_path / "capsule", tmp_path / "source", tmp_path / "cache", request)
    assert command[:2] == [str(tmp_path / "capsule/tools/uv"), "sync"]
    assert "--locked" in command and "--no-editable" in command
    assert command[command.index("--python") + 1] == str(tmp_path / "capsule/python/bin/python3")
    assert command[-4:] == ["--group", "tests", "--extra", "native"]


def test_uv_disposable_copy_retains_tracked_executable_mode(tmp_path: Path, monkeypatch):
    import os
    import sys

    capsule, project, output, temporary = [tmp_path / name for name in ("capsule", "project", "output", "temporary")]
    for root in (project, output, temporary, capsule / "tools"):
        root.mkdir(parents=True)
    (capsule / "tools/uv").write_bytes(b"verified fixture image")
    (capsule / "tools/uv").chmod(0o500)
    (project / "script").write_text("pass\n")
    (project / "script").chmod(0o500)
    (project / ".specfact-uv.json").write_text(
        json.dumps(
            {"schema": native_project_uv.SCHEMA, "environment": "default", "groups": [], "extras": [], "locked": False}
        )
    )
    monkeypatch.setattr(sys, "argv", ["worker", *map(str, (capsule, project, output, temporary))])
    original = Path.cwd()

    def execute(*_args):
        assert Path("script").stat().st_mode & 0o111

    monkeypatch.setattr(os, "execve", execute)
    try:
        assert native_project_uv.main() == 76
    finally:
        os.chdir(original)
