"""Packaged SCM admission without host executable discovery or version overrides."""

import os
import plistlib
import shutil

import pytest

from specfact_code_review.run import native_managed_process as managed


class Transport:
    def __init__(self):
        self.requests = []

    def exchange(self, opcode, handle=0, payload=b""):
        if opcode == managed.LAUNCH:
            self.requests.append(plistlib.loads(payload))
            return managed.WorkerReply(1, -1, b"")
        return managed.WorkerReply(1, 0, b"")


@pytest.fixture
def git_adapter(tmp_path, monkeypatch):
    roots = {name: (tmp_path / name).resolve() for name in ("project", "output", "temporary")}
    for root in roots.values():
        root.mkdir()
    (roots["project"] / ".git").mkdir()
    image = tmp_path / "capsule/tools/git"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"verified capsule fixture")
    image.chmod(0o555)
    transport = Transport()
    monkeypatch.chdir(roots["project"])
    monkeypatch.setattr(os, "environ", {"LANG": "C", "PATH": "/host/bin", "PYTHONPATH": "/host/overlay"})
    adapter = managed.ManagedSubprocess(transport, roots=roots, executables={str(image): "git", "git": "git"})
    return adapter, transport, image


@pytest.mark.parametrize(
    "query",
    [
        ["describe", "--dirty", "--tags", "--long", "--match", "hatch-v*"],
        ["rev-parse", "--show-prefix"],
        ["-c", "log.showSignature=false", "log", "-n", "1", "HEAD", "--format=%cI"],
        ["status", "--porcelain", "--untracked-files=no"],
    ],
)
def test_git_scm_queries_use_packaged_identity_and_no_python_overlay(git_adapter, query):
    adapter, transport, image = git_adapter
    for executable in ("git", str(image)):
        adapter.popen([executable, "--git-dir", str(adapter.roots["project"] / ".git"), *query])
        request = transport.requests[-1]
        assert request["program"] == "git"
        assert request["python_paths"] == []
        assert request["python_prefix"] == request["python_alias"] == ""
        assert request["environment"]["LANG"] == "C"
        assert not {"PATH", "HOME", "TMPDIR", "PYTHONPATH"} & request["environment"].keys()


@pytest.mark.parametrize(
    "args",
    [
        ["fetch", "--unshallow"],
        ["clone", "https://example.invalid/project"],
        ["config", "core.hooksPath", "/host/hooks"],
        ["-c", "alias.q=!touch /tmp/marker", "q"],
        ["--git-dir=/host/repo", "describe"],
        ["-C", "/usr", "rev-parse", "HEAD"],
        ["symbolic-ref", "HEAD", "refs/heads/new"],
        ["describe", "--broken"],
    ],
)
def test_git_rejects_non_scm_commands_and_foreign_repository_selectors(git_adapter, args):
    adapter, transport, image = git_adapter
    with pytest.raises(managed.ManagedProcessError):
        adapter.popen([str(image), *args])
    assert not transport.requests


def test_git_rejects_environment_configuration_and_writable_image(git_adapter):
    adapter, transport, image = git_adapter
    for environment in ({"GIT_CONFIG_COUNT": "1"}, {"GIT_DIR": "/host/repo"}, {"GIT_SSH": "/host/ssh"}):
        with pytest.raises(managed.ManagedProcessError):
            adapter.popen([str(image), "--version"], env=environment)
    image.chmod(0o755)
    with pytest.raises(managed.ManagedProcessError):
        adapter.popen(["git", "--version"])
    assert not transport.requests


def test_git_discovery_uses_capsule_image_without_host_path(git_adapter, monkeypatch):
    adapter, _transport, image = git_adapter
    monkeypatch.setattr(managed, "NativeWorkerChannel", Transport)
    previous = shutil.which
    with managed.installed_subprocess(image.parents[1], *adapter.roots.values()):
        assert shutil.which("git") == str(image)
        assert shutil.which("/usr/bin/git") is None
        assert shutil.which("git", path="/host/bin") == str(image)
    assert shutil.which is previous


def test_git_fixed_bootstrap_environment_cannot_be_shadowed(git_adapter):
    adapter, transport, image = git_adapter
    adapter.popen([str(image), "--version"], env={"XDG_CONFIG_HOME": "/host/config", "LC_ALL": "untrusted-locale"})
    assert transport.requests[-1]["environment"] == {}


@pytest.mark.parametrize(
    "cwd,args",
    [
        (".", ["--git-dir", ".git", "describe", "--tags"]),
        (".", ["--git-dir=.git", "rev-parse", "HEAD"]),
        (".", ["-C", "member", "rev-parse", "--show-prefix"]),
        ("member", ["--git-dir", ".git", "rev-parse", "HEAD"]),
    ],
)
def test_git_relative_cwd_uses_the_same_admitted_base_as_subprocess(git_adapter, cwd, args):
    adapter, transport, image = git_adapter
    member = adapter.roots["project"] / "member"
    member.mkdir()
    (member / ".git").mkdir()
    adapter.popen([str(image), *args], cwd=cwd)
    request = transport.requests[-1]
    assert request["cwd"] == ("project" if cwd == "." else "project/member")
    assert request["argv"] == args
    assert request["program"] == "git"


@pytest.mark.parametrize(
    "cwd,args",
    [
        ("../project", ["--git-dir", ".git", "rev-parse", "HEAD"]),
        ("/usr", ["-C", ".", "rev-parse", "HEAD"]),
        (".", ["-C", "../project", "rev-parse", "HEAD"]),
        (".", ["--git-dir", "/usr", "rev-parse", "HEAD"]),
        (".", ["--git-dir", "foreign-link", "rev-parse", "HEAD"]),
    ],
)
def test_git_relative_cwd_does_not_relax_grants_or_canonical_paths(git_adapter, cwd, args):
    adapter, transport, image = git_adapter
    (adapter.roots["project"] / "foreign-link").symlink_to("/usr")
    with pytest.raises(managed.ManagedProcessError):
        adapter.popen([str(image), *args], cwd=cwd)
    assert not transport.requests
