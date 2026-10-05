"""Selected project plugin compatibility inside an already confined worker."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import stat
import sys
import uuid
from collections.abc import Iterator
from contextlib import ExitStack, closing, contextmanager
from importlib.metadata import Distribution, EntryPoint, distributions
from pathlib import Path
from typing import Any
from unittest.mock import patch


class ProjectPytestPluginError(ValueError):
    """Selected plugin metadata cannot be admitted unambiguously."""


class ConfinedRerunStore:
    """Project-origin failure counts shared only inside invocation storage."""

    def __init__(self, temporary: Path, *, token: str | None = None):
        if temporary.resolve() != temporary or not temporary.is_dir() or temporary.stat().st_mode & 0o077:
            raise ProjectPytestPluginError("project_native_pytest_rerun_store_root")
        create = token is None
        if token is None:
            token = "specfact-rerun-v1:" + uuid.uuid4().hex
        if not isinstance(token, str) or not re.fullmatch(r"specfact-rerun-v1:[0-9a-f]{32}", token):
            raise ProjectPytestPluginError("project_native_pytest_rerun_store_token")
        self.sock_port = token
        self.path = temporary / (".specfact-rerun-" + token.partition(":")[2] + ".sqlite")
        if create:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(descriptor)
            with self._database() as database:
                database.execute(
                    "CREATE TABLE counts (test TEXT PRIMARY KEY, failures INTEGER NOT NULL, reruns INTEGER NOT NULL)"
                )

    @contextmanager
    def _database(self) -> Iterator[sqlite3.Connection]:
        info = self.path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ProjectPytestPluginError("project_native_pytest_rerun_store_identity")
        if info.st_size > 4 << 20:
            raise ProjectPytestPluginError("project_native_pytest_rerun_store_size")
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5)) as database:
            database.execute("PRAGMA trusted_schema=OFF")
            page_size = int(database.execute("PRAGMA page_size").fetchone()[0])
            database.execute(f"PRAGMA max_page_count={(4 << 20) // page_size}")
            with database:
                yield database

    @staticmethod
    def _key(nodeid: str) -> str:
        if not isinstance(nodeid, str) or len(nodeid) > 65536:
            raise ProjectPytestPluginError("project_native_pytest_rerun_store_nodeid")
        return hashlib.sha256(nodeid.encode()).hexdigest()

    def add_test_failure(self, nodeid: str) -> None:
        with self._database() as database:
            database.execute(
                "INSERT INTO counts VALUES (?, 1, 0) ON CONFLICT(test) DO UPDATE SET failures=failures+1",
                (self._key(nodeid),),
            )

    def get_test_failures(self, nodeid: str) -> int:
        return self._get(nodeid, "failures")

    def set_test_reruns(self, nodeid: str, reruns: int) -> None:
        if type(reruns) is not int or not 0 <= reruns <= 2147483647:
            raise ProjectPytestPluginError("project_native_pytest_rerun_store_count")
        with self._database() as database:
            database.execute(
                "INSERT INTO counts VALUES (?, 0, ?) ON CONFLICT(test) DO UPDATE SET reruns=excluded.reruns",
                (self._key(nodeid), reruns),
            )

    def get_test_reruns(self, nodeid: str) -> int:
        return self._get(nodeid, "reruns")

    def _get(self, nodeid: str, column: str) -> int:
        query = (
            "SELECT failures FROM counts WHERE test=?"
            if column == "failures"
            else "SELECT reruns FROM counts WHERE test=?"
        )
        with self._database() as database:
            row = database.execute(query, (self._key(nodeid),)).fetchone()
            return int(row[0]) if row else 0


@contextmanager
def installed_rerunfailures(plugins: dict[str, tuple[object, object]], temporary: Path | None) -> Iterator[None]:
    with ExitStack() as stack:
        for plugin, distribution in plugins.values():
            if getattr(plugin, "__name__", None) != "pytest_rerunfailures":
                continue
            if getattr(distribution, "version", None) != "14.0":
                raise ProjectPytestPluginError("project_native_pytest_rerunfailures_version_unsupported")
            if temporary is None:
                raise ProjectPytestPluginError("project_native_pytest_rerun_store_root")

            def server() -> ConfinedRerunStore:
                assert temporary is not None
                return ConfinedRerunStore(temporary)

            def client(token: str) -> ConfinedRerunStore:
                assert temporary is not None
                return ConfinedRerunStore(temporary, token=token)

            stack.enter_context(patch.object(plugin, "ServerStatusDB", server))
            stack.enter_context(patch.object(plugin, "ClientStatusDB", client))
        yield


def project_pytest_plugins(project: Path, *, include_coverage: bool = False) -> dict[str, tuple[object, object]]:
    site = project / ".specfact-project-runtime/site-packages"
    entries: dict[str, tuple[EntryPoint, Distribution]] = {}
    for distribution in distributions(path=[str(site)]):
        for entry in distribution.entry_points:
            if entry.group != "pytest11" or (entry.value == "pytest_cov.plugin" and not include_coverage):
                continue
            if entry.name in entries:
                raise ProjectPytestPluginError("project_native_pytest_plugin_ambiguous")
            if (
                len(entries) >= 128
                or len(entry.value) > 512
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*(?::[A-Za-z_][A-Za-z0-9_.]*)?", entry.value)
            ):
                raise ProjectPytestPluginError("project_native_pytest_plugin_invalid")
            entries[entry.name] = (entry, distribution)
    from pluggy._manager import DistFacade

    return {name: (entry.load(), DistFacade(distribution)) for name, (entry, distribution) in sorted(entries.items())}


@contextmanager
def installed_child_pytest_plugins(project: Path, *, temporary: Path | None = None) -> Iterator[None]:
    """Lazily cover pytest config creation without requiring pytest in a child."""
    with ExitStack() as stack:
        installed: set[int] = set()

        def install(config_module: Any) -> None:
            if config_module is None or id(config_module) in installed or not hasattr(config_module, "get_config"):
                return
            installed.add(id(config_module))
            original = config_module.get_config

            def get_config(*args: Any, **kwargs: Any) -> Any:
                import pytest_cov.plugin as coverage_plugin

                config = original(*args, **kwargs)
                explicit = config.invocation_params.plugins or ()
                manager = config.pluginmanager

                def supplied(plugin: object, name: str) -> bool:
                    module_name = getattr(plugin, "__name__", None)
                    return any(
                        candidate is plugin or (isinstance(candidate, str) and candidate in {name, module_name})
                        for candidate in explicit
                    )

                plugins = project_pytest_plugins(project, include_coverage=True)
                stack.enter_context(installed_rerunfailures(plugins, temporary))
                for name, (plugin, distribution) in plugins.items():
                    if supplied(plugin, name) or manager.register(plugin, name) is not None:
                        manager._plugin_distinfo.append((plugin, distribution))
                if (
                    not supplied(coverage_plugin, "pytest_cov")
                    and not manager.hasplugin("pytest_cov")
                    and not manager.is_blocked("pytest_cov")
                ):
                    manager.register(coverage_plugin, "pytest_cov")
                return config

            stack.enter_context(patch.object(config_module, "get_config", get_config))

        class ConfigLoader:
            def __init__(self, loader: Any):
                self.loader = loader

            def create_module(self, spec: Any) -> Any:
                create = getattr(self.loader, "create_module", None)
                return create(spec) if create is not None else None

            def exec_module(self, module: Any) -> None:
                self.loader.exec_module(module)
                install(module)

            def __getattr__(self, name: str) -> Any:
                return getattr(self.loader, name)

        class ConfigFinder:
            def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
                if fullname != "_pytest.config":
                    return None
                for finder in tuple(sys.meta_path):
                    if finder is self:
                        continue
                    spec = finder.find_spec(fullname, path, target)
                    if spec is not None:
                        if spec.loader is not None:
                            spec.loader = ConfigLoader(spec.loader)
                        return spec
                return None

        install(sys.modules.get("_pytest.config"))
        finder = ConfigFinder()
        sys.meta_path.insert(0, finder)
        try:
            yield
        finally:
            sys.meta_path[:] = [candidate for candidate in sys.meta_path if candidate is not finder]
