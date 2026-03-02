"""Shared pytest configuration for specfact-cli-modules tests."""

from __future__ import annotations

import os


os.environ.setdefault("TEST_MODE", "true")
