"""Portable entry guard measurements supplement mandatory real Git/host proofs."""

from __future__ import annotations

import importlib
import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from specfact_code_review.tools.contract_runner import _scan_file


if TYPE_CHECKING:
    from scripts import owner_commit_entry as entry
else:
    entry = importlib.import_module("scripts.owner_commit_entry")


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


@pytest.fixture(name="transaction")
def transaction_fixture(owner, tmp_path, monkeypatch):
    binding = entry._binding(owner.root, owner.normal, owner.interpreter)
    config = tmp_path / "transaction-binding.json"
    config.write_text(json.dumps(binding), encoding="utf-8")
    old, proposed, tree = "a" * 40, "b" * 40, "c" * 40
    owner.values.update(
        {
            ("rev-parse", "HEAD"): old,
            ("cat-file", "-t", proposed): "commit",
            ("rev-parse", proposed + "^{tree}"): tree,
            ("read-tree", tree): "",
            ("write-tree",): tree,
        }
    )
    payload = f"{old} {proposed} refs/heads/{binding['branch']}\n"
    record = entry._record_path(config)
    record.write_text(
        json.dumps({"git_pid": str(entry.os.getppid()), "started": entry._parent_started(), "head": old, "tree": tree}),
        encoding="utf-8",
    )
    record.chmod(0o600)
    checked = []

    def check(actual):
        assert actual == binding
        path = Path(entry.os.environ["GIT_INDEX_FILE"])
        assert path.parent != owner.root and path.name == "index"
        checked.append(path)

    monkeypatch.setattr(entry, "validate_index", check)
    return SimpleNamespace(
        owner=owner,
        binding=binding,
        config=config,
        payload=payload,
        old=old,
        proposed=proposed,
        tree=tree,
        checked=checked,
    )


def test_owner_transaction_has_precise_public_contracts():
    findings = _scan_file(Path(entry.__file__))
    assert not [finding for finding in findings if "'validate_transaction'" in finding.message]


@pytest.mark.parametrize("previous", [None, "existing-caller-index"])
@pytest.mark.parametrize("reject", [False, True])
def test_owner_transaction_restores_private_index_and_environment(transaction, monkeypatch, previous, reject):
    if previous is None:
        monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    else:
        monkeypatch.setenv("GIT_INDEX_FILE", previous)
    if reject:

        def reject_index(_binding):
            transaction.checked.append(Path(entry.os.environ["GIT_INDEX_FILE"]))
            raise ValueError("genuine approved checker rejection")

        monkeypatch.setattr(entry, "validate_index", reject_index)
        with pytest.raises(ValueError, match="genuine approved checker rejection"):
            entry.validate_transaction(transaction.config, "prepared", transaction.payload)
    else:
        assert entry.validate_transaction(transaction.config, "prepared", transaction.payload) is None
    assert len(transaction.checked) == 1
    assert not transaction.checked[0].parent.exists()
    assert entry.os.environ.get("GIT_INDEX_FILE") == previous


def test_owner_transaction_rejects_changed_private_tree(transaction):
    transaction.owner.values[("write-tree",)] = "d" * 40
    with pytest.raises(ValueError, match="Proposed tree index changed"):
        entry.validate_transaction(transaction.config, "prepared", transaction.payload)
    assert len(transaction.checked) == 1 and not transaction.checked[0].parent.exists()


@pytest.mark.parametrize(
    "invalid",
    [
        "empty",
        "oversized",
        "incomplete",
        "fields",
        "oid",
        "duplicate",
        "other-reference",
        "old",
        "conflicting-head",
        "not-commit",
        "metadata-update",
        "other-deletion",
    ],
)
def test_owner_transaction_rejects_noncanonical_or_unbound_reference_input(transaction, invalid):
    old, new = transaction.old, transaction.proposed
    cases = {
        "empty": "",
        "oversized": "x" * 4097 + "\n",
        "incomplete": transaction.payload.rstrip("\n"),
        "fields": old + "\n",
        "oid": transaction.payload.replace(old, "not-a-git-object", 1),
        "duplicate": transaction.payload * 2,
        "other-reference": f"{old} {new} refs/heads/other\n",
        "old": transaction.payload.replace(old, "d" * 40, 1),
        "conflicting-head": transaction.payload + f"{old} {'d' * 40} HEAD\n",
        "not-commit": transaction.payload,
        "metadata-update": f"{old} {new} AUTO_MERGE\n",
        "other-deletion": f"{old} {'0' * 40} refs/heads/other\n",
    }
    if invalid == "not-commit":
        transaction.owner.values[("cat-file", "-t", new)] = "tree"
    with pytest.raises(ValueError):
        entry.validate_transaction(transaction.config, "prepared", cases[invalid])
    assert transaction.checked == []


def test_owner_transaction_validates_head_notification_actual_tree(transaction):
    transaction.owner.values[("rev-parse", "HEAD")] = transaction.proposed
    payload = f"{transaction.old} {transaction.proposed} HEAD\n"
    assert entry.validate_transaction(transaction.config, "prepared", payload) is None
    assert len(transaction.checked) == 1


