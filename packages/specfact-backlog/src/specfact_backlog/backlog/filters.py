"""Backlog filter model re-exported from core runtime."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from specfact_cli.backlog.filters import BacklogFilters
else:
    BacklogFilters = import_module("specfact_cli.backlog.filters").BacklogFilters


__all__ = ["BacklogFilters"]
