"""Backlog adapter base interface for bundle-local dependencies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from beartype import beartype
from icontract import ensure, require
from specfact_cli.models.backlog_item import BacklogItem

from specfact_backlog.backlog.filters import BacklogFilters


class BacklogAdapter(ABC):
    """Abstract base interface for backlog adapters."""

    @abstractmethod
    @beartype
    @ensure(lambda result: isinstance(result, str) and len(result) > 0, "Must return non-empty adapter name")
    def name(self) -> str: ...

    @abstractmethod
    @beartype
    @require(lambda format_type: isinstance(format_type, str) and len(format_type) > 0, "Format type must be non-empty")
    @ensure(lambda result: isinstance(result, bool), "Must return boolean")
    def supports_format(self, format_type: str) -> bool: ...

    @abstractmethod
    @beartype
    @require(lambda filters: isinstance(filters, BacklogFilters), "Filters must be BacklogFilters instance")
    @ensure(lambda result: isinstance(result, list), "Must return list of BacklogItem")
    @ensure(
        lambda result, filters: all(isinstance(item, BacklogItem) for item in result), "All items must be BacklogItem"
    )
    def fetch_backlog_items(self, filters: BacklogFilters) -> list[BacklogItem]: ...

    @abstractmethod
    @beartype
    @require(lambda item: isinstance(item, BacklogItem), "Item must be BacklogItem")
    @require(
        lambda update_fields: update_fields is None or isinstance(update_fields, list),
        "Update fields must be None or list",
    )
    @ensure(lambda result: isinstance(result, BacklogItem), "Must return BacklogItem")
    @ensure(
        lambda result, item: result.id == item.id and result.provider == item.provider,
        "Updated item must preserve id and provider",
    )
    def update_backlog_item(self, item: BacklogItem, update_fields: list[str] | None = None) -> BacklogItem: ...

    @beartype
    @require(lambda original: isinstance(original, BacklogItem), "Original must be BacklogItem")
    @require(lambda updated: isinstance(updated, BacklogItem), "Updated must be BacklogItem")
    @ensure(lambda result: isinstance(result, bool), "Must return boolean")
    def validate_round_trip(self, original: BacklogItem, updated: BacklogItem) -> bool:
        return (
            original.id == updated.id
            and original.provider == updated.provider
            and original.title == updated.title
            and original.body_markdown == updated.body_markdown
            and original.state == updated.state
        )

    @beartype
    def create_backlog_item_from_spec(self) -> BacklogItem | None:
        return None

    @beartype
    @ensure(lambda result: isinstance(result, bool), "Must return boolean")
    def supports_add_comment(self) -> bool:
        return False

    @beartype
    def add_comment(self, item: BacklogItem, comment: str) -> bool:
        return False

    @beartype
    def get_comments(self, item: BacklogItem) -> list[str]:
        return []
