"""Observe customer pytest in its target worker, never in the controller."""

from __future__ import annotations

import glob
import importlib.metadata
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/opt/specfact/project-runtime")
SNAPSHOT_ROOT = Path("/opt/specfact/snapshot")


def _explicit_plugins(config: dict[str, Any]) -> set[str]:
    raw = config.get("addopts", [])
    tokens = shlex.split(raw) if isinstance(raw, str) else list(raw)
    explicit = {str(tokens[index + 1]) for index, token in enumerate(tokens[:-1]) if token == "-p"}
    explicit.update(str(token)[2:] for token in tokens if str(token).startswith("-p") and len(str(token)) > 2)
    return explicit


def _entry_plugins(distribution: importlib.metadata.Distribution, explicit: set[str]) -> list[str]:
    plugins = []
    for entry in distribution.entry_points:
        if entry.group != "pytest11":
            continue
        names = {entry.name, entry.value.split(":")[0]}
        if names & explicit or {f"no:{name}" for name in names} & explicit:
            continue
        plugins.extend(("-p", entry.name))
    return plugins


def _plugins(config: dict[str, Any]) -> list[str]:
    explicit = _explicit_plugins(config)
    plugins = []
    raw = config.get("addopts", [])
    options = shlex.split(raw) if isinstance(raw, str) else list(raw)
    autoload = "--disable-plugin-autoload" not in options
    for distribution in importlib.metadata.distributions(path=[str(ROOT / "site-packages")]):
        if autoload:
            plugins.extend(_entry_plugins(distribution, explicit))
    coverage_choices = {"pytest_cov", "pytest_cov.plugin", "no:pytest_cov", "no:pytest_cov.plugin"}
    if "pytest_cov" not in plugins and not coverage_choices & explicit:
        plugins.extend(("-p", "pytest_cov"))
    return plugins


def _effective_pytest_config(descriptor: dict[str, Any]) -> dict[str, Any]:
    config = dict(descriptor["project"]["pytest_config"])
    options = config.get("addopts", [])
    config["addopts"] = [
        *(shlex.split(options) if isinstance(options, str) else options),
        *descriptor["inventory"].get("pytest_arguments", []),
    ]
    return config


def _test_support_roots(config) -> list[str]:
    """Retain configured test directories without excluding the whole snapshot."""
    snapshot = SNAPSHOT_ROOT.resolve()
    roots = set()
    for pattern in config.getini("testpaths"):
        for relative in glob.iglob(pattern, root_dir=config.rootpath, recursive=True):
            path = (config.rootpath / relative).resolve()
            if path.is_dir() and path != snapshot and path.is_relative_to(snapshot):
                roots.add(path.relative_to(snapshot).as_posix())
    return sorted(roots)


class Observer:
    """Retain phase-specific facts without claiming setup failures executed test calls."""

    def __init__(self) -> None:
        self.records = []
        self.collected = set()
        self.deselected = set()
        self.deselection_inventory = "complete"
        self.worker_collected = set()
        self.collection_errors = []
        self.internal_errors = []
        self.coverage_threshold = None
        self.test_roots = []
        self.pytest_root = None

    def pytest_sessionfinish(self, session, exitstatus):
        del exitstatus
        coverage_plugin = session.config.pluginmanager.getplugin("_cov")
        self.coverage_threshold = getattr(getattr(coverage_plugin, "options", None), "cov_fail_under", None)
        self.test_roots = _test_support_roots(session.config)
        root = session.config.rootpath.resolve()
        snapshot = SNAPSHOT_ROOT.resolve()
        self.pytest_root = root.relative_to(snapshot).as_posix() if root.is_relative_to(snapshot) else str(root)

    def pytest_internalerror(self, excrepr, excinfo):
        del excinfo
        self.internal_errors.append(str(excrepr))

    def pytest_testnodedown(self, node, error):
        del node
        if error and str(error) not in self.internal_errors:
            self.internal_errors.append(str(error))

    def pytest_itemcollected(self, item):
        self.collected.add(item.nodeid)

    def pytest_deselected(self, items):
        removed = {item.nodeid for item in items}
        self.deselected.update(removed)
        self.collected.difference_update(removed)

    def pytest_collection_finish(self, session):
        selected = {item.nodeid for item in session.items} | self.worker_collected
        self.deselected.update(self.collected - selected)
        self.collected = selected

    def pytest_xdist_node_collection_finished(self, node, ids):
        del node
        self.deselection_inventory = "controller_observed"
        self.worker_collected.update(ids)
        self.collected.update(ids)

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors.append({"nodeid": report.nodeid, "detail": report.longreprtext})

    def pytest_runtest_logreport(self, report):
        self.records.append(
            {
                "nodeid": report.nodeid,
                "phase": report.when,
                "outcome": report.outcome,
                "wasxfail": str(getattr(report, "wasxfail", "")),
                "has_xfail": hasattr(report, "wasxfail"),
                "detail": report.longreprtext if report.failed else "",
            }
        )


def main() -> None:
    import pytest

    pytest.hookimpl(optionalhook=True)(Observer.pytest_xdist_node_collection_finished)
    pytest.hookimpl(optionalhook=True)(Observer.pytest_testnodedown)
    request = json.loads(sys.argv[1])
    descriptor = json.loads((ROOT / "project-runtime.json").read_text(encoding="utf-8"))
    output = Path("/opt/specfact/tmp/pytest-observation.json")
    observer = Observer()

    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    coverage_output = Path("/opt/specfact/tmp/coverage.json")
    os.environ["COVERAGE_FILE"] = "/opt/specfact/tmp/.coverage"
    args = [
        *_plugins(_effective_pytest_config(descriptor)),
        *descriptor["inventory"].get("pytest_arguments", []),
        "-o",
        "cache_dir=/opt/specfact/tmp/pytest-cache",
        "--basetemp=/opt/specfact/tmp/pytest",
        "--cov=/opt/specfact/snapshot",
        f"--cov-report=json:{coverage_output}",
        *request["selectors"],
    ]
    code = pytest.main(args, plugins=[observer])
    output.write_text(
        json.dumps(
            {
                "exit_code": int(code),
                "collected": sorted(observer.collected),
                "deselected": sorted(observer.deselected),
                "deselection_inventory": observer.deselection_inventory,
                "records": observer.records,
                "collection_errors": observer.collection_errors,
                "internal_errors": observer.internal_errors,
                "pytest_version": pytest.__version__,
                "coverage_version": importlib.metadata.version("coverage"),
                "pytest_cov_version": importlib.metadata.version("pytest-cov"),
                "coverage_threshold": observer.coverage_threshold,
                "test_roots": observer.test_roots,
                "pytest_root": observer.pytest_root,
                "argv": args,
                "configured_addopts": descriptor["project"]["pytest_config"].get("addopts", []),
                "coverage": json.loads(coverage_output.read_text(encoding="utf-8"))
                if coverage_output.is_file()
                else {},
            }
        ),
        encoding="utf-8",
    )
    raise SystemExit(int(code))


if __name__ == "__main__":
    main()
