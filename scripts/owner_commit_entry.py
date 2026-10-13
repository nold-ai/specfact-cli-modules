"""Validate final PR commit scheduling in existing CI; install no local hooks."""

from __future__ import annotations

import argparse
import os
import re
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
    "scripts/check_macos_boundary_ci_receipts.py",
    "scripts/macos_managed_boundary/control.py",
    "tests/unit/test_macos_boundary_ci_receipts.py",
    "tests/unit/test_macos_managed_control.py",
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments],
        text=True,
        env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
    ).strip()


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


@ensure(lambda result: isinstance(result, bool))
def validate_commit(root: Path, head: str, base: str) -> bool:
    """Validate one immutable PR tree; return whether capsule scheduling applies.

    :raises OSError: Git, the checker or private temporary storage is unavailable.
    :raises ValueError: commit identity, history, authority, paths or tree is invalid.
    :raises subprocess.CalledProcessError: Git or the approved checker rejects validation.
    """
    for revision in (head, base):
        if not isinstance(revision, str) or re.fullmatch("[0-9a-f]{40}", revision) is None:
            raise ValueError("PR head and base must be full commit identities")
        if _git(root, "rev-parse", "--verify", revision + "^{commit}") != revision:
            raise ValueError("PR commit identity changed")
    if _git(root, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("Committed scheduling requires complete history")
    merge_base = _git(root, "merge-base", head, base)
    tree = _git(root, "rev-parse", head + "^{tree}")
    previous = os.environ.get("GIT_INDEX_FILE")
    with tempfile.TemporaryDirectory(prefix="specfact-committed-scheduling-") as temporary:
        try:
            os.environ["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
            _git(root, "read-tree", tree)
            capsule = _checker_paths(root, merge_base, *CAPSULE_PATHS)
            if not capsule:
                return False
            complete = _checker_paths(root, merge_base)
            source = _checker_source(root, base)
            checker = Path(temporary) / "checker.py"
            checker.write_bytes(
                subprocess.check_output(
                    ["git", "-C", str(root), "show", source],
                    env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
                )
            )
            subprocess.run(
                [sys.executable, "-I", str(checker), capsule, complete, base],
                cwd=root,
                env=os.environ | {"GIT_NO_REPLACE_OBJECTS": "1"},
                check=True,
            )
            if _git(root, "write-tree") != tree:
                raise ValueError("Committed scheduling index changed")
            return True
        finally:
            if previous is None:
                os.environ.pop("GIT_INDEX_FILE", None)
            else:
                os.environ["GIT_INDEX_FILE"] = previous


@ensure(lambda result: result in {0, 1})
def main() -> int:
    """Return committed scheduling status, preserving argparse help/errors.

    :raises SystemExit: required arguments are missing or help is requested.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    try:
        checked = validate_commit(Path.cwd(), args.head, args.base)
        outcome = "validated" if checked else "no capsule delta; ordinary gates still required"
        sys.stderr.write(f"CI committed scheduling {outcome}: {args.head}\n")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.stderr.write(f"CI committed scheduling rejected: {error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
