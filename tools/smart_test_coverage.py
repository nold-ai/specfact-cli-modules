#!/usr/bin/env python3
"""Lightweight smart-test entrypoint for specfact-cli-modules."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _ensure_core_dependency(repo_root: Path) -> int:
    sys.path.insert(0, str(repo_root / "src"))
    from specfact_cli_modules.dev_bootstrap import ensure_core_dependency

    return ensure_core_dependency(repo_root)


def _run_pytest(extra_args: list[str]) -> int:
    cmd = [sys.executable, "-m", "pytest", "tests", *extra_args]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    bootstrap_result = _ensure_core_dependency(ROOT)
    if bootstrap_result != 0:
        return bootstrap_result
    parser = argparse.ArgumentParser(description="Run smart tests in modules repo")
    parser.add_argument("command", choices=["run", "check", "status", "force"])
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()

    if ns.command in {"run", "force"}:
        return _run_pytest(ns.args)

    if ns.command == "check":
        print("smart-test check: configured (modules repo scoped)")
        return 0

    # status
    print("smart-test status: ready (uses pytest tests/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
