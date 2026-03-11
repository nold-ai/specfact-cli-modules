#!/usr/bin/env python3
"""Ensure the active environment uses the expected local specfact-cli checkout."""

from __future__ import annotations

from dev_bootstrap_support import ROOT, ensure_core_dependency


if __name__ == "__main__":
    raise SystemExit(ensure_core_dependency(ROOT))
