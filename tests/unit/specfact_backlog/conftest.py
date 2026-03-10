"""Pytest configuration for specfact_backlog tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


# Calculate repository root
REPO_ROOT = Path(__file__).resolve().parents[3]

# Add source paths to sys.path for this process
PACKAGES_SRC = str(REPO_ROOT / "packages" / "specfact-backlog" / "src")
SRC = str(REPO_ROOT / "src")

if PACKAGES_SRC not in sys.path:
    sys.path.insert(0, PACKAGES_SRC)
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Set PYTHONPATH for subprocesses (CliRunner)
_current_pythonpath = os.environ.get("PYTHONPATH", "")
_new_pythonpath = f"{PACKAGES_SRC}:{SRC}"
if _current_pythonpath:
    _new_pythonpath = f"{_new_pythonpath}:{_current_pythonpath}"
os.environ["PYTHONPATH"] = _new_pythonpath


# Patch CliRunner to always include proper PYTHONPATH in env
def _patch_clirunner() -> None:
    """Monkey-patch CliRunner.invoke to always include PYTHONPATH."""
    # pylint: disable=import-outside-toplevel
    from collections.abc import Callable

    from click.testing import Result
    from typer.testing import CliRunner

    original_invoke: Callable[..., Result] = CliRunner.invoke

    def patched_invoke(
        self: Any,
        cli: Any,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Result:
        # Merge our PYTHONPATH with any existing env
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        # Ensure PYTHONPATH is set
        if "PYTHONPATH" not in merged_env:
            merged_env["PYTHONPATH"] = _new_pythonpath
        # Pass merged env to original invoke
        return original_invoke(self, cli, args=args, env=merged_env, **kwargs)

    # Use Any to bypass type checking for monkey-patch
    CliRunner.invoke = patched_invoke  # type: ignore[method-assign]


_patch_clirunner()


# ruff: noqa: E402
# Import after path setup
from specfact_cli.registry.bridge_registry import BRIDGE_PROTOCOL_REGISTRY

# Trigger protocol registration by importing main module
from specfact_backlog.backlog_core import main as _main_module  # noqa: F401

# Register backlog graph protocol with bridge registry for tests
from specfact_backlog.backlog_core.adapters.backlog_protocol import BacklogGraphProtocol


BRIDGE_PROTOCOL_REGISTRY.register_protocol("backlog_graph", BacklogGraphProtocol)
