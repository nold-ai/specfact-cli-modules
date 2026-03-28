"""Shared helpers for sync CLI commands (avoids circular imports with commands.py)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from beartype import beartype
from icontract import ensure, require


@beartype
@ensure(lambda result: isinstance(result, bool), "Must return bool")
def is_test_mode() -> bool:
    """Check if running in test mode."""
    if os.environ.get("TEST_MODE") == "true":
        return True
    return any("pytest" in arg or "test" in arg.lower() for arg in sys.argv) or "pytest" in sys.modules


@beartype
@require(lambda selection: isinstance(selection, str), "Selection must be string")
@ensure(lambda result: isinstance(result, list), "Must return list")
def parse_backlog_selection(selection: str) -> list[str]:
    """Parse backlog selection string into a list of IDs/URLs."""
    if not selection:
        return []
    parts = re.split(r"[,\n\r]+", selection)
    return [part.strip() for part in parts if part.strip()]


@beartype
@require(lambda repo: isinstance(repo, Path), "Repo must be Path")
@ensure(lambda result: result is None or isinstance(result, str), "Must return None or string")
def infer_bundle_name(repo: Path) -> str | None:
    """Infer bundle name from active config or single bundle directory."""
    from specfact_cli.utils.structure import SpecFactStructure

    active_bundle = SpecFactStructure.get_active_bundle_name(repo)
    if active_bundle:
        return active_bundle

    projects_dir = repo / SpecFactStructure.PROJECTS
    if projects_dir.exists():
        candidates = [
            bundle_dir.name
            for bundle_dir in projects_dir.iterdir()
            if bundle_dir.is_dir() and (bundle_dir / "bundle.manifest.yaml").exists()
        ]
        if len(candidates) == 1:
            return candidates[0]

    return None
