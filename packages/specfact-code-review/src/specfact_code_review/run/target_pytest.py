"""Observe customer pytest in its target worker, never in the controller."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/opt/specfact/project-runtime")


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
    target_names = set()
    for distribution in importlib.metadata.distributions(path=[str(ROOT / "site-packages")]):
        target_names.add(distribution.metadata["Name"].lower().replace("_", "-"))
        plugins.extend(_entry_plugins(distribution, explicit))
    if "pytest-cov" not in target_names and not {"no:pytest_cov", "no:pytest_cov.plugin"} & explicit:
        plugins.extend(("-p", "pytest_cov"))
    return plugins


def main() -> None:
    import pytest

    request = json.loads(sys.argv[1])
    descriptor = json.loads((ROOT / "project-runtime.json").read_text(encoding="utf-8"))
    output = Path("/opt/specfact/tmp/pytest-observation.json")
    records = []
    collected = set()

    class Observer:
        def pytest_itemcollected(self, item):
            collected.add(item.nodeid)

        @pytest.hookimpl(optionalhook=True)
        def pytest_xdist_node_collection_finished(self, node, ids):
            del node
            collected.update(ids)

        def pytest_runtest_logreport(self, report):
            records.append(
                {
                    "nodeid": report.nodeid,
                    "phase": report.when,
                    "outcome": report.outcome,
                    "wasxfail": str(getattr(report, "wasxfail", "")),
                }
            )

    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    coverage_output = Path("/opt/specfact/tmp/coverage.json")
    os.environ["COVERAGE_FILE"] = "/opt/specfact/tmp/.coverage"
    args = [
        *_plugins(descriptor["project"]["pytest_config"]),
        "-o",
        "cache_dir=/opt/specfact/tmp/pytest-cache",
        "--basetemp=/opt/specfact/tmp/pytest",
        "--cov=/opt/specfact/snapshot",
        f"--cov-report=json:{coverage_output}",
        *request["selectors"],
    ]
    code = pytest.main(args, plugins=[Observer()])
    output.write_text(
        json.dumps(
            {
                "exit_code": int(code),
                "collected": sorted(collected),
                "records": records,
                "pytest_version": pytest.__version__,
                "coverage_version": importlib.metadata.version("coverage"),
                "pytest_cov_version": importlib.metadata.version("pytest-cov"),
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
