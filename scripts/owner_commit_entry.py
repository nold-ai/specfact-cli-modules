"""Install the owner-approved, invocation-scoped commit entry outside a worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from icontract import ensure


CHECKER = "scripts/check_capsule_deferral.py"
BOOTSTRAP_COMMIT = "c65a41e61a6b4e61e8dd2b69526a1cfc8650b3ad"
BOOTSTRAP_BLOB = "cc549b5bbd945b64d055afe111bcaeeb059d585a"
CAPSULE_PATHS = (
    "packages/specfact-code-review",
    ".github/workflows/capsule-customer-execution.yml",
    ".github/workflows/pr-orchestrator.yml",
    "scripts/pre-commit-quality-checks.sh",
    CHECKER,
    "scripts/owner_commit_entry.py",
    "scripts/pre_commit_code_review.py",
    "tests/native",
    "tests/unit/specfact_code_review",
    "tests/unit/test_native_broker_cleanup.py",
    "pyproject.toml",
    "tools/smart_test_coverage.py",
    ".github/workflows/code-review-macos-boundary.yml",
    "tests/unit/test_capsule_proof_contexts.py",
    "tests/host/proof_capsule_deferred_review_ci.py",
    "tests/host/proof_capsule_review_projection_shell.py",
    "tests/unit/test_pre_commit_quality_parity.py",
    "tests/unit/test_capsule_review_projection.py",
    "tests/unit/scripts/test_pre_commit_code_review.py",
    "tests/support/capsule_review_fixtures.py",
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments],
        text=True,
        env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
    ).strip()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _interpreter_binding(root: Path, interpreter: Path) -> dict[str, str]:
    caller = root / ".venv/bin/python"
    interpreter = interpreter.absolute()
    if interpreter.is_relative_to(root) or interpreter.resolve().is_relative_to(root):
        raise ValueError("Owner entry interpreter must be outside the candidate checkout")
    if not os.access(caller, os.X_OK) or not os.access(interpreter, os.X_OK):
        raise ValueError("Owner-installed interpreters are required")
    return {
        "interpreter": str(interpreter),
        "interpreter_target": str(interpreter.resolve(strict=True)),
        "interpreter_digest": _digest(interpreter),
        "caller_interpreter_target": str(caller.resolve(strict=True)),
        "caller_interpreter_digest": _digest(caller),
    }


def _binding(root: Path, normal_hook: Path, interpreter: Path) -> dict[str, str]:
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    if branch in {"dev", "main"} or not (root / ".git").is_file():
        raise ValueError("Owner entry requires a non-protected linked worktree")
    if not os.access(normal_hook, os.X_OK):
        raise ValueError("Owner-installed interpreter and existing normal hook are required")
    return {
        "root": str(root),
        "gitdir": _git(root, "rev-parse", "--absolute-git-dir"),
        "branch": branch,
        "integrated_dev": _git(root, "rev-parse", "--verify", "refs/remotes/origin/dev^{commit}"),
        **_interpreter_binding(root, interpreter),
        "normal_hook": str(normal_hook),
        "normal_digest": _digest(normal_hook),
        "normal_config_digest": _digest(root / ".pre-commit-config.yaml")
        if (root / ".pre-commit-config.yaml").is_file()
        else "",
    }


@ensure(lambda result: result is None)
def install(root: Path, destination: Path, normal_hook: Path, interpreter: Path) -> None:
    """Freeze reviewed entry bytes and bindings; never change shared hooks/config.

    :raises OSError: the private installation or an installed tool cannot be accessed.
    :raises ValueError: caller, interpreter or destination violates the approved scope.
    :raises subprocess.CalledProcessError: verified Git metadata cannot be read.
    """
    root, destination, normal_hook = root.resolve(), destination.resolve(), normal_hook.resolve()
    if destination.is_relative_to(root):
        raise ValueError("Owner entry must be installed outside the candidate checkout")
    binding = _binding(root, normal_hook, interpreter)
    destination.mkdir(mode=0o700)
    entry = destination / "owner_commit_entry.py"
    shutil.copyfile(Path(__file__).resolve(), entry)
    entry.chmod(0o600)
    config = destination / "binding.json"
    config.write_text(json.dumps(binding, sort_keys=True) + "\n", encoding="utf-8")
    config.chmod(0o600)
    hook = destination / "pre-commit"
    hook.write_text(
        "#!/bin/sh\nexec "
        + " ".join(shlex.quote(item) for item in (binding["interpreter"], "-I", str(entry), "check", str(config)))
        + ' "$@"\n',
        encoding="utf-8",
    )
    hook.chmod(0o700)
    transaction = destination / "reference-transaction"
    transaction.write_text(
        "#!/bin/sh\nexec "
        + " ".join(shlex.quote(item) for item in (binding["interpreter"], "-I", str(entry), "transaction", str(config)))
        + ' "$@"\n',
        encoding="utf-8",
    )
    transaction.chmod(0o700)
    print(f"Owner entry installed: {destination}; select with invocation-only core.hooksPath")


def _validate_binding(binding: dict[str, str]) -> Path:
    root = Path(binding["root"])
    actual_root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
    if actual_root != root or _binding(root, Path(binding["normal_hook"]), Path(binding["interpreter"])) != binding:
        raise ValueError("Owner commit entry caller/interpreter/hook binding changed")
    return root


def _checker_source(root: Path, integrated_dev: str) -> str:
    source = f"{integrated_dev}:{CHECKER}"
    exists = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", source],
        env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
        capture_output=True,
        check=False,
    )
    if exists.returncode == 0:
        if _git(root, "cat-file", "-t", source) != "blob":
            raise ValueError("Integrated checker is not a blob")
        return source
    if _git(root, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("Bootstrap requires complete history")
    if _git(root, "log", "-1", "--format=%H", integrated_dev, "--", CHECKER):
        raise ValueError("Integrated checker history forbids bootstrap")
    if _git(root, "cat-file", "-t", BOOTSTRAP_COMMIT) != "commit":
        raise ValueError("Approved bootstrap commit missing")
    source = f"{BOOTSTRAP_COMMIT}:{CHECKER}"
    if _git(root, "rev-parse", "--verify", source) != BOOTSTRAP_BLOB:
        raise ValueError("Approved bootstrap blob mismatch")
    ancestry = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", BOOTSTRAP_COMMIT, integrated_dev],
        env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
        check=False,
    )
    if ancestry.returncode != 1 or _git(root, "cat-file", "-t", source) != "blob":
        raise ValueError("Bootstrap expired or ancestry validation failed")
    return source


def _checker_paths(root: Path, base: str, *selectors: str) -> str:
    raw = subprocess.check_output(
        ["git", "-C", str(root), "diff", "--cached", "--name-only", "-z", base, "--", *selectors],
        env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
    )
    paths = raw.decode("utf-8").split("\0")[:-1]
    if any(path.splitlines() != [path] for path in paths):
        raise ValueError("Staged pathname cannot be represented by the approved checker line protocol")
    return "\n".join(paths)


@ensure(lambda result: result is None)
def validate_index(binding: dict[str, str]) -> None:
    """Validate the actual index using only the bound approved authority.

    :raises OSError: required private files or installed tooling are unavailable.
    :raises ValueError: binding, authority, path protocol or scheduling is invalid.
    :raises KeyError: a required frozen binding field is missing.
    :raises subprocess.CalledProcessError: Git or the approved checker rejects validation.
    """
    root = _validate_binding(binding)
    integrated_dev = binding["integrated_dev"]
    source = _checker_source(root, integrated_dev)
    base = _git(root, "merge-base", "HEAD", integrated_dev)
    candidate = _checker_paths(root, base)
    capsule = _checker_paths(root, base, *CAPSULE_PATHS)
    if not capsule:
        raise ValueError("Owner entry requires a scheduled capsule candidate delta")
    with tempfile.TemporaryDirectory(prefix="specfact-owner-checker-") as temporary:
        checker = Path(temporary) / "checker.py"
        checker.write_bytes(
            subprocess.check_output(
                ["git", "-C", str(root), "show", source], env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"}
            )
        )
        subprocess.run(
            [binding["interpreter"], "-I", str(checker), capsule, candidate, integrated_dev],
            cwd=root,
            env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
            check=True,
        )


def _validate_tree(binding: dict[str, str], tree: str) -> None:
    """Run the same authority on a private index loaded from one immutable tree."""
    root = Path(binding["root"])
    previous = os.environ.get("GIT_INDEX_FILE")
    with tempfile.TemporaryDirectory(prefix="specfact-owner-proposed-tree-") as temporary:
        try:
            os.environ["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
            _git(root, "read-tree", tree)
            validate_index(binding)
            if _git(root, "write-tree") != tree:
                raise ValueError("Proposed tree index changed during validation")
        finally:
            if previous is None:
                os.environ.pop("GIT_INDEX_FILE", None)
            else:
                os.environ["GIT_INDEX_FILE"] = previous


def _record_path(config: Path) -> Path:
    return config.parent / f"checked-tree.{os.getppid()}.json"


def _parent_started() -> str:
    """Prevent an old private record from authorizing a reused Git process ID."""
    started = subprocess.check_output(["ps", "-p", str(os.getppid()), "-o", "lstart="], text=True).strip()
    if not started:
        raise ValueError("Parent Git process identity is unavailable")
    return started


def _starting_index(binding: dict[str, str]) -> str | None:
    """Capture the actual complete index before normal hooks may run."""
    if "GIT_INDEX_FILE" not in os.environ:
        validate_index(binding)
        return None
    tree = _git(Path(binding["root"]), "write-tree")
    _validate_tree(binding, tree)
    return tree


def _finish_index(binding: dict[str, str], config: Path, successful: bool, expected: str | None) -> None:
    """Seal the complete post-normal-hook tree within this Git invocation."""
    if expected is None:
        # A standalone index check cannot create a Git commit acceptance record.
        validate_index(binding)
        return
    root = Path(binding["root"])
    if _git(root, "write-tree") != expected:
        raise ValueError("Normal hooks changed the complete checked index; review and retry")
    tree = expected
    _validate_tree(binding, tree)
    if not successful:
        _record_path(config).unlink(missing_ok=True)
        return
    record = {
        "git_pid": str(os.getppid()),
        "started": _parent_started(),
        "head": _git(root, "rev-parse", "HEAD"),
        "tree": tree,
    }
    with tempfile.NamedTemporaryFile(mode="w", dir=config.parent, encoding="utf-8", delete=False) as output:
        name = Path(output.name)
        try:
            json.dump(record, output)
            output.flush()
            os.replace(name, _record_path(config))
        finally:
            name.unlink(missing_ok=True)


def _recorded_tree(config: Path, old: str) -> str:
    record = _record_path(config)
    if record.is_symlink() or record.stat().st_mode & 0o777 != 0o600:
        raise ValueError("Invalid private checked-tree record")
    value = json.loads(record.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"git_pid", "started", "head", "tree"}:
        raise ValueError("Invalid private checked-tree fields")
    if value["git_pid"] != str(os.getppid()) or value["started"] != _parent_started() or value["head"] != old:
        raise ValueError("Private checked-tree invocation changed")
    if not isinstance(value["tree"], str) or re.fullmatch("[0-9a-f]{40}", value["tree"]) is None:
        raise ValueError("Invalid private checked-tree object")
    return value["tree"]


@ensure(lambda result: isinstance(result, int) and not isinstance(result, bool))
def enforce(config: Path, hook_arguments: list[str]) -> int:
    """Retain normal-hook status only after both approved index validations.

    :raises OSError: private config or bound installed tooling is unavailable.
    :raises ValueError: config, binding, authority or scheduling is invalid.
    :raises KeyError: a required frozen binding field is missing.
    :raises subprocess.CalledProcessError: Git or the approved checker rejects validation.
    """
    binding = json.loads(config.read_text(encoding="utf-8"))
    checked = _starting_index(binding)
    print("Owner entry: indexed scheduling validated before normal hooks", file=sys.stderr)
    normal = subprocess.run([binding["normal_hook"], *hook_arguments], check=False)
    _finish_index(binding, config, normal.returncode == 0, checked)
    print("Owner entry: indexed scheduling validated after normal hooks; hosted review still required", file=sys.stderr)
    return normal.returncode


def _transaction_records(payload: str) -> dict[str, tuple[str, str]]:
    """Parse only complete bounded canonical Git reference records."""
    if not payload or len(payload) > 4096 or not payload.endswith("\n"):
        raise ValueError("Invalid prepared reference transaction payload")
    references = {}
    for line in payload.splitlines():
        fields = line.split(" ")
        if len(fields) != 3 or any(re.fullmatch("[0-9a-f]{40}", value) is None for value in fields[:2]):
            raise ValueError("Invalid prepared reference transaction record")
        old, new, reference = fields
        if reference in references:
            raise ValueError("Duplicate prepared reference transaction record")
        references[reference] = (old, new)
    return references


def _transaction_commit(root: Path, binding: dict[str, str], payload: str) -> str | None:
    """Bind the actual branch update and its subsequent HEAD notification."""
    references = _transaction_records(payload)
    if references.keys() == {"AUTO_MERGE"} and references["AUTO_MERGE"][1] == "0" * 40:
        return None
    branch = "refs/heads/" + binding["branch"]
    if not references or not references.keys() <= {branch, "HEAD"}:
        raise ValueError(f"Prepared reference transaction is outside the bound branch: {tuple(references)}")
    old, proposed = references[branch] if branch in references else references["HEAD"]
    expected = old if branch in references else proposed
    if expected != _git(root, "rev-parse", "HEAD") or any(row != (old, proposed) for row in references.values()):
        raise ValueError("Prepared reference transaction does not bind current HEAD")
    if _git(root, "cat-file", "-t", proposed) != "commit":
        raise ValueError("Prepared reference is not a commit")
    return proposed


@ensure(lambda result: result is None)
def validate_transaction(config: Path, phase: str, payload: str) -> None:
    """Check the immutable proposed tree before Git advances the bound branch.

    :raises OSError: required private files or installed tooling are unavailable.
    :raises ValueError: transaction, binding or scheduling is invalid.
    :raises KeyError: a required frozen binding field is missing.
    :raises subprocess.CalledProcessError: Git or the approved checker rejects validation.
    """
    if phase == "aborted":
        _record_path(config).unlink(missing_ok=True)
        return
    if phase in {"preparing", "committed"}:
        return
    if phase != "prepared":
        raise ValueError("Unknown reference transaction phase")
    binding = json.loads(config.read_text(encoding="utf-8"))
    root = _validate_binding(binding)
    proposed = _transaction_commit(root, binding, payload)
    if proposed is None:
        _record_path(config).unlink(missing_ok=True)
        return
    tree = _git(root, "rev-parse", proposed + "^{tree}")
    references = _transaction_records(payload)
    old = next(iter(references.values()))[0]
    if tree != _recorded_tree(config, old):
        raise ValueError("Actual proposed tree differs from the tree checked after normal hooks")
    _validate_tree(binding, tree)
    sys.stderr.write("Owner entry: immutable proposed commit tree validated before reference advancement\n")


@ensure(lambda result: isinstance(result, int) and not isinstance(result, bool))
def main() -> int:
    """Return the entry status or preserve argparse's own exit protocol.

    :raises SystemExit: invalid CLI arguments or an explicit help request.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    installer = commands.add_parser("install")
    installer.add_argument("worktree", type=Path)
    installer.add_argument("destination", type=Path)
    installer.add_argument("normal_hook", type=Path)
    installer.add_argument("--interpreter", type=Path, default=Path(sys.executable))
    checker = commands.add_parser("check")
    checker.add_argument("config", type=Path)
    checker.add_argument("hook_arguments", nargs="*")
    transaction = commands.add_parser("transaction")
    transaction.add_argument("config", type=Path)
    transaction.add_argument("phase")
    arguments = parser.parse_args()
    try:
        if arguments.command == "install":
            install(arguments.worktree, arguments.destination, arguments.normal_hook, arguments.interpreter)
            return 0
        if arguments.command == "transaction":
            validate_transaction(arguments.config, arguments.phase, sys.stdin.read(4097))
            return 0
        return enforce(arguments.config, arguments.hook_arguments)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Owner commit entry rejected: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
