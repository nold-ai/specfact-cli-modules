"""Isolated target-child startup; only standard-library imports precede target setup."""

from __future__ import annotations

import builtins
import faulthandler
import importlib.machinery
import importlib.metadata
import importlib.util
import io
import json
import os
import pkgutil
import re
import runpy
import site
import sys
import sysconfig
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType


PROJECT = Path("/opt/specfact/project-runtime")
SNAPSHOT = Path("/opt/specfact/snapshot")
ANALYZERS = Path("/opt/specfact/config/member-analyzers")
BUILTIN = Path("/opt/specfact/builtin")
CONTEXT = Path("/opt/specfact/config/python-context")
_OWNED_COVERAGE_MODULES: dict[str, ModuleType] = {}
_TOOL_IMPORTS = {
    "pylint": {"pylint", "astroid"},
    "crosshair": {"crosshair", "z3"},
    "basedpyright": {"basedpyright", "nodejs_wheel"},
}


def _verified_analyzer_spec(fullname: str, spec, *, analyzer_root: Path | None = None):
    """Confine module origins and every namespace portion to the verified mount."""
    locations = [] if spec is None else list(spec.submodule_search_locations or ())
    if spec is not None and spec.origin:
        locations.append(spec.origin)
    root = (analyzer_root or ANALYZERS).resolve()
    if not locations or any(not Path(location).resolve().is_relative_to(root) for location in locations):
        raise ImportError(f"project_worker_analyzer_origin_mismatch:{fullname}")
    return spec


class AnalyzerFinder:
    """Pin analyzer entry-point packages while allowing target-owned dependencies."""

    def __init__(self, names: set[str], *, analyzer_root: Path | None = None) -> None:
        self.names = names
        self.analyzer_root = analyzer_root or ANALYZERS

    def find_spec(self, fullname: str, path=None, target=None):
        del target
        if fullname.split(".")[0] not in self.names:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path or [str(self.analyzer_root)])
        return _verified_analyzer_spec(fullname, spec, analyzer_root=self.analyzer_root)

    def validate_loaded(self) -> None:
        """Reject cached project modules instead of silently replacing their objects."""
        for fullname, module in tuple(sys.modules.items()):
            if fullname.split(".")[0] in self.names:
                _verified_analyzer_spec(fullname, getattr(module, "__spec__", None), analyzer_root=self.analyzer_root)


class DomainFinder(AnalyzerFinder, importlib.metadata.DistributionFinder):
    """Pin this member's recorded analyzer-owned dependency closure."""

    def __init__(self, graph: dict, *, analyzer_root: Path | None = None) -> None:
        super().__init__(set(graph["sealed_imports"]), analyzer_root=analyzer_root)
        self.distributions = {row["name"] for row in graph["installed"] if row["origin"] == "analyzer"}

    def find_distributions(self, context=None):
        context = context or importlib.metadata.DistributionFinder.Context()
        # Explicit target inventories must never enumerate analyzer plugins.
        if tuple(context.path) != tuple(sys.path):
            return iter(())
        requested = re.sub(r"[-_.]+", "-", context.name).lower() if context.name else None
        return (
            distribution
            for distribution in importlib.metadata.distributions(path=[str(self.analyzer_root)])
            if (name := re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()) in self.distributions
            and (requested is None or requested == name)
        )


