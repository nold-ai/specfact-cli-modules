"""Backlog filter model re-exported from core runtime."""

from __future__ import annotations

from importlib import import_module


BacklogFilters = import_module("specfact_cli.backlog.filters").BacklogFilters


__all__ = ["BacklogFilters"]
