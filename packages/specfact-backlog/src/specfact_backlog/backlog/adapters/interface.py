"""Backlog adapter interface re-exported from core runtime."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from specfact_cli.backlog.adapters.base import BacklogAdapter
else:
    BacklogAdapter = import_module("specfact_cli.backlog.adapters.base").BacklogAdapter


__all__ = ["BacklogAdapter"]
