"""Shared bootstrap access for tool entrypoints."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

ensure_core_dependency = importlib.import_module("specfact_cli_modules.dev_bootstrap").ensure_core_dependency


__all__ = ["ROOT", "ensure_core_dependency"]
