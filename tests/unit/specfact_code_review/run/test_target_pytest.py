"""Explicit pytest plugin modules must not be registered twice."""

from types import SimpleNamespace

import pytest

from specfact_code_review.run import target_pytest
from specfact_code_review.run.target_pytest import _installed_coverage_modules


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


def test_disabled_autoload_preserves_only_explicit_plugins_and_coverage(monkeypatch) -> None:
    packages = [
        SimpleNamespace(
            metadata={"Name": name}, entry_points=[SimpleNamespace(group="pytest11", name=entry, value=value)]
        )
        for name, entry, value in [
            ("pytest-asyncio", "asyncio", "pytest_asyncio.plugin"),
            ("pytest-cov", "pytest_cov", "pytest_cov.plugin"),
        ]
    ]
    monkeypatch.setattr(target_pytest.importlib.metadata, "distributions", lambda **_kwargs: packages)
    for options in ["--disable-plugin-autoload", ["--disable-plugin-autoload"]]:
        assert target_pytest._plugins({"addopts": options}) == ["-p", "pytest_cov"]
    assert not target_pytest._plugins(
        {"addopts": "--disable-plugin-autoload -p pytest_cov.plugin -p pytest_asyncio.plugin"}
    )
    assert not target_pytest._plugins({"addopts": "--disable-plugin-autoload -p no:pytest_cov"})


@pytest.mark.parametrize(
    "modules", [None, "standalone", [1], ["../escape"], ["pkg.module"], ["class"], ["missing"], ["linked"]]
)
def test_installed_module_selector_rejects_unattached_or_invalid_names(tmp_path, monkeypatch, modules):
    site = tmp_path / "site-packages"
    site.mkdir()
    external = tmp_path / "external.py"
    external.write_text("VALUE = 1\n")
    (site / "linked.py").symlink_to(external)
    monkeypatch.setattr(target_pytest, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="project_pytest_installed_coverage_module_invalid"):
        _installed_coverage_modules({"coverage_modules": modules})


def test_installed_module_selector_accepts_only_regular_attached_module(tmp_path, monkeypatch):
    site = tmp_path / "site-packages"
    site.mkdir()
    (site / "standalone.py").write_text("VALUE = 1\n")
    monkeypatch.setattr(target_pytest, "ROOT", tmp_path)
    assert _installed_coverage_modules({"coverage_modules": ["standalone"]}) == ["standalone"]
    assert _installed_coverage_modules({}) == []
