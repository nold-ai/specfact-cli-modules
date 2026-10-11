"""Install the owner-approved, invocation-scoped commit entry outside a worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
        **_interpreter_binding(root, interpreter),
        "normal_hook": str(normal_hook),
        "normal_digest": _digest(normal_hook),
        "normal_config_digest": _digest(root / ".pre-commit-config.yaml")
        if (root / ".pre-commit-config.yaml").is_file()
        else "",
    }


def install(root: Path, destination: Path, normal_hook: Path, interpreter: Path) -> None:
    """Freeze reviewed entry bytes and bindings; never change shared hooks/config."""
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


def validate_index(binding: dict[str, str]) -> None:
    root = _validate_binding(binding)
    integrated_dev = _git(root, "rev-parse", "--verify", "refs/remotes/origin/dev^{commit}")
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


def enforce(config: Path, hook_arguments: list[str]) -> int:
    binding = json.loads(config.read_text(encoding="utf-8"))
    validate_index(binding)
    print("Owner entry: indexed scheduling validated before normal hooks", file=sys.stderr)
    normal = subprocess.run([binding["normal_hook"], *hook_arguments], check=False)
    validate_index(binding)
    print("Owner entry: indexed scheduling validated after normal hooks; hosted review still required", file=sys.stderr)
    return normal.returncode


def main() -> int:
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
    arguments = parser.parse_args()
    try:
        if arguments.command == "install":
            install(arguments.worktree, arguments.destination, arguments.normal_hook, arguments.interpreter)
            return 0
        return enforce(arguments.config, arguments.hook_arguments)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Owner commit entry rejected: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