def test_owner_transaction_git_cleanup_deletion_has_no_commit_authority(transaction):
    payload = f"{'0' * 40} {'0' * 40} AUTO_MERGE\n"
    assert entry.validate_transaction(transaction.config, "prepared", payload) is None
    assert transaction.checked == []


@pytest.mark.parametrize("phase", ["preparing", "committed", "aborted"])
def test_owner_transaction_notifications_are_not_commit_authority(transaction, phase):
    assert entry.validate_transaction(transaction.config, phase, "") is None
    assert transaction.checked == []


def test_owner_transaction_unknown_phase_rejects(transaction):
    with pytest.raises(ValueError, match="Unknown reference transaction phase"):
        entry.validate_transaction(transaction.config, "unknown", transaction.payload)
    assert transaction.checked == []


@pytest.mark.parametrize("successful", [False, True])
def test_owner_commit_lifecycle_checks_and_records_same_complete_tree(transaction, monkeypatch, successful):
    monkeypatch.setenv("GIT_INDEX_FILE", "original-caller-index")
    entry._record_path(transaction.config).unlink()
    checked = entry._starting_index(transaction.binding)
    assert checked == transaction.tree
    assert entry._finish_index(transaction.binding, transaction.config, successful, checked) is None
    assert len(transaction.checked) == 2
    assert all(not path.parent.exists() for path in transaction.checked)
    assert entry.os.environ["GIT_INDEX_FILE"] == "original-caller-index"
    if successful:
        assert entry._recorded_tree(transaction.config, transaction.old) == transaction.tree
    else:
        assert not entry._record_path(transaction.config).exists()


def test_owner_commit_lifecycle_rejects_normal_hook_index_change(transaction, monkeypatch):
    monkeypatch.setenv("GIT_INDEX_FILE", "original-caller-index")
    entry._record_path(transaction.config).unlink()
    checked = entry._starting_index(transaction.binding)
    transaction.owner.values[("write-tree",)] = "d" * 40
    with pytest.raises(ValueError, match="Normal hooks changed the complete checked index"):
        entry._finish_index(transaction.binding, transaction.config, True, checked)
    assert len(transaction.checked) == 1
    assert not entry._record_path(transaction.config).exists()


@pytest.mark.parametrize(
    "invalid", ["mode", "symlink", "shape", "keys", "pid", "birth", "head", "tree-type", "tree-oid"]
)
def test_owner_transaction_rejects_unbound_private_record(transaction, invalid):
    path = entry._record_path(transaction.config)
    value = json.loads(path.read_text(encoding="utf-8"))
    mutations = {
        "keys": {"unexpected": 1},
        "pid": {"git_pid": "other"},
        "birth": {"started": "old process"},
        "head": {"head": "d" * 40},
        "tree-type": {"tree": True},
        "tree-oid": {"tree": "invalid"},
    }
    if invalid == "mode":
        path.chmod(0o644)
    elif invalid == "symlink":
        target = path.with_suffix(".target")
        path.rename(target)
        path.symlink_to(target)
    else:
        content = [] if invalid == "shape" else value | mutations[invalid]
        path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError):
        entry.validate_transaction(transaction.config, "prepared", transaction.payload)
    assert transaction.checked == []


def test_owner_transaction_requires_private_record_and_exact_tree(transaction):
    path = entry._record_path(transaction.config)
    path.unlink()
    with pytest.raises(OSError):
        entry.validate_transaction(transaction.config, "prepared", transaction.payload)
    path.write_text(
        json.dumps(
            {
                "git_pid": str(entry.os.getppid()),
                "started": entry._parent_started(),
                "head": transaction.old,
                "tree": "d" * 40,
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)
    with pytest.raises(ValueError, match="differs from the tree checked after normal hooks"):
        entry.validate_transaction(transaction.config, "prepared", transaction.payload)
    assert transaction.checked == []


def test_owner_transaction_aborted_notification_removes_only_own_record(transaction):
    record = entry._record_path(transaction.config)
    assert record.exists()
    assert entry.validate_transaction(transaction.config, "aborted", "") is None
    assert not record.exists() and transaction.config.exists()
    assert transaction.checked == []


@pytest.mark.parametrize("invalid", [False, True])
def test_owner_transaction_cli_retains_zero_or_rejection_status(transaction, monkeypatch, invalid):
    monkeypatch.setattr(entry.sys, "argv", ["owner-entry", "transaction", str(transaction.config), "prepared"])
    monkeypatch.setattr(entry.sys, "stdin", io.StringIO("invalid\n" if invalid else transaction.payload))
    assert entry.main() == (1 if invalid else 0)


def test_owner_checked_tree_write_failure_cleans_real_private_allocation(transaction, monkeypatch):
    entry._record_path(transaction.config).unlink()

    def reject_write(*_arguments):
        raise OSError("private record write failed")

    monkeypatch.setattr(entry.json, "dump", reject_write)
    before = set(transaction.config.parent.iterdir())
    with pytest.raises(OSError, match="private record write failed"):
        entry._finish_index(transaction.binding, transaction.config, True, transaction.tree)
    assert set(transaction.config.parent.iterdir()) == before
    assert not entry._record_path(transaction.config).exists()
