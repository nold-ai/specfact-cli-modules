#!/usr/bin/env python3
"""Contract-test wrapper scoped for specfact-cli-modules."""

from __future__ import annotations

import argparse
import subprocess
import sys

from dev_bootstrap_support import ROOT, ensure_core_dependency


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

    if ns.command == "run":
        return _run_pytest(ns.args)
    if ns.command == "contracts":
        return _run_pytest(ns.args, marker="contract")
    if ns.command == "exploration":
        print("contract exploration: placeholder (run crosshair in package-specific tasks)")
        return 0
    if ns.command == "scenarios":
        return _run_pytest(ns.args, marker="integration or e2e")

    print("contract-test status: ready (pytest-backed, modules repo scoped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
