"""Shared pytest configuration for specfact-cli-modules tests."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import suppress
from pathlib import Path


os.environ.setdefault("TEST_MODE", "true")
MODULES_REPO_ROOT = Path(__file__).resolve().parents[1]

# Ensure local bundle package sources are importable during tests.
packages_root = MODULES_REPO_ROOT / "packages"
if packages_root.exists():
    for bundle_src in packages_root.glob("*/src"):
        bundle_src_str = str(bundle_src)
        if bundle_src_str not in sys.path:
            sys.path.insert(0, bundle_src_str)

# Lock specfact_project to the modules-repo package path to avoid accidental shadowing.
with suppress(ModuleNotFoundError):
    importlib.import_module("specfact_project")


def _resolve_core_repo() -> Path | None:
    configured = os.environ.get("SPECFACT_CLI_REPO")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if (candidate / "src" / "specfact_cli").exists():
            return candidate
    here = Path(__file__).resolve()
    for parent in here.parents:
        sibling = parent.parent / "specfact-cli"
        if (sibling / "src" / "specfact_cli").exists():
            return sibling.resolve()
    return None


core_repo = _resolve_core_repo()
if core_repo is not None:
    os.environ.setdefault("SPECFACT_REPO_ROOT", str(core_repo))
    os.environ.setdefault("SPECFACT_MODULES_REPO", str(MODULES_REPO_ROOT))
