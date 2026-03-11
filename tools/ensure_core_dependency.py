#!/usr/bin/env python3
"""Ensure the active environment uses the expected local specfact-cli checkout."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    from specfact_cli_modules.dev_bootstrap import ensure_core_dependency

    raise SystemExit(ensure_core_dependency(ROOT))
