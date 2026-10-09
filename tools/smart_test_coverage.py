#!/usr/bin/env python3
"""Lightweight smart-test entrypoint for specfact-cli-modules."""

from __future__ import annotations

import argparse
import subprocess
import sys

from dev_bootstrap_support import ROOT, ensure_core_dependency


def _run_pytest(extra_args: list[str]) -> int:
    # Separate explicit proofs from parent discovery so pytest collects them once.
    host = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/host/proof_capsule_deferred_review_ci.py",
            "tests/native/proof_native_canonical_path.py",
        ],
        cwd=ROOT,
        check=False,
    )
    if host.returncode:
        return host.returncode
    # Baseline proof versions stay immutable for index review; run their current contexts.
    baseline_proofs = (
        "tests/unit/test_capsule_deferred_review_ci.py",
        "tests/unit/test_macos_managed_uv_child.py",
        "tests/unit/test_macos_native_broker_wait.py",
        "tests/unit/test_macos_python_candidate.py",
    )
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        *("--ignore=" + proof for proof in baseline_proofs),
        *extra_args,
    ]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    bootstrap_result = ensure_core_dependency(ROOT)
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
