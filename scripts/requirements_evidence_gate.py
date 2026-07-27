"""Compatibility adapter for the public Requirements evidence command."""

from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path


write_requirements_evidence = import_module("specfact_requirements.requirements.evidence").write_requirements_evidence


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--base-ref", help="Git ref used as the branch-diff base.")
    selection.add_argument("--staged", action="store_true", help="Evaluate the current Git index snapshot.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root to inspect.")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON evidence artifact.")
    parser.add_argument("--summary", type=Path, help="Optional destination for a GitHub Actions Markdown summary.")
    return parser.parse_args()


def _main() -> int:
    arguments = _parse_args()
    return write_requirements_evidence(
        arguments.repo_root.resolve(),
        arguments.output,
        arguments.summary,
        base_ref=arguments.base_ref,
        staged=arguments.staged,
    )


if __name__ == "__main__":
    raise SystemExit(_main())
