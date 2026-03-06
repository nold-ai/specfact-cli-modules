#!/usr/bin/env python3
# ruff: noqa: N999
"""Compatibility wrapper for publish_module.py."""

from __future__ import annotations

from scripts.publish_module import main


if __name__ == "__main__":
    raise SystemExit(main())
