"""Portable authority/path checks for the required committed-tree CI validation."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.tools.contract_runner import _scan_file


entry = importlib.import_module("scripts.owner_commit_entry")


@pytest.fixture(name="owner")
def committed_repository_fixture(tmp_path):
    return SimpleNamespace(root=tmp_path)


@pytest.mark.parametrize(
    "failure", [None, "integrated-type", "shallow", "history", "commit", "blob", "ancestry", "source-type"]
)
def test_owner_entry_selects_only_valid_integrated_or_approved_bootstrap(owner, monkeypatch, failure):
    integrated = failure == "integrated-type"
    calls = []

    def git(_root, *args):
        calls.append(args)
        if args[:2] == ("cat-file", "-t"):
            if args[2] == entry.BOOTSTRAP_COMMIT:
                return "blob" if failure == "commit" else "commit"
            return "tree" if failure in {"integrated-type", "source-type"} else "blob"
        if args == ("rev-parse", "--is-shallow-repository"):
            return "true" if failure == "shallow" else "false"
        if args[0] == "log":
            return "old-checker-history" if failure == "history" else ""
        assert args[:2] == ("rev-parse", "--verify")
        return "wrong" if failure == "blob" else entry.BOOTSTRAP_BLOB

    def process(command, **options):
        assert options["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        if "--is-ancestor" in command:
            return SimpleNamespace(returncode=0 if failure == "ancestry" else 1)
        return SimpleNamespace(returncode=0 if integrated else 128)

    monkeypatch.setattr(entry, "_git", git)
    monkeypatch.setattr(entry.subprocess, "run", process)
    if failure:
        with pytest.raises(ValueError):
            entry._checker_source(owner.root, "d" * 40)
    else:
        assert entry._checker_source(owner.root, "d" * 40) == f"{entry.BOOTSTRAP_COMMIT}:{entry.CHECKER}"
        assert any(args[0] == "log" for args in calls)


def test_owner_entry_integrated_checker_precedes_bootstrap(owner, monkeypatch):
    monkeypatch.setattr(entry.subprocess, "run", lambda *_args, **_options: SimpleNamespace(returncode=0))
    monkeypatch.setattr(entry, "_git", lambda _root, *args: "blob" if args[0] == "cat-file" else pytest.fail(str(args)))
    assert entry._checker_source(owner.root, "d" * 40) == f"{'d' * 40}:{entry.CHECKER}"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (b'file with spaces\0quote".py\0', 'file with spaces\nquote".py'),
        (b"", ""),
        (b"multi\nline\0", None),
        (b"bad\xff\0", None),
    ],
)
def test_owner_entry_path_protocol_preserves_bytes_or_rejects(owner, monkeypatch, raw, expected):
    def read(command, **options):
        assert command[:8] == ["git", "-C", str(owner.root), "diff", "--cached", "--name-only", "-z", "base"]
        assert options["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        return raw

    monkeypatch.setattr(entry.subprocess, "check_output", read)
    if expected is None:
        with pytest.raises(ValueError):
            entry._checker_paths(owner.root, "base", "scripts/")
    else:
        assert entry._checker_paths(owner.root, "base", "scripts/") == expected


@pytest.mark.parametrize("function", ["validate_commit", "main"])
def test_committed_check_public_contract_policy(function):
    assert entry.__file__ is not None
    findings = _scan_file(Path(entry.__file__))
    assert not [finding for finding in findings if f"'{function}'" in finding.message]


@pytest.mark.parametrize("revision", ["HEAD", "", "a" * 39, "A" * 40, True, None])
def test_committed_check_rejects_noncanonical_identity(tmp_path, revision):
    with pytest.raises(ValueError, match="full commit"):
        entry.validate_commit(tmp_path, revision, "b" * 40)


@pytest.mark.parametrize("argument,status", [("install", 2), ("transaction", 2), ("--help", 0)])
def test_committed_check_cli_has_no_private_hook_route(monkeypatch, argument, status):
    monkeypatch.setattr(entry.sys, "argv", ["checker", argument])
    with pytest.raises(SystemExit) as error:
        entry.main()
    assert error.value.code == status


@pytest.mark.parametrize("previous", [None, "caller-index"])
@pytest.mark.parametrize("outcome", ["success", "empty", "checker-failure", "changed-tree", "read-failure"])
def test_committed_check_restores_index_and_cleans_private_files(tmp_path, monkeypatch, previous, outcome):
    head, base, tree = "a" * 40, "b" * 40, "c" * 40
    calls = []

    def git(_root, *args):
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify"):
            return args[2].split("^")[0]
        if args == ("rev-parse", "--is-shallow-repository"):
            return "false"
        if args[0] == "merge-base":
            return base
        if args[0] == "read-tree":
            if outcome == "read-failure":
                raise subprocess.CalledProcessError(1, ["git", "read-tree"])
            return ""
        if args[0] == "write-tree":
            return "d" * 40 if outcome == "changed-tree" else tree
        return tree

    def check(command, **options):
        assert options["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        assert Path(command[2]).is_file()
        assert command[3:] == ["capsule", "candidate", base]
        if outcome == "checker-failure":
            raise subprocess.CalledProcessError(7, command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(entry, "_git", git)
    monkeypatch.setattr(
        entry,
        "_checker_paths",
        lambda _root, _base, *paths: "" if outcome == "empty" else "capsule" if paths else "candidate",
    )
    monkeypatch.setattr(entry, "_checker_source", lambda _root, _base: "approved:checker")
    monkeypatch.setattr(entry.subprocess, "check_output", lambda *_args, **_options: b"approved checker bytes")
    monkeypatch.setattr(entry.subprocess, "run", check)
    monkeypatch.setattr(entry.tempfile, "tempdir", str(tmp_path))
    if previous is None:
        monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    else:
        monkeypatch.setenv("GIT_INDEX_FILE", previous)
    if outcome in {"checker-failure", "read-failure", "changed-tree"}:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            entry.validate_commit(tmp_path, head, base)
    else:
        assert entry.validate_commit(tmp_path, head, base) == (outcome == "success")
    assert entry.os.environ.get("GIT_INDEX_FILE") == previous
    assert not list(tmp_path.iterdir())
    assert ("read-tree", tree) in calls


@pytest.mark.parametrize("outcome", [True, False, "error"])
def test_committed_check_cli_preserves_validation_status(monkeypatch, capsys, outcome):
    def validate(*_args):
        if outcome == "error":
            raise ValueError("fixture rejection")
        return outcome

    monkeypatch.setattr(entry, "validate_commit", validate)
    monkeypatch.setattr(entry.sys, "argv", ["checker", "--head", "a" * 40, "--base", "b" * 40])
    assert entry.main() == (1 if outcome == "error" else 0)
    text = capsys.readouterr().err
    assert "rejected" in text if outcome == "error" else "a" * 40 in text
