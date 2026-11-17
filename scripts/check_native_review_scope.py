#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_SHA256 = "1d9696307907e1af6985ae5e41a4a453a1e5ce9bcd6662b5855d795893ba8cef"


def read_policy(root: Path) -> tuple[str, tuple[str, ...], dict[str, list[str]]]:
    policy_bytes = (root / "openspec/native-review-policy.json").read_bytes()
    if hashlib.sha256(policy_bytes).hexdigest() != POLICY_SHA256:
        raise ValueError("migration policy changed: execution_backend, freeze_ref and legacy_paths require review")
    policy = json.loads(policy_bytes)
    if not isinstance(policy, dict) or policy.get("execution_backend") != "trusted-local-native":
        raise ValueError("execution_backend must remain trusted-local-native; the owner already decided this")
    baseline = policy.get("freeze_ref")
    if not isinstance(baseline, str) or not re.fullmatch(r"[0-9a-f]{40,64}", baseline):
        raise ValueError("freeze_ref must name the recorded migration baseline")
    patterns = policy_patterns(policy)
    manifest = policy.get("baseline_files")
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("baseline_files must retain the reviewed path, mode and blob identities")
    return baseline, patterns, manifest


def policy_patterns(policy: dict) -> tuple[str, ...]:
    patterns = policy.get("legacy_paths")
    if not isinstance(patterns, list) or not patterns or not all(isinstance(item, str) and item for item in patterns):
        raise ValueError("legacy_paths must classify the frozen capsule surfaces")
    return tuple(patterns)


def working_entry(root: Path, name: str, *, filemode: bool, index_mode: str | None) -> list[str] | None:
    path = root / name
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(mode):
        kind, data = "120000", os.fsencode(os.readlink(path))
        filters = "--no-filters"
    elif stat.S_ISREG(mode):
        kind = "100755" if filemode and mode & stat.S_IXUSR else "100644"
        if not filemode and index_mode in {"100644", "100755"}:
            kind = index_mode
        data = path.read_bytes()
        filters = f"--path={name}"
    else:
        return ["unsupported-type", ""]
    blob = (
        subprocess.run(
            ["git", "-C", str(root), "hash-object", filters, "--stdin"], input=data, capture_output=True, check=True
        )
        .stdout.decode()
        .strip()
    )
    return [kind, blob]


def manifest_changes(root: Path, manifest: dict[str, list[str]], patterns: tuple[str, ...]) -> list[tuple[str, str]]:
    listed = (
        subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
        )
        .decode()
        .split("\0")
    )
    mode = subprocess.check_output(["git", "-C", str(root), "config", "--get", "core.filemode"], text=True).strip()
    modes = index_modes(root)
    changes = []
    for name in sorted(set(listed) | set(manifest)):
        if not name or not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
            continue
        observed = working_entry(root, name, filemode=mode != "false", index_mode=modes.get(name))
        expected = manifest.get(name)
        if observed is None:
            continue
        if observed != expected:
            changes.append(("M" if expected else "A", name))
    return changes


def index_modes(root: Path) -> dict[str, str]:
    records = subprocess.check_output(["git", "-C", str(root), "ls-files", "--stage", "-z"]).decode().split("\0")
    return {name: metadata.split()[0] for record in records if record for metadata, name in [record.split("\t", 1)]}


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


def rejected_paths(changes: list[tuple[str, str]], patterns: tuple[str, ...]) -> list[str]:
    return sorted(
        {path for status, path in changes if status != "D" and any(fnmatch.fnmatchcase(path, p) for p in patterns)}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject renewed capsule work during the native review migration.")
    parser.add_argument("--base-ref", help="Read-only historical comparison baseline")
    parser.add_argument("--head-ref", help="Read-only historical comparison head; default is the working tree")
    arguments = parser.parse_args()
    try:
        baseline, patterns, manifest = read_policy(ROOT)
        changes = (
            changed_paths(ROOT, arguments.base_ref or baseline, arguments.head_ref)
            if arguments.base_ref or arguments.head_ref
            else manifest_changes(ROOT, manifest, patterns)
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Native review scope check failed: {exc}")
        return 1
    rejected = rejected_paths(changes, patterns)
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