class RestrictedDomainFinder(DomainFinder):
    """Expose a member's analyzer location without general package fallback."""

    def __init__(self, graph: dict, *, analyzer_root: Path, project_site: Path) -> None:
        super().__init__(graph, analyzer_root=analyzer_root)
        self.project_site = project_site

    def find_spec(self, fullname: str, path=None, target=None):
        if fullname.partition(".")[0] in self.names:
            return super().find_spec(fullname, path, target)
        search = path or sys.path
        project_search = [
            location for location in search if not Path(location).resolve().is_relative_to(self.analyzer_root.resolve())
        ]
        spec = importlib.machinery.PathFinder.find_spec(fullname, project_search)
        if spec is not None:
            return spec
        spec = importlib.machinery.PathFinder.find_spec(fullname, search)
        locations = [] if spec is None else list(spec.submodule_search_locations or ())
        if spec is not None and spec.origin and spec.origin not in {"built-in", "frozen"}:
            locations.append(spec.origin)
        if any(Path(location).resolve().is_relative_to(self.analyzer_root.resolve()) for location in locations):
            raise ModuleNotFoundError(f"project_worker_unrelated_analyzer_import:{fullname}")
        return spec

    def find_distributions(self, context=None):
        context = context or importlib.metadata.DistributionFinder.Context()
        roots = {str(self.project_site.resolve()): "project", str(self.analyzer_root.resolve()): "analyzer"}
        for path in context.path:
            origin = roots.get(str(Path(path).resolve()))
            if origin is None:
                continue
            selected = importlib.metadata.DistributionFinder.Context(name=context.name, path=[path])
            # Query the standard directory scanner directly, avoiding recursive
            # dispatch and excluding every unrelated analyzer distribution.
            for distribution in importlib.metadata.MetadataPathFinder.find_distributions(selected):
                name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
                if (origin == "analyzer" and name in self.distributions) or (
                    origin == "project" and name not in self.distributions
                ):
                    yield distribution


class ImportPathFinder:
    """Resolve ordinary imports without widening the member's metadata domain."""

    find_spec = staticmethod(importlib.machinery.PathFinder.find_spec)


def _stdlib_paths() -> list[str]:
    """Exclude target and analyzer paths before rebuilding an execution domain."""
    stdlib = Path(sysconfig.get_path("stdlib"))
    allowed = {
        stdlib,
        stdlib / "lib-dynload",
        Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}{sys.version_info.minor}.zip",
    }
    canonical = {path.resolve() for path in allowed}
    return [path for path in sys.path if path and Path(path).resolve() in canonical]


def _dispatch_callable_state(value) -> tuple:
    """Detect replacement and in-place changes to dispatch function implementations."""
    return (
        id(value),
        getattr(value, "__code__", None),
        getattr(value, "__defaults__", None),
        tuple(sorted((getattr(value, "__kwdefaults__", None) or {}).items())),
    )


def _dispatch_namespace_state(namespace: Mapping[str, object]) -> tuple:
    """Retain each namespace member's identity and callable implementation."""
    return tuple((name, _dispatch_callable_state(value)) for name, value in namespace.items())


def _protected_dispatch_state() -> tuple:
    """Bind runpy's dispatch namespace and the code-loading primitives it consumes."""
    namespace = _dispatch_namespace_state(vars(runpy))
    classes = (
        importlib.machinery.SourceFileLoader,
        importlib.machinery.SourcelessFileLoader,
        *(value for value in vars(runpy).values() if isinstance(value, type)),
    )
    class_state = tuple((id(base), _dispatch_namespace_state(vars(base))) for cls in classes for base in cls.__mro__)
    primitives = (
        builtins.exec,
        builtins.compile,
        io.open_code,
        importlib.util.find_spec,
        importlib.util.find_spec.__globals__.get("_find_spec"),
        pkgutil.get_importer,
        pkgutil.read_code,
        os.fsdecode,
        os.path.abspath,
    )
    modules = tuple(id(sys.modules.get(name)) for name in ("runpy", "pkgutil", "io", "importlib.util"))
    return namespace, class_state, tuple(_dispatch_callable_state(value) for value in primitives), modules


def _protected_import_state(finder: AnalyzerFinder) -> tuple:
    """Snapshot the lookup machinery and graph that startup hooks must preserve."""
    return (
        builtins.__import__,
        importlib.machinery.PathFinder.find_spec,
        _verified_analyzer_spec,
        finder.find_spec,
        finder.validate_loaded,
        getattr(finder, "find_distributions", None),
        frozenset(finder.names),
        frozenset(getattr(finder, "distributions", ())),
        id(sys.modules),
        PROJECT.resolve(),
        SNAPSHOT.resolve(),
        ANALYZERS.resolve(),
        BUILTIN.resolve(),
        _protected_dispatch_state(),
    )


