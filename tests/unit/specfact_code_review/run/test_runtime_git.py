"""Git transport helpers and their identity travel with the disposable builder."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runtime_git
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def test_missing_git_https_helper_only_fails_when_used(tmp_path: Path, monkeypatch) -> None:
    git = tmp_path / "git"
    git.write_bytes(b"\x7fELFgit")
    (tmp_path / "git-remote-http").write_bytes(b"\x7fELFhttp")
    monkeypatch.setattr(runtime_git, "GIT", git)
    run = subprocess.run
    monkeypatch.setattr(runtime_git.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout=str(tmp_path)))
    assert set(runtime_git.git_identity()) == {"bin/git", "git-core/git-remote-http"}
    monkeypatch.setattr(runtime_git, "elf_dependencies", lambda _path: ())
    monkeypatch.setattr(runtime_git, "inventory_native", lambda *_args, **_kwargs: None)
    runtime_git.stage_git(tmp_path)
    helper = tmp_path / "builder-tools/git-core/git-remote-https"
    completed = run([sys.executable, str(helper)], capture_output=True, text=True, check=False)
    assert completed.returncode == 127
    assert "project_builder_tool_missing:git-remote-https" in completed.stderr
    assert "install Git HTTP transport helpers" in completed.stderr
    assert not helper.with_name(helper.name + ".real").exists()


def test_missing_git_is_optional_for_identity_and_staging(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_git, "GIT", tmp_path / "unavailable-git")
    assert runtime_git.git_identity() == {}
    runtime_git.stage_git(tmp_path)
    assert not (tmp_path / "builder-tools").exists()


def test_transport_change_invalidates_builder_identity_and_is_staged(tmp_path: Path, monkeypatch) -> None:
    program = tmp_path / "git"
    helper = tmp_path / "http"
    program.write_bytes(b"\x7fELFgit")
    helper.write_bytes(b"\x7fELFhttp")
    monkeypatch.setattr(runtime_git, "GIT", program)
    monkeypatch.setattr(runtime_git, "_programs", lambda: {"bin/git": program, "git-core/git-remote-https": helper})
    before = runtime_git.git_identity()
    helper.write_bytes(b"\x7fELFchanged")
    assert runtime_git.git_identity() != before
    monkeypatch.setattr(runtime_git, "elf_dependencies", lambda path: ("libcurl.so.4",) if path == helper else ())
    observed = []
    monkeypatch.setattr(runtime_git, "inventory_native", lambda *_args, **kwargs: observed.append(kwargs["declared"]))
    runtime_git.stage_git(tmp_path)
    copied = tmp_path / "builder-tools/git-core/git-remote-https.real"
    assert copied.read_bytes() == helper.read_bytes()
    launcher = copied.with_suffix("").read_text()
    assert "GIT_EXEC_PATH" in launcher and "--library-path" in launcher
    assert "libcurl.so.4" in observed[0]


@pytest.mark.parametrize(
    "failure", [subprocess.CalledProcessError(1, "git"), subprocess.TimeoutExpired("git", 10), OSError("unavailable")]
)
def test_git_identity_failures_use_runtime_diagnostic(tmp_path: Path, monkeypatch, failure: Exception) -> None:
    git = tmp_path / "git"
    git.write_bytes(b"\x7fELFgit")
    monkeypatch.setattr(runtime_git, "GIT", git)

    def fail(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(runtime_git.subprocess, "run", fail)
    with pytest.raises(ProjectRuntimeError, match="project_builder_git_identity_failed") as caught:
        runtime_git.git_identity()
    assert caught.value.__cause__ is failure
