#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_SHA256 = "29f6db0dff0d8f89ba4d47dd02d2753a23adc4c41222102879f9773be506d44f"


def read_policy(root: Path) -> tuple[str, tuple[str, ...]]:
    policy_bytes = (root / "openspec/native-review-policy.json").read_bytes()
    if hashlib.sha256(policy_bytes).hexdigest() != POLICY_SHA256:
        raise ValueError("migration policy changed: execution_backend, freeze_ref and legacy_paths require review")
    policy = json.loads(policy_bytes)
    if not isinstance(policy, dict) or policy.get("execution_backend") != "trusted-local-native":
        raise ValueError("execution_backend must remain trusted-local-native; the owner already decided this")
    baseline = policy.get("freeze_ref")
    if not isinstance(baseline, str) or not baseline:
        raise ValueError("freeze_ref must name the recorded migration baseline")
    patterns = policy.get("legacy_paths")
    if not isinstance(patterns, list) or not patterns or not all(isinstance(item, str) and item for item in patterns):
        raise ValueError("legacy_paths must classify the frozen capsule surfaces")
    return baseline, tuple(patterns)


def resolve_commit(root: Path, revision: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
            stderr=subprocess.PIPE,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"freeze_ref comparison unavailable: {revision}; fetch the recorded Git history") from exc


def changed_paths(root: Path, baseline: str, head: str | None) -> list[tuple[str, str]]:
    baseline = resolve_commit(root, baseline)
    head = resolve_commit(root, head) if head is not None else None
    command = ["git", "-C", str(root), "diff", "--name-status", "-z", "--no-renames", baseline]
    if head:
        command.append(head)
    try:
        records = subprocess.check_output([*command, "--"], stderr=subprocess.PIPE).decode().split("\0")
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"freeze_ref comparison unavailable: {baseline}; fetch the recorded Git history") from exc
    changes = list(zip(records[0:-1:2], records[1:-1:2], strict=True))
    if head is None:
        untracked = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"], stderr=subprocess.PIPE
        ).decode()
        changes.extend(("A", name) for name in untracked.split("\0") if name)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject renewed capsule work during the native review migration.")
    parser.add_argument("--base-ref", help="Read-only historical comparison baseline")
    parser.add_argument("--head-ref", help="Read-only historical comparison head; default is the working tree")
    arguments = parser.parse_args()
    try:
        baseline, patterns = read_policy(ROOT)
        changes = changed_paths(ROOT, arguments.base_ref or baseline, arguments.head_ref)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Native review scope check failed: {exc}")
        return 1
    rejected = sorted(
        {path for status, path in changes if status != "D" and any(fnmatch.fnmatchcase(path, p) for p in patterns)}
    )
    if rejected:
        for path in rejected:
            print(f"{path}: capsule additions/repairs are frozen; retirement deletions remain allowed.")
        print(
            "Use native execution in packages/specfact-codebase/src/specfact_codebase/project_runtime.py. "
            "Follow changes 17 -> 18 -> 19 -> paired core adoption -> 20 in openspec/CHANGE_ORDER.md; "
            "do not reopen capsule implementation."
        )
        return 1
    print("Native review scope check passed; existing gate outcomes remain authoritative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
