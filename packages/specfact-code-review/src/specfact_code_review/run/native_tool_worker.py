"""Closed managed-tool worker for the native Darwin capsule.

The broker fixes the selected tool plan. This module validates the matching
immutable request, projects only admitted capsule paths and either runs a
Python tool in-process or replaces itself with one exact capsule image.
"""

from __future__ import annotations

import importlib
import json
import os
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path, PurePosixPath
from typing import Final, cast

import yaml
from beartype import beartype
from icontract import require


REQUEST_NAME: Final = ".specfact-native-tool-request.json"
REQUEST_SCHEMA: Final = "specfact-managed-launch-request-v1"
DIRECT_TOOLS: Final = frozenset({"basedpyright", "ruff", "semgrep"})
PYTHON_TOOLS: Final = frozenset({"crosshair", "pylint", "pytest", "radon"})
TOOLS: Final = DIRECT_TOOLS | PYTHON_TOOLS
MAX_REQUEST_BYTES: Final = 16 << 20
MAX_ARGUMENTS: Final = 128
MAX_ARGUMENT_BYTES: Final = 64 << 10
SAFE_ENVIRONMENT: Final = frozenset(
    {
        "COVERAGE_FILE",
        "HOME",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "RUFF_CACHE_DIR",
        "SEMGREP_SEND_METRICS",
        "SEMGREP_SETTINGS_FILE",
        "TMPDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
    }
)


class ToolRequestError(ValueError):
    """The fixed tool request differs from its admitted plan."""


def _validate_root_permissions(mode: int, writable: bool, private_tree: bool) -> None:
    if private_tree and (not mode & stat.S_IWUSR or mode & (stat.S_IRWXG | stat.S_IRWXO)):
        raise ToolRequestError("private tool root is not owner-only")
    if writable and not private_tree and not mode & stat.S_IWUSR:
        raise ToolRequestError("writable tool root is not owner-writable")
    if not writable and not private_tree and mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise ToolRequestError("immutable tool root is writable")


def _root(raw: str, *, writable: bool, private_tree: bool = False) -> Path:
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink():
        raise ToolRequestError("tool roots must be absolute non-symlink directories")
    resolved = path.resolve(strict=True)
    if resolved != path or not resolved.is_dir():
        raise ToolRequestError("tool root identity changed during resolution")
    _validate_root_permissions(resolved.stat().st_mode, writable, private_tree)
    return resolved


def _roots() -> tuple[Path, Path, Path, Path, str]:
    if len(sys.argv) != 6:
        raise ToolRequestError("tool worker requires four roots and one fixed tool")
    capsule = _root(sys.argv[1], writable=True, private_tree=True)
    project = _root(sys.argv[2], writable=False)
    output = _root(sys.argv[3], writable=True)
    temporary = _root(sys.argv[4], writable=True)
    tool = sys.argv[5]
    roots = (capsule, project, output, temporary)
    if (
        tool not in TOOLS
        or len(set(roots)) != len(roots)
        or any(
            left.is_relative_to(right) or right.is_relative_to(left)
            for index, left in enumerate(roots)
            for right in roots[index + 1 :]
        )
    ):
        raise ToolRequestError("tool plan or root separation is invalid")
    return capsule, project, output, temporary, tool


def _validate_request_plan(request: dict[str, object], tool: str) -> None:
    timeout = request["timeout_ms"]
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["tool"] != tool
        or request["capture_output"] is not True
        or request["text"] is not True
        or request["cwd"] != "project"
        or type(request["sequence"]) is not int
        or cast(int, request["sequence"]) < 0
        or type(timeout) is not int
        or not 1 <= cast(int, timeout) <= 240_000
    ):
        raise ToolRequestError("tool request payload differs from its fixed plan")


def _validate_request_arguments(argv: object, tool: str) -> None:
    if (
        not isinstance(argv, list)
        or not argv
        or len(argv) > MAX_ARGUMENTS
        or argv[0] != f"capsule-tool:{tool}"
        or any(
            not isinstance(argument, str) or "\x00" in argument or len(argument.encode("utf-8")) > MAX_ARGUMENT_BYTES
            for argument in argv
        )
    ):
        raise ToolRequestError("tool request payload differs from its fixed plan")


def _validate_request_environment(environment: object) -> None:
    if not isinstance(environment, dict) or not all(
        isinstance(name, str) and isinstance(item, str) and name in SAFE_ENVIRONMENT
        for name, item in environment.items()
    ):
        raise ToolRequestError("tool request payload differs from its fixed plan")