def _validate_target_paths(allowed: tuple[Path, ...]) -> None:
    """Retain rebased editable roots without admitting unrelated startup paths."""
    for path in sys.path:
        if not isinstance(path, str) or not any(Path(path).resolve().is_relative_to(root) for root in allowed):
            raise RuntimeError(
                "project_worker_startup_path_escape; inspect target .pth files and "
                "rebuild editable installs against the copied project"
            )


def _configure_member_site(finder: AnalyzerFinder, stdlib_paths: list[str]) -> None:
    """Preserve additive editable hooks and reestablish member lookup precedence."""
    state = _protected_import_state
    expected = state(finder)
    protected = {id(entry) for entry in sys.meta_path}
    allowed = tuple(Path(path).resolve() for path in [*stdlib_paths, PROJECT, SNAPSHOT, ANALYZERS])
    site.addsitedir(str(PROJECT / "site-packages"))
    try:
        unchanged = state(finder) == expected and protected <= {id(entry) for entry in sys.meta_path}
    except (AttributeError, TypeError):
        unchanged = False
    if not unchanged:
        raise RuntimeError(
            "project_worker_startup_import_state_changed; target .pth hooks must preserve protected import machinery"
        )
    sys.meta_path[:] = [finder, *(entry for entry in sys.meta_path if entry is not finder)]
    _validate_target_paths(allowed)
    finder.validate_loaded()


def _load_pytest_coverage() -> ModuleType:
    """Load only the fixed builtin helper, rejecting cached customer aliases."""
    alias = "_specfact_target_coverage"
    helper = Path(__file__).with_name("target_coverage.py")
    if helper.is_symlink() or not helper.is_file():
        raise ImportError("project_pytest_coverage_helper_unavailable")
    if alias in sys.modules:
        loaded = sys.modules[alias]
        owned = _OWNED_COVERAGE_MODULES.get(alias)
        origin = getattr(getattr(loaded, "__spec__", None), "origin", None)
        filename = getattr(loaded, "__file__", None)
        if loaded is not owned or not origin or not filename:
            raise ImportError("project_pytest_coverage_helper_origin_mismatch")
        if Path(origin).resolve() != helper.resolve() or Path(filename).resolve() != helper.resolve():
            raise ImportError("project_pytest_coverage_helper_origin_mismatch")
        return loaded
    spec = importlib.util.spec_from_file_location(alias, helper)
    if spec is None or spec.loader is None:
        raise ImportError("project_pytest_coverage_helper_unavailable")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[alias] = loaded
    try:
        spec.loader.exec_module(loaded)
    except BaseException:
        if sys.modules.get(alias) is loaded:
            del sys.modules[alias]
        raise
    _OWNED_COVERAGE_MODULES[alias] = loaded
    return loaded


def _configure_runtime(module: str) -> None:
    """Initialize only the target worker; project Python gets no analyzer fallbacks."""
    caller_paths = _caller_pythonpath()
    set_paths, prepend = list.__setitem__, slice(0, 0)
    descriptor = json.loads((PROJECT / "project-runtime.json").read_text(encoding="utf-8"))
    stdlib_paths = _stdlib_paths()
    sys.path[:] = stdlib_paths
    finder = AnalyzerFinder(set(_TOOL_IMPORTS.get(module, set())))
    if module != "project-python":
        finder = DomainFinder(descriptor["inventory"]["member_graphs"][module])
        finder.names.update(_TOOL_IMPORTS.get(module, set()))
    sys.meta_path.insert(0, finder)
    finder.validate_loaded()
    roots = descriptor["project"]["source_roots"]
    sys.path.extend(str(SNAPSHOT / root) for root in roots)
    if module == "project-python":
        site.addsitedir(str(PROJECT / "site-packages"))
    else:
        _configure_member_site(finder, stdlib_paths)
        sys.path.append(str(ANALYZERS))
    set_paths(sys.path, prepend, caller_paths)
    sys.executable = str(PROJECT / "bin/python")
    if module == "pytest-observe":
        _load_pytest_coverage()


