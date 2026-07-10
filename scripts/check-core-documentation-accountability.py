#!/usr/bin/env python3
# ruff: noqa: N999
"""Run the authoritative core documentation-accountability checker for modules."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from beartype import beartype
from icontract import ensure, require


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_CHECKER_RELATIVE_PATH = Path("scripts") / "check-documentation-accountability.py"
DEFAULT_CHECKER_TIMEOUT_SECONDS = 120


def _paired_worktree_checkout() -> Path | None:
    marker = "specfact-cli-modules-worktrees"
    if marker not in REPO_ROOT.parts:
        return None
    marker_index = REPO_ROOT.parts.index(marker)
    base = Path(*REPO_ROOT.parts[:marker_index])
    suffix = Path(*REPO_ROOT.parts[marker_index + 1 :])
    return base / "specfact-cli-worktrees" / suffix


def _core_candidates(explicit_path: str | None) -> list[Path]:
    candidates: list[Path] = []
    configured = explicit_path or os.environ.get("SPECFACT_CLI_REPO", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())

    paired_checkout = _paired_worktree_checkout()
    if paired_checkout is not None:
        candidates.append(paired_checkout)
    candidates.append(REPO_ROOT.parent / "specfact-cli")

    marker = "specfact-cli-modules-worktrees"
    if marker in REPO_ROOT.parts:
        marker_index = REPO_ROOT.parts.index(marker)
        candidates.append(Path(*REPO_ROOT.parts[:marker_index]) / "specfact-cli")
    return candidates


@beartype
@ensure(lambda result: result.is_dir())
def resolve_core_checkout(explicit_path: str | None = None) -> Path:
    """Resolve a core checkout containing its authoritative checker."""
    checked_paths: list[Path] = []
    for candidate in _core_candidates(explicit_path):
        resolved = candidate.resolve()
        if resolved in checked_paths:
            continue
        checked_paths.append(resolved)
        if (resolved / CORE_CHECKER_RELATIVE_PATH).is_file():
            return resolved
    checked = ", ".join(str(path) for path in checked_paths)
    raise ValueError(
        "Cannot resolve specfact-cli documentation-accountability checker. "
        "Set SPECFACT_CLI_REPO to a core checkout containing "
        f"{CORE_CHECKER_RELATIVE_PATH}. Checked: {checked}"
    )


@beartype
@require(lambda core_root, modules_root: core_root.is_dir() and modules_root.is_dir())
@require(lambda timeout_seconds: timeout_seconds > 0, "timeout must be positive")
@ensure(lambda result: isinstance(result, int))
def run_accountability(
    core_root: Path,
    modules_root: Path,
    *,
    timeout_seconds: int = DEFAULT_CHECKER_TIMEOUT_SECONDS,
) -> int:
    """Delegate validation to the core-owned checker without copying its rules."""
    command = [
        sys.executable,
        str(core_root / CORE_CHECKER_RELATIVE_PATH),
        "--modules-repo",
        str(modules_root.resolve()),
    ]
    try:
        return subprocess.run(command, check=False, timeout=timeout_seconds).returncode
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"core-documentation-accountability: checker timed out after {timeout_seconds} seconds\n")
        return 1


def _checker_timeout_seconds() -> int:
    configured = os.environ.get("SPECFACT_CORE_ACCOUNTABILITY_TIMEOUT_SECONDS", "").strip()
    if not configured:
        return DEFAULT_CHECKER_TIMEOUT_SECONDS
    try:
        timeout_seconds = int(configured)
    except ValueError as exc:
        raise ValueError("SPECFACT_CORE_ACCOUNTABILITY_TIMEOUT_SECONDS must be a positive integer") from exc
    if timeout_seconds <= 0:
        raise ValueError("SPECFACT_CORE_ACCOUNTABILITY_TIMEOUT_SECONDS must be a positive integer")
    return timeout_seconds


@beartype
@ensure(lambda result: isinstance(result, int))
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-repo", help="Path to the paired specfact-cli checkout")
    args = parser.parse_args(argv)
    try:
        core_root = resolve_core_checkout(args.core_repo)
        timeout_seconds = _checker_timeout_seconds()
    except ValueError as exc:
        sys.stderr.write(f"core-documentation-accountability: {exc}\n")
        return 1
    return run_accountability(core_root, REPO_ROOT, timeout_seconds=timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
