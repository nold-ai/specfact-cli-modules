"""Portable entry guard measurements supplement mandatory real Git/host proofs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import owner_commit_entry as entry
from specfact_code_review.tools.contract_runner import _scan_file


@pytest.fixture(name="owner")
def owner_fixture(tmp_path, monkeypatch):
    root = tmp_path / "caller"
    root.mkdir()
    (root / ".git").write_text("gitdir: fixture\n")
    (root / ".venv/bin").mkdir(parents=True)
    caller = root / ".venv/bin/python"
    caller.write_bytes(b"caller interpreter fixture")
    caller.chmod(0o700)
    interpreter = tmp_path / "owner python"
    interpreter.write_bytes(b"external interpreter fixture")
    interpreter.chmod(0o700)
    normal = tmp_path / "normal hook"
    normal.write_text("fixture hook bytes\n")
    normal.chmod(0o700)
    config = root / ".pre-commit-config.yaml"
    config.write_text("repos: []\n")
    values = {
        ("symbolic-ref", "--short", "HEAD"): "bugfix/fixture",
        ("rev-parse", "--absolute-git-dir"): str(tmp_path / "gitdir"),
        ("rev-parse", "--verify", "refs/remotes/origin/dev^{commit}"): "d" * 40,
        ("rev-parse", "--show-toplevel"): str(root),
    }
    monkeypatch.setattr(entry, "_git", lambda _root, *args: values[args])
    return SimpleNamespace(root=root, normal=normal, interpreter=interpreter, caller=caller, values=values)


@pytest.mark.parametrize("function", ["install", "validate_index", "enforce", "main"])
def test_owner_entry_public_contract_policy_is_enforced(function):
    findings = _scan_file(Path(entry.__file__))
    assert not [finding for finding in findings if f"'{function}'" in finding.message]


def test_owner_entry_binding_freezes_actual_targets_bytes_and_context(owner):
    binding = entry._binding(owner.root, owner.normal, owner.interpreter)
    assert binding["integrated_dev"] == "d" * 40
    assert binding["interpreter_target"] == str(owner.interpreter)
    assert binding["interpreter_digest"] == entry._digest(owner.interpreter)
    assert binding["caller_interpreter_digest"] == entry._digest(owner.caller)
    assert binding["normal_digest"] == entry._digest(owner.normal)
    assert entry._validate_binding(binding) == owner.root
    owner.interpreter.write_bytes(b"changed interpreter")
    with pytest.raises(ValueError, match="binding changed"):
        entry._validate_binding(binding)


@pytest.mark.parametrize("mutation", ["protected", "primary", "normal", "caller", "inside", "context", "dev"])
def test_owner_entry_rejects_invalid_binding(owner, mutation):
    binding = entry._binding(owner.root, owner.normal, owner.interpreter)
    mutations = {
        "protected": lambda: owner.values.__setitem__(("symbolic-ref", "--short", "HEAD"), "dev"),
        "primary": lambda: (owner.root / ".git").unlink(),
        "normal": lambda: owner.normal.chmod(0o600),
        "caller": lambda: owner.caller.chmod(0o600),
        "inside": lambda: binding.__setitem__("interpreter", str(owner.caller)),
        "context": lambda: owner.values.__setitem__(("rev-parse", "--show-toplevel"), str(owner.root.parent)),
        "dev": lambda: owner.values.__setitem__(
            ("rev-parse", "--verify", "refs/remotes/origin/dev^{commit}"), "e" * 40
        ),
    }
    mutations[mutation]()
    with pytest.raises(ValueError):
        entry._validate_binding(binding)


def test_owner_entry_installation_retains_source_modes_and_quoted_shell(owner, tmp_path):
    destination = tmp_path / "entry with spaces"
    assert entry.install(owner.root, destination, owner.normal, owner.interpreter) is None
    assert destination.stat().st_mode & 0o777 == 0o700
    installed = destination / "owner_commit_entry.py"
    binding = json.loads((destination / "binding.json").read_text())
    assert installed.read_bytes() == Path(entry.__file__).read_bytes()
    assert binding == entry._binding(owner.root, owner.normal, owner.interpreter)
    assert installed.stat().st_mode & 0o777 == 0o600
    assert (destination / "binding.json").stat().st_mode & 0o777 == 0o600
    shell = (destination / "pre-commit").read_text()
    assert shell.startswith("#!/bin/sh\nexec '") and " -I " in shell and shell.endswith(' "$@"\n')
    assert (destination / "pre-commit").stat().st_mode & 0o777 == 0o700
    assert (owner.root / ".pre-commit-config.yaml").read_text() == "repos: []\n"
    assert owner.normal.read_text() == "fixture hook bytes\n"
    with pytest.raises(ValueError, match="outside"):
        entry.install(owner.root, owner.root / "entry", owner.normal, owner.interpreter)


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


@pytest.mark.parametrize("outcome", ["success", "checker-failure", "empty"])
def test_owner_entry_index_check_uses_private_authority_and_cleans_up(owner, monkeypatch, outcome):
    binding = entry._binding(owner.root, owner.normal, owner.interpreter)
    selected = []
    monkeypatch.setattr(entry, "_checker_source", lambda root, dev: selected.append((root, dev)) or "approved-source")
    owner.values[("merge-base", "HEAD", "d" * 40)] = "base"
    monkeypatch.setattr(
        entry,
        "_checker_paths",
        lambda _root, _base, *selectors: "" if outcome == "empty" and selectors else "scripts/owner_commit_entry.py",
    )
    paths = []

    def read(command, **options):
        assert command == ["git", "-C", str(owner.root), "show", "approved-source"]
        assert options["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        return b"approved fixture bytes: never executed\n"

    def process(command, **options):
        checker = Path(command[2])
        paths.append(checker)
        assert checker.read_bytes() == b"approved fixture bytes: never executed\n"
        assert command[0:2] == [str(owner.interpreter), "-I"] and command[-1] == "d" * 40
        assert options["cwd"] == owner.root and options["check"] is True
        assert options["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        if outcome == "checker-failure":
            raise subprocess.CalledProcessError(1, command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(entry.subprocess, "check_output", read)
    monkeypatch.setattr(entry.subprocess, "run", process)
    if outcome == "success":
        assert entry.validate_index(binding) is None
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            entry.validate_index(binding)
    assert selected == [(owner.root, "d" * 40)]
    assert all(not path.exists() and not path.parent.exists() for path in paths)


@pytest.mark.parametrize("status,invalid", [(0, ""), (7, ""), (-9, ""), (0, "before"), (0, "after")])
def test_owner_entry_hook_order_and_original_status(owner, tmp_path, monkeypatch, status, invalid):
    config = tmp_path / "binding.json"
    binding = entry._binding(owner.root, owner.normal, owner.interpreter)
    config.write_text(json.dumps(binding))
    events = []

    def validate(actual):
        assert actual == binding
        events.append("check")
        if invalid == ("before" if len(events) == 1 else "after"):
            raise ValueError("binding changed")

    def normal(command, **options):
        events.append("normal")
        assert command == [str(owner.normal), "original-argument"] and options == {"check": False}
        return SimpleNamespace(returncode=status)

    monkeypatch.setattr(entry, "validate_index", validate)
    monkeypatch.setattr(entry.subprocess, "run", normal)
    if invalid:
        with pytest.raises(ValueError, match="binding changed"):
            entry.enforce(config, ["original-argument"])
    else:
        assert entry.enforce(config, ["original-argument"]) == status
    assert events == (["check"] if invalid == "before" else ["check", "normal", "check"])


@pytest.mark.parametrize("command,status", [("install", 0), ("check", 7), ("reject", 1)])
def test_owner_entry_cli_retains_install_check_and_rejection_status(owner, tmp_path, monkeypatch, command, status):
    calls = []

    def install(*arguments):
        calls.append(arguments)

    def enforce(*arguments):
        calls.append(arguments)
        if command == "reject":
            raise ValueError("invalid binding")
        return status

    monkeypatch.setattr(entry, "install", install)
    monkeypatch.setattr(entry, "enforce", enforce)
    arguments = (
        [
            "owner-entry",
            "install",
            str(owner.root),
            str(tmp_path / "install"),
            str(owner.normal),
            "--interpreter",
            str(owner.interpreter),
        ]
        if command == "install"
        else ["owner-entry", "check", str(tmp_path / "binding.json"), "original-argument"]
    )
    monkeypatch.setattr(entry.sys, "argv", arguments)
    assert entry.main() == status
    assert len(calls) == 1


@pytest.mark.parametrize("argument,status", [("unknown-command", 2), ("--help", 0)])
def test_owner_entry_cli_declares_precise_real_parser_exit(monkeypatch, argument, status):
    from crosshair.condition_parser import parse_sphinx_raises

    monkeypatch.setattr(entry.sys, "argv", ["owner-entry", argument])
    with pytest.raises(SystemExit) as outcome:
        entry.main()
    assert outcome.value.code == status
    assert parse_sphinx_raises(entry.main) == {SystemExit}


@pytest.mark.parametrize("api", ["install", "validate_index", "enforce"])
def test_owner_entry_rejection_contracts_match_actual_errors(owner, tmp_path, api):
    from crosshair.condition_parser import parse_sphinx_raises

    if api == "install":
        with pytest.raises(ValueError, match="outside"):
            entry.install(owner.root, owner.root / "entry", owner.normal, owner.interpreter)
    elif api == "validate_index":
        with pytest.raises(KeyError, match="root"):
            entry.validate_index({})
    else:
        config = tmp_path / "malformed.json"
        config.write_text("not JSON")
        with pytest.raises(ValueError):
            entry.enforce(config, [])
    expected = {OSError, ValueError, subprocess.CalledProcessError}
    if api != "install":
        expected.add(KeyError)
    assert parse_sphinx_raises(getattr(entry, api)) == expected
