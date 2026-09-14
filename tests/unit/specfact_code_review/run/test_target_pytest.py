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


def test_observer_retains_setup_failure_details() -> None:
    observer = target_pytest.Observer()
    observer.pytest_runtest_logreport(
        SimpleNamespace(
            nodeid="test_app.py::test_app",
            when="setup",
            outcome="failed",
            longreprtext="TypeError: str expected, not NoneType",
            failed=True,
        )
    )
    assert observer.records[0]["detail"] == "TypeError: str expected, not NoneType"
    observer.pytest_collectreport(
        SimpleNamespace(nodeid="test_app.py", failed=True, longreprtext="ImportError: missing_plugin")
    )
    assert observer.collection_errors == [{"nodeid": "test_app.py", "detail": "ImportError: missing_plugin"}]


def test_observer_retains_internal_plugin_errors() -> None:
    observer = target_pytest.Observer()
    observer.pytest_internalerror("socket.gaierror: localhost unavailable", None)
    assert observer.internal_errors == ["socket.gaierror: localhost unavailable"]


def test_native_hatch_plugin_options_participate_in_explicit_selection() -> None:
    descriptor = {
        "project": {"pytest_config": {"addopts": "-ra"}},
        "inventory": {"pytest_arguments": ["-p", "no:randomly"]},
    }
    assert target_pytest._effective_pytest_config(descriptor)["addopts"] == ["-ra", "-p", "no:randomly"]


def test_observer_retains_xdist_worker_startup_failure() -> None:
    observer = target_pytest.Observer()
    observer.pytest_testnodedown(None, "coverage storage is read-only")
    assert observer.internal_errors == ["coverage storage is read-only"]
