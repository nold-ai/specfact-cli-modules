"""
Backlog field mappers for provider-specific field extraction and mapping.

This module provides field mappers that normalize provider-specific field structures
to canonical field names, enabling provider-agnostic backlog item handling.
"""

from specfact_backlog.backlog.mappers.ado_mapper import AdoFieldMapper
from specfact_backlog.backlog.mappers.base import FieldMapper
from specfact_backlog.backlog.mappers.github_mapper import GitHubFieldMapper


__all__ = ["AdoFieldMapper", "FieldMapper", "GitHubFieldMapper"]
