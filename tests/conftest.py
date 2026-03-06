"""Shared pytest configuration for specfact-cli-modules tests."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import suppress
from pathlib import Path

import pytest


os.environ.setdefault("TEST_MODE", "true")
MODULES_REPO_ROOT = Path(__file__).resolve().parents[1]
repo_root_str = str(MODULES_REPO_ROOT)
LOCAL_BUNDLE_SRCS = tuple(
    str(bundle_src.resolve()) for bundle_src in sorted((MODULES_REPO_ROOT / "packages").glob("*/src"))
)
USER_MODULES_MARKER = f"{Path.home() / '.specfact' / 'modules'}{os.sep}"
LOCAL_BUNDLE_PACKAGES = (
    "specfact_project",
    "specfact_backlog",
    "specfact_codebase",
    "specfact_spec",
    "specfact_govern",
)


def _is_user_module_path(path_value: str | None) -> bool:
    if not path_value:
        return False
    return USER_MODULES_MARKER in str(Path(path_value).expanduser())


def _purge_shadowed_bundle_modules() -> None:
    for module_name, module in list(sys.modules.items()):
        if not module_name.startswith(LOCAL_BUNDLE_PACKAGES):
            continue
        module_file = getattr(module, "__file__", None)
        if _is_user_module_path(module_file):
            sys.modules.pop(module_name, None)


def _filter_user_module_pythonpath() -> None:
    pythonpath = os.environ.get("PYTHONPATH", "")
    if not pythonpath:
        return
    filtered_entries = [entry for entry in pythonpath.split(os.pathsep) if entry and not _is_user_module_path(entry)]
    if filtered_entries:
        os.environ["PYTHONPATH"] = os.pathsep.join(filtered_entries)
    else:
        os.environ.pop("PYTHONPATH", None)


def _enforce_local_bundle_sources() -> None:
    cleaned_sys_path = [entry for entry in sys.path if not _is_user_module_path(entry)]
    cleaned_sys_path = [
        entry for entry in cleaned_sys_path if entry != repo_root_str and entry not in LOCAL_BUNDLE_SRCS
    ]
    sys.path[:] = [*LOCAL_BUNDLE_SRCS, repo_root_str, *cleaned_sys_path]
    _filter_user_module_pythonpath()
    _purge_shadowed_bundle_modules()


_enforce_local_bundle_sources()

# Lock specfact_project to the modules-repo package path to avoid accidental shadowing.
with suppress(ModuleNotFoundError):
    importlib.import_module("specfact_project")


def _resolve_core_repo() -> Path | None:
    configured = os.environ.get("SPECFACT_CLI_REPO")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if (candidate / "src" / "specfact_cli").exists():
            return candidate
    here = Path(__file__).resolve()
    for parent in here.parents:
        sibling = parent.parent / "specfact-cli"
        if (sibling / "src" / "specfact_cli").exists():
            return sibling.resolve()
    return None


core_repo = _resolve_core_repo()
if core_repo is not None:
    os.environ.setdefault("SPECFACT_REPO_ROOT", str(core_repo))
    os.environ.setdefault("SPECFACT_MODULES_REPO", str(MODULES_REPO_ROOT))


def pytest_sessionstart(session: pytest.Session) -> None:
    _ = session
    _enforce_local_bundle_sources()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    _ = item
    _enforce_local_bundle_sources()
