"""Backlog adapter interface re-exported from core runtime."""

from __future__ import annotations

from importlib import import_module


BacklogAdapter = import_module("specfact_cli.backlog.adapters.base").BacklogAdapter


__all__ = ["BacklogAdapter"]
