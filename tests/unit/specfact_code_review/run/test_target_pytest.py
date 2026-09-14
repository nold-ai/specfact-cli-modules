"""Explicit pytest plugin modules must not be registered twice."""

from types import SimpleNamespace

from specfact_code_review.run import target_pytest


def test_explicit_plugin_module_does_not_also_load_entry_point(monkeypatch) -> None:
    distribution = SimpleNamespace(
        metadata={"Name": "pytest-asyncio"},
        entry_points=[SimpleNamespace(group="pytest11", name="asyncio", value="pytest_asyncio.plugin")],
    )
    monkeypatch.setattr(target_pytest.importlib.metadata, "distributions", lambda **kwargs: [distribution])
    assert "asyncio" not in target_pytest._plugins({"addopts": "-p pytest_asyncio.plugin"})
    assert "asyncio" in target_pytest._plugins({"addopts": "-ra"})
    assert "asyncio" not in target_pytest._plugins({"addopts": "-p no:asyncio"})