def _request(project: Path, tool: str) -> dict[str, object]:
    path = project / REQUEST_NAME
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REQUEST_BYTES:
        raise ToolRequestError("tool request must be a bounded regular file")
    if path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise ToolRequestError("tool request must be immutable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolRequestError("tool request is not UTF-8 JSON") from exc
    fields = {
        "argv",
        "capture_output",
        "cwd",
        "environment",
        "member",
        "schema",
        "sequence",
        "text",
        "timeout_ms",
        "tool",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ToolRequestError("tool request fields differ from schema v1")
    request = cast(dict[str, object], value)
    argv = request["argv"]
    environment = request["environment"]
    _validate_request_plan(request, tool)
    _validate_request_arguments(argv, tool)
    _validate_request_environment(environment)
    return request


def _relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ToolRequestError("logical tool path escapes its root")
    return path


def _project_path(root: Path, relative: PurePosixPath) -> str:
    candidate = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ToolRequestError("logical tool path contains a symlink")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ToolRequestError("logical tool path escapes its root")
    return str(candidate)


def _materialize(value: str, *, capsule: Path, project: Path, temporary: Path) -> str:
    roots = {"capsule": capsule, "project": project, "temporary": temporary}
    for label, root in roots.items():
        if value == label:
            return str(root)
        prefix = f"{label}/"
        if value.startswith(prefix):
            return _project_path(root, _relative(value.removeprefix(prefix)))
    snapshot = "/opt/specfact/snapshot"
    if value == snapshot:
        return str(project)
    if value.startswith(snapshot + "/"):
        return _project_path(project, _relative(value.removeprefix(snapshot + "/")))
    config = "/opt/specfact/config/"
    if value.startswith(config):
        return _project_path(project / ".specfact-native-config", _relative(value.removeprefix(config)))
    project_runtime = "/opt/specfact/project-runtime"
    if value == project_runtime:
        return str(project / ".specfact-project-runtime")
    if value.startswith(project_runtime + "/"):
        return _project_path(
            project / ".specfact-project-runtime",
            _relative(value.removeprefix(project_runtime + "/")),
        )
    if value.startswith("/"):
        raise ToolRequestError("tool request contains an absolute host path")
    return value


def _environment(raw: object, *, capsule: Path, project: Path, temporary: Path) -> dict[str, str]:
    values = cast(Mapping[str, str], raw)
    state_roots = {
        "HOME": temporary / "home",
        "XDG_CACHE_HOME": temporary / "cache",
        "XDG_CONFIG_HOME": temporary / "config",
        "RUFF_CACHE_DIR": temporary / "ruff-cache",
        "TMPDIR": temporary / "tmp",
    }
    for path in state_roots.values():
        path.mkdir(mode=0o700, exist_ok=True)
        if path.is_symlink() or path.resolve() != path or not path.is_dir() or path.stat().st_mode & 0o077:
            raise ToolRequestError("private tool state root is invalid")
    result = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "TZ": "UTC",
        **{name: str(path) for name, path in state_roots.items()},
    }
    for name, value in values.items():
        result[name] = _materialize(value, capsule=capsule, project=project, temporary=temporary)
    result.update({name: str(path) for name, path in state_roots.items()})
    return result


def _mapped_arguments(request: Mapping[str, object], *, capsule: Path, project: Path, temporary: Path) -> list[str]:
    argv = cast(list[str], request["argv"])

    def materialize_argument(argument: str) -> str:
        for prefix in ("--cov-report=json:", "--junitxml=", "cache_dir="):
            if argument.startswith(prefix):
                logical_path = argument.removeprefix(prefix)
                if not logical_path.startswith("temporary/"):
                    raise ToolRequestError("pytest evidence path differs from its fixed temporary plan")
                return prefix + _materialize(
                    logical_path,
                    capsule=capsule,
                    project=project,
                    temporary=temporary,
                )
        return _materialize(argument, capsule=capsule, project=project, temporary=temporary)

    return [
        argv[0],
        *(materialize_argument(argument) for argument in argv[1:]),
    ]


@dataclass(frozen=True)
class _ToolCommandContext:
    capsule: Path
    project: Path
    temporary: Path
    sequence: int


def _semgrep_rules(config_arguments, context: _ToolCommandContext) -> list[object]:
    capsule, project = context.capsule, context.project
    rules: list[object] = []
    for raw in config_arguments[1::2]:
        config = Path(raw)
        if (
            config.is_symlink()
            or not config.is_file()
            or config.resolve(strict=True) != config
            or not (config.is_relative_to(project / ".specfact-native-config") or config.is_relative_to(capsule))
            or config.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise ToolRequestError("Semgrep rule pack is outside immutable admitted configuration")
        document = yaml.safe_load(config.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or set(document) != {"rules"} or not isinstance(document["rules"], list):
            raise ToolRequestError("Semgrep rule pack shape is invalid")
        rules.extend(document["rules"])
    if not rules:
        raise ToolRequestError("Semgrep rule pack is empty")

    return rules


def _semgrep_targets(source_arguments, project: Path) -> list[object]:
    targets: list[object] = []
    for raw in source_arguments:
        source = Path(raw)
        if (
            source.is_symlink()
            or not source.is_file()
            or source.resolve(strict=True) != source
            or not source.is_relative_to(project)
            or source.suffix not in {".py", ".pyi"}
            or source.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise ToolRequestError("Semgrep target is outside immutable admitted Python inputs")
        relative = source.relative_to(project).as_posix()
        targets.append(
            [
                "CodeTarget",
                {
                    "analyzer": "python",
                    "path": {"fpath": str(source), "ppath": f"/{relative}"},
                    "products": ["sast"],
                },
            ]
        )

    return targets


def _semgrep_core_command(
    arguments: list[str],
    *,
    context: _ToolCommandContext,
    target: Path,
) -> list[str]:
    if arguments[1:4] != ["--disable-version-check", "--quiet", "--disable-nosem"]:
        raise ToolRequestError("Semgrep launch flags differ from the fixed direct-core plan")
    try:
        json_index = arguments.index("--json", 4)
    except ValueError as exc:
        raise ToolRequestError("Semgrep launch lacks its JSON result contract") from exc
    config_arguments = arguments[4:json_index]
    source_arguments = arguments[json_index + 1 :]
    if (
        not config_arguments
        or len(config_arguments) % 2
        or any(flag != "--config" for flag in config_arguments[::2])
        or not source_arguments
    ):
        raise ToolRequestError("Semgrep launch inputs differ from the fixed direct-core plan")

    rules = _semgrep_rules(config_arguments, context)
    targets = _semgrep_targets(source_arguments, context.project)
    temporary, sequence = context.temporary, context.sequence
    input_root = temporary / f"semgrep-core-{sequence:03d}"
    input_root.mkdir(mode=0o700)
    rules_path = input_root / "rules.json"
    targets_path = input_root / "targets.json"
    rules_path.write_text(json.dumps({"rules": rules}, separators=(",", ":")) + "\n", encoding="utf-8")
    targets_path.write_text(json.dumps(["Targets", targets], separators=(",", ":")) + "\n", encoding="utf-8")
    rules_path.chmod(0o600)
    targets_path.chmod(0o600)
    return [str(target), "-json_nodots", "-j", "1", "-rules", str(rules_path), "-targets", str(targets_path)]


def _direct_command(
    tool: str,
    arguments: list[str],
    context: _ToolCommandContext,
) -> tuple[Path, list[str]]:
    capsule = context.capsule
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    site = capsule / f"python/lib/python{version}/site-packages"
    if tool == "ruff":
        target = capsule / "tools/ruff"
        return target, [str(target), *arguments[1:]]
    if tool == "basedpyright":
        target = capsule / "tools/node"
        return (
            target,
            [
                str(target),
                "--jitless",
                "--unhandled-rejections=warn",
                "--require",
                str(site / "node_guard.cjs"),
                str(capsule / "python/node/basedpyright/index.js"),
                *arguments[1:],
            ],
        )
    target = capsule / "tools/semgrep-core"
    return target, _semgrep_core_command(
        arguments,
        context=context,
        target=target,
    )


def _bind_semgrep_ca_bundle(capsule: Path, environment: dict[str, str]) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    bundle = capsule / f"python/lib/python{version}/site-packages/certifi/cacert.pem"
    if (
        bundle.is_symlink()
        or not bundle.is_file()
        or bundle.resolve(strict=True) != bundle
        or not bundle.is_relative_to(capsule)
        or bundle.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise ToolRequestError("verified Semgrep CA bundle is missing or mutable")
    environment["SSL_CERT_FILE"] = str(bundle)


def _exit_code(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, IntEnum):
        value = int(value)
    if type(value) is int and 0 <= value <= 255:
        return value
    raise ToolRequestError("Python tool returned an invalid exit code")


def _project_source_declarations(descriptor: Path) -> list[str]:
    if (
        descriptor.is_symlink()
        or not descriptor.is_file()
        or descriptor.stat().st_size > MAX_REQUEST_BYTES
        or descriptor.stat().st_mode & 0o222
    ):
        raise ToolRequestError("project runtime descriptor is mutable or invalid")
    document = json.loads(descriptor.read_text(encoding="utf-8"))
    inventory = document.get("inventory", {}) if isinstance(document, dict) else None
    roots = inventory.get("source_roots", []) if isinstance(inventory, dict) else None
    if not isinstance(roots, list) or len(roots) > MAX_ARGUMENTS or any(not isinstance(root, str) for root in roots):
        raise ToolRequestError("project source roots are invalid")
    return roots


def _project_source_roots(project: Path, runtime: Path) -> list[str]:
    descriptor = runtime / "project-runtime.json"
    if not descriptor.exists():
        return []
    roots = _project_source_declarations(descriptor)
    source_roots: list[str] = []
    for value in roots:
        root = Path(_project_path(project, _relative(value)))
        if not root.is_dir() or root.stat().st_mode & 0o222:
            raise ToolRequestError("project source root is mutable or invalid")
        source_roots.append(str(root))
    return source_roots


def _activate_project_runtime(project: Path) -> None:
    """Append immutable customer imports after the sealed capsule tool paths."""
    runtime = project / ".specfact-project-runtime"
    if not runtime.exists():
        sys.path.append(str(project))
        return
    site_packages = runtime / "site-packages"
    for path, label in ((runtime, "project runtime"), (site_packages, "project site-packages")):
        if path.is_symlink() or not path.is_dir() or path.resolve() != path:
            raise ToolRequestError(f"{label} is invalid")
        if path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise ToolRequestError(f"{label} is writable")
    source_roots = _project_source_roots(project, runtime)
    sys.path.extend((str(project), *source_roots, str(site_packages)))


def _project_pytest_plugins(project: Path) -> dict[str, tuple[object, object]]:
    """Load selected environment plugins only after worker confinement."""
    from specfact_code_review.run.native_pytest_plugins import ProjectPytestPluginError, project_pytest_plugins

    try:
        return project_pytest_plugins(project)
    except ProjectPytestPluginError as exc:
        raise ToolRequestError(str(exc)) from exc


def _run_python_tool(tool: str, arguments: list[str], project: Path) -> int:
    os.chdir(project)
    if tool == "pytest":
        # Automatic xdist counts must fit the unchanged owned-worker budget.
        os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"] = "4"
        try:
            command_index = arguments.index("-c")
        except ValueError as exc:
            raise ToolRequestError("pytest plan lacks its trusted observer") from exc
        if command_index + 1 >= len(arguments) or command_index not in {1, 3}:
            raise ToolRequestError("pytest observer position differs from its fixed plan")
        source = arguments[command_index + 1]
        sys.argv = ["-c", *arguments[command_index + 2 :]]
        plugins = _project_pytest_plugins(project)
        namespace = {
            "__name__": "__main__",
            "__file__": "<specfact-native-pytest-observer>",
            "__specfact_project_pytest_plugins__": plugins,
        }
        from specfact_code_review.run.native_pytest_plugins import installed_rerunfailures

        temporary = Path(os.environ["TMPDIR"]).parent if os.environ.get("TMPDIR") else None
        try:
            with installed_rerunfailures(plugins, temporary):
                exec(compile(source, "<specfact-native-pytest-observer>", "exec"), namespace)
        except SystemExit as exc:
            return _exit_code(exc.code)
        return 0
    module_name, attribute = {
        "crosshair": ("crosshair.main", "main"),
        "pylint": ("pylint", "run_pylint"),
        "radon": ("radon", "main"),
    }[tool]
    sys.argv = [tool, *arguments[1:]]
    try:
        return _exit_code(getattr(importlib.import_module(module_name), attribute)())
    except SystemExit as exc:
        return _exit_code(exc.code)


def _cached_analyzer_dependency(module, original_site, stdlib, admitted) -> bool:
    filename = getattr(module, "__file__", None)
    locations = list(getattr(module, "__path__", ()))
    if filename:
        locations.append(filename)
    cached_site = any(Path(location).resolve().is_relative_to(original_site) for location in locations)
    nonstdlib = filename and not any(Path(filename).resolve().is_relative_to(root.resolve()) for root in stdlib)
    return bool(cached_site or (nonstdlib and not admitted))


def _purge_analyzer_dependencies(original_site, finder, stdlib_paths) -> None:
    stdlib = tuple(Path(path) for path in stdlib_paths)
    for fullname, module in tuple(sys.modules.items()):
        top_level = fullname.partition(".")[0]
        if top_level == "specfact_code_review" or fullname == "__main__":
            continue
        if _cached_analyzer_dependency(module, original_site, stdlib, top_level in finder.names):
            sys.modules.pop(fullname, None)


@beartype
@require(lambda project: project.is_dir())
def activate_project_domain(project: Path, capsule: Path, tool: str) -> None:
    """Pin one analyzer graph without exposing unrelated capsule dependencies."""
    from specfact_code_review.run.target_bootstrap import ImportPathFinder, RestrictedDomainFinder, _stdlib_paths

    _activate_project_runtime(project)
    descriptor = project / ".specfact-project-runtime/project-runtime.json"
    if not descriptor.exists():
        raise ToolRequestError("project_native_dependency_graph_missing:prepare the project environment")
    document = json.loads(descriptor.read_text(encoding="utf-8"))
    inventory = document.get("inventory", {}) if isinstance(document, dict) else {}
    domain = "pytest-observe" if tool == "pytest" else tool
    graph = inventory.get("member_graphs", {}).get(domain) if isinstance(inventory, dict) else None
    if not isinstance(graph, dict) or not isinstance(graph.get("sealed_imports"), list):
        raise ToolRequestError(f"project_native_dependency_graph_missing:{domain}:prepare the project environment")
    from specfact_code_review.run.native_analyzer_view import VIEW_NAME

    original_site = capsule / f"python/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    sealed = project / VIEW_NAME
    if not sealed.is_dir() or sealed.is_symlink() or sealed.resolve() != sealed:
        raise ToolRequestError("project_native_analyzer_root_invalid")
    runtime = project / ".specfact-project-runtime"
    finder = RestrictedDomainFinder(graph, analyzer_root=sealed, project_site=runtime / "site-packages")
    stdlib_paths = _stdlib_paths()
    # A worker starts with trusted control imports already cached. Remove other
    # site modules before project imports so those objects cannot substitute
    # for the versions recorded in the selected environment.
    _purge_analyzer_dependencies(original_site, finder, stdlib_paths)
    source_roots = inventory.get("source_roots", [])
    sys.path[:] = [
        # Astroid maps plugin files to module names using the first matching
        # path. This location precedes its stdlib ancestor; the finder still
        # resolves non-owned dependencies from project/stdlib paths first.
        str(sealed),
        *stdlib_paths,
        str(project),
        *(str(project / root) for root in source_roots),
        str(runtime / "site-packages"),
    ]
    sys.meta_path[:] = [
        finder,
        importlib.machinery.BuiltinImporter,
        importlib.machinery.FrozenImporter,
        ImportPathFinder,
    ]
    finder.validate_loaded()


def _execute_tool(capsule: Path, project: Path, output: Path, temporary: Path, tool: str) -> int:
    request = _request(project, tool)
    arguments = _mapped_arguments(request, capsule=capsule, project=project, temporary=temporary)
    environment = _environment(request["environment"], capsule=capsule, project=project, temporary=temporary)
    os.environ.clear()
    os.environ.update(environment)
    os.chdir(project)
    if tool in DIRECT_TOOLS:
        target, command = _direct_command(
            tool,
            arguments,
            _ToolCommandContext(capsule, project, temporary, cast(int, request["sequence"])),
        )
        if tool == "semgrep":
            _bind_semgrep_ca_bundle(capsule, environment)
        if target.is_symlink() or not target.is_file():
            raise ToolRequestError("fixed native tool image is missing")
        os.execve(target, command, environment)
        raise AssertionError("execve returned")
    # Radon parses source without importing customer modules; keep it
    # entirely in the sealed analyzer domain, as on Linux.
    if tool != "radon":
        from specfact_code_review.run.native_managed_process import installed_subprocess

        activate_project_domain(project, capsule, tool)
        with installed_subprocess(capsule, project, output, temporary):
            return _run_python_tool(tool, arguments, project)
    return _run_python_tool(tool, arguments, project)


def _reject_tool_request(detail: object) -> int:
    sys.stderr.write(f"specfact native tool request rejected: {detail}\n")
    return 76


def _admitted_tool() -> int:
    try:
        return _execute_tool(*_roots())
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _reject_tool_request(exc)


def main() -> int:
    """Execute the one broker-fixed tool plan."""

    cwd_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        caller_cwd = os.open(".", cwd_flags)
    except OSError as exc:
        return _reject_tool_request(f"cannot retain caller cwd: {exc}")
    caller_environment = dict(os.environ)
    caller_path = list(sys.path)
    caller_argv = list(sys.argv)
    try:
        return _admitted_tool()
    finally:
        os.environ.clear()
        os.environ.update(caller_environment)
        sys.path[:] = caller_path
        sys.argv = caller_argv
        try:
            os.fchdir(caller_cwd)
        finally:
            os.close(caller_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