def _caller_pythonpath() -> list[str]:
    """Consume caller configuration before hooks; defer paths until member sealing."""
    encoded = os.environ.pop("_SPECFACT_CALLER_PYTHONPATH", None)
    if encoded is None:
        return []
    pythonpath = json.loads(encoded)
    if pythonpath is None:
        os.environ.pop("PYTHONPATH", None)
        return []
    os.environ["PYTHONPATH"] = pythonpath
    return [os.path.abspath(path) for path in pythonpath.split(os.pathsep)] if pythonpath else []


def python_execution_domain() -> str:
    """Keep subprocesses in the recorded domain even with an empty environment."""
    launcher = runpy.run_path(
        str(Path(__file__).with_name("target_launch.py")), init_globals={"CONTEXT": CONTEXT, "BUILTIN": BUILTIN}
    )
    return launcher["execution_domain"]()


def _validate_python_arguments(arguments: list[str]) -> None:
    skip_value = False
    for argument in arguments:
        if skip_value:
            skip_value = False
            continue
        if argument in {"-c", "-m", "--"} or not argument.startswith("-") or argument == "-":
            break
        if argument.startswith(("-W", "-X")):
            skip_value = argument in {"-W", "-X"}
            continue
        unsupported = next((option for option in "IES" if option in argument[1:]), None)
        if not argument.startswith("--") and unsupported:
            raise RuntimeError(
                f"project_python_option_unsupported:-{unsupported}; this option disables required runtime attachment"
            )


def _project_python_command(arguments: list[str]) -> tuple[list[str], dict[str, str]]:
    """Use the native Python CLI, preserving -c/-m/-u and future imports exactly."""
    _validate_python_arguments(arguments)
    environment = dict(os.environ)
    environment["_SPECFACT_CALLER_PYTHONPATH"] = json.dumps(environment.get("PYTHONPATH"))
    environment.update(PYTHONPATH=str(BUILTIN / "specfact_code_review/run"), SPECFACT_PROJECT_PYTHON="1")
    launcher = runpy.run_path(str(Path(__file__).with_name("target_launch.py")))
    return launcher["interpreter_command"](["-s", *arguments]), environment


@contextmanager
def _crosshair_stack_samples(enabled: bool):
    """Temporary opt-in observations; ordinary dispatch makes no sampling calls."""
    if not enabled:
        yield
        return
    faulthandler.dump_traceback_later(5, repeat=True, file=sys.stderr)
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()


def main() -> None:
    """Enter an isolated analyzer or hand native Python arguments to its interpreter."""
    module = sys.argv.pop(1)
    diagnostic_marker = os.environ.pop("SPECFACT_CODE_REVIEW_CROSSHAIR_STACK_SAMPLES", None)
    if module.startswith("-") or module.endswith(".py") or module == "python-argv":
        arguments = sys.argv[1:] if module == "python-argv" else [module, *sys.argv[1:]]
        command, environment = _project_python_command(arguments)
        os.execve(command[0], command, environment)
    run_module, run_path = runpy.run_module, runpy.run_path
    observer_path = str(BUILTIN / "specfact_code_review/run/target_pytest.py")
    pylint_path = str(BUILTIN / "specfact_code_review/run/target_pylint.py")
    crosshair_path = str(BUILTIN / "specfact_code_review/run/target_crosshair.py")
    snapshot_root = SNAPSHOT
    with _crosshair_stack_samples(module == "crosshair" and diagnostic_marker == "1"):
        try:
            _configure_runtime(module)
        except (RuntimeError, ImportError) as exc:
            sys.stderr.write(f"{exc}\n")
            raise SystemExit(78) from exc
        if module == "pytest-observe":
            run_path(observer_path, run_name="__main__")
        elif module == "pylint":
            run_path(pylint_path, init_globals={"SNAPSHOT_ROOT": snapshot_root}, run_name="__main__")
        elif module == "crosshair":
            run_path(crosshair_path, init_globals={"ENTRY_PROGRAM": sys.argv[0]}, run_name="__main__")
        else:
            run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
