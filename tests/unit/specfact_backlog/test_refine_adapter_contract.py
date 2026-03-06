from __future__ import annotations

import importlib

from specfact_cli.backlog.adapters.base import BacklogAdapter as CoreBacklogAdapter
from specfact_cli.models.backlog_item import BacklogItem


def test_fetch_backlog_items_accepts_core_backlog_adapter(monkeypatch) -> None:
    backlog_commands = importlib.import_module("specfact_backlog.backlog.commands")

    class _CoreAdapter(CoreBacklogAdapter):
        def name(self) -> str:
            return "ado"

        def supports_format(self, format_type: str) -> bool:
            _ = format_type
            return True

        def fetch_backlog_items(self, filters):  # type: ignore[no-untyped-def]
            _ = filters
            return [
                BacklogItem(
                    id="185",
                    provider="ado",
                    url="https://dev.azure.com/org/project/_apis/wit/workitems/185",
                    title="Fix the error",
                    body_markdown="Description",
                    state="New",
                )
            ]

        def update_backlog_item(self, item: BacklogItem, update_fields: list[str] | None = None) -> BacklogItem:
            _ = update_fields
            return item

    class _Registry:
        def get_adapter(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            return _CoreAdapter()

    def _registry_factory() -> _Registry:
        return _Registry()

    monkeypatch.setattr(backlog_commands, "AdapterRegistry", _registry_factory)

    # pylint: disable=protected-access
    items = backlog_commands._fetch_backlog_items(
        "ado",
        ado_org="test-org",
        ado_project="test-project",
        ado_token="test-token",
        limit=1,
    )

    assert len(items) == 1
    assert items[0].id == "185"
