#!/usr/bin/env python3
# ruff: noqa: N999
"""Compatibility wrapper for publish_module.py."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
repo_root_str = str(REPO_ROOT)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

main = import_module("scripts.publish_module").main


if __name__ == "__main__":
    raise SystemExit(main())
