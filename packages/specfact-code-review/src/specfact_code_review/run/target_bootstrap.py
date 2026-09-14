"""Isolated target-child startup; only standard-library imports precede target setup."""

from __future__ import annotations

import importlib.machinery
import json
import os
import runpy
import site
import sys
import sysconfig
from pathlib import Path


PROJECT = Path("/opt/specfact/project-runtime")
SNAPSHOT = Path("/opt/specfact/snapshot")
ANALYZERS = Path("/opt/specfact/analyzers")
BUILTIN = Path("/opt/specfact/builtin")
_TOOL_IMPORTS = {
    "pylint": {"pylint", "astroid"},
    "crosshair": {"crosshair", "z3"},
    "basedpyright": {"basedpyright", "nodejs_wheel"},
}


class AnalyzerFinder:
    """Pin analyzer entry-point packages while allowing target-owned dependencies."""

    def __init__(self, names: set[str]) -> None:
        self.names = names

    def find_spec(self, fullname: str, path=None, target=None):
        del target
        if fullname.split(".")[0] not in self.names:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path or [str(ANALYZERS)])
        if spec is None or (spec.origin and not Path(spec.origin).is_relative_to(ANALYZERS)):
            raise ImportError(f"project_worker_analyzer_origin_mismatch:{fullname}")
        return spec


def _stdlib_paths() -> list[str]:
    """Exclude target and analyzer paths before rebuilding an execution domain."""
    stdlib = Path(sysconfig.get_path("stdlib"))
    allowed = {
        stdlib,
        stdlib / "lib-dynload",
        Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}{sys.version_info.minor}.zip",
    }
    return [path for path in sys.path if path and Path(path) in allowed]


def _configure_runtime(module: str) -> None:
    """Initialize only the target worker; project Python gets no analyzer fallbacks."""
    descriptor = json.loads((PROJECT / "project-runtime.json").read_text(encoding="utf-8"))
    sys.path[:] = _stdlib_paths()
    sys.meta_path.insert(0, AnalyzerFinder(_TOOL_IMPORTS.get(module, set())))
    roots = descriptor["project"]["source_roots"]
    sys.path.extend(str(SNAPSHOT / root) for root in roots)
    site.addsitedir(str(PROJECT / "site-packages"))
    if module != "project-python":
        sys.path.append(str(ANALYZERS))
    sys.executable = str(PROJECT / "bin/python")


def _project_python_command(arguments: list[str]) -> tuple[list[str], dict[str, str]]:
    """Use the native Python CLI, preserving -c/-m/-u and future imports exactly."""
    environment = dict(os.environ)
    environment.update(PYTHONPATH=str(BUILTIN / "specfact_code_review/run"), SPECFACT_PROJECT_PYTHON="1")
    return ["/opt/specfact/python/bin/python", "-s", *arguments], environment


def main() -> None:
    """Enter an isolated analyzer or hand native Python arguments to its interpreter."""
    module = sys.argv.pop(1)
    if module.startswith("-") or module.endswith(".py") or module == "python-argv":
        arguments = sys.argv[1:] if module == "python-argv" else [module, *sys.argv[1:]]
        command, environment = _project_python_command(arguments)
        os.execve(command[0], command, environment)
    _configure_runtime(module)
    if module == "pytest-observe":
        runpy.run_path(str(BUILTIN / "specfact_code_review/run/target_pytest.py"), run_name="__main__")
    else:
        runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
