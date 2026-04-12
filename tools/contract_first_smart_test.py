#!/usr/bin/env python3
"""Contract-test wrapper scoped for specfact-cli-modules."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from dev_bootstrap_support import ROOT, ensure_core_dependency


# Staged paths that should trigger `contract-test` in pre-commit when present.
_RELEVANT_PREFIXES = (
    "tests/",
    "packages/",
    "src/",
    "tools/",
    "openspec/",
    "registry/",
)
_RELEVANT_TOP_FILES = frozenset({"pyproject.toml"})
_RELEVANT_SCRIPT_PY = re.compile(r"^scripts/.+\.pyi?$")


def _git_staged_names(repo_root: Path) -> list[str] | None:
    """Return staged path names, or None if git is unavailable or the command failed."""
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _names_require_contract_test(names: list[str]) -> bool:
    """Return True when staged files touch surfaces covered by the contract-test pytest run."""
    for name in names:
        if name in _RELEVANT_TOP_FILES:
            return True
        if any(name.startswith(prefix) for prefix in _RELEVANT_PREFIXES):
            return True
        if _RELEVANT_SCRIPT_PY.match(name):
            return True
    return False


def _contract_test_status() -> int:
    """Exit 0 = pre-commit may skip pytest. Exit 1 = run ``hatch run contract-test``.

    Shell guard in ``pre-commit-quality-checks.sh``:
    ``if hatch run contract-test-status; then`` skip; ``else`` run ``hatch run contract-test``.
    """
    names = _git_staged_names(ROOT)
    if names is None:
        print(
            "contract-test status: cannot read git index — run contract-test",
            file=sys.stderr,
        )
        return 1
    if not names:
        print("contract-test status: nothing staged — skip contract-test", file=sys.stderr)
        return 0
    if _names_require_contract_test(names):
        print("contract-test status: staged changes touch contract surface — run contract-test", file=sys.stderr)
        return 1
    print("contract-test status: staged paths omit contract surface — skip contract-test", file=sys.stderr)
    return 0


def _run_pytest(extra_args: list[str], marker: str | None = None) -> int:
    cmd = [sys.executable, "-m", "pytest", "tests"]
    if marker:
        cmd.extend(["-m", marker])
    cmd.extend(extra_args)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    bootstrap_result = ensure_core_dependency(ROOT)
    if bootstrap_result != 0:
        return bootstrap_result
    parser = argparse.ArgumentParser(description="Run contract-first checks in modules repo")
    parser.add_argument("command", choices=["run", "contracts", "exploration", "scenarios", "status"])
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()

    if ns.command == "status":
        return _contract_test_status()
    if ns.command == "run":
        return _run_pytest(ns.args)
    if ns.command == "contracts":
        return _run_pytest(ns.args, marker="contract")
    if ns.command == "exploration":
        print("contract exploration: placeholder (run crosshair in package-specific tasks)")
        return 0
    if ns.command == "scenarios":
        return _run_pytest(ns.args, marker="integration or e2e")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
