"""Fixed startup for broker-owned Python children; never creates a process."""

from __future__ import annotations

import io
import os
import plistlib
import runpy
import site
import struct
import sys
import warnings
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType

from specfact_code_review.run.native_managed_process import (
    MAX_PAYLOAD,
    ManagedProcessError,
    installed_subprocess,
    python_launch_isolated,
)
from specfact_code_review.run.native_pytest_plugins import installed_child_pytest_plugins


def _read(length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = os.read(3, length - len(data))
        if not chunk:
            raise ManagedProcessError("child startup channel closed")
        data.extend(chunk)
    return bytes(data)


def _warning_filter(arguments: list[str]) -> list[str]:
    if arguments[0] == "-W":
        if len(arguments) < 2:
            raise ManagedProcessError("Python warning filter is missing")
        value, remaining = arguments[1], arguments[2:]
    else:
        value, remaining = arguments[0][2:], arguments[1:]
    try:
        warnings._setoption(value)
    except warnings._OptionError as exc:
        raise ManagedProcessError("Python warning filter is invalid") from exc
    return remaining


def _unbuffered_output() -> None:
    for name, descriptor in (("stdout", 1), ("stderr", 2)):
        current = getattr(sys, name)
        current.flush()
        raw = os.fdopen(descriptor, "wb", buffering=0, closefd=False)
        setattr(sys, name, io.TextIOWrapper(raw, encoding=current.encoding, errors=current.errors, write_through=True))


def _startup_arguments(arguments: list[str]) -> list[str]:
    while arguments and (arguments[0] in {"-u", "-B", "-W", "-I"} or arguments[0].startswith("-W")):
        if arguments[0].startswith("-W"):
            arguments = _warning_filter(arguments)
            continue
        if arguments[0] == "-u":
            _unbuffered_output()
        arguments = arguments[1:]
    if not arguments:
        raise ManagedProcessError("interactive Python is unsupported")
    return arguments


def _script_arguments(arguments: list[str]) -> list[str]:
    script = arguments[1:] if arguments[0] == "--" else arguments
    if not script:
        raise ManagedProcessError("Python script is missing")
    return script


def _execution_directory(arguments: list[str], allowed_roots: tuple[Path, ...] | None) -> None:
    directory = (
        Path.cwd() if arguments[0] in {"-c", "-m", "-"} else Path(_script_arguments(arguments)[0]).resolve().parent
    )
    if allowed_roots is not None and not any(directory.is_relative_to(root) for root in allowed_roots):
        raise ManagedProcessError("Python execution directory exceeds inherited grants")
    sys.path.insert(0, str(directory))


def _run_command(arguments: list[str]) -> None:
    selector = arguments[0]
    if selector != "-" and len(arguments) < 2:
        raise ManagedProcessError("Python launch value is missing")
    sys.argv[:] = arguments if selector == "-" else [selector if selector == "-c" else arguments[1], *arguments[2:]]
    if selector == "-m":
        runpy.run_module(arguments[1], run_name="__main__", alter_sys=True)
        return
    main_module = ModuleType("__main__")
    main_module.__dict__.update(__package__=None, __builtins__=__builtins__)
    sys.modules["__main__"] = main_module
    code = sys.stdin.read() if selector == "-" else arguments[1]
    exec(compile(code, "<stdin>" if selector == "-" else "<managed-python>", "exec"), main_module.__dict__)


def _dispatch(arguments: list[str], *, allowed_roots: tuple[Path, ...] | None = None) -> int:
    """Support reviewed Python launch forms, with no shell or startup injection."""
    isolated = python_launch_isolated(arguments)
    arguments = _startup_arguments(arguments)
    if not isolated:
        _execution_directory(arguments, allowed_roots)
    selector = arguments[0]
    if selector in {"-c", "-m", "-"}:
        _run_command(arguments)
    elif selector == "--" or not selector.startswith("-"):
        script = _script_arguments(arguments)
        sys.argv[:] = script
        runpy.run_path(script[0], run_name="__main__")
    else:
        raise ManagedProcessError("Python startup option is unsupported")
    return 0


def _startup_request() -> tuple[int, dict]:
    try:
        parent_plan, length = struct.unpack("<II", _read(8))
        if not 0 < length <= MAX_PAYLOAD:
            raise ManagedProcessError("child startup request exceeds bounds")
        request = plistlib.loads(_read(length))
    finally:
        # Project code never receives this startup/configuration descriptor.
        os.close(3)
    if not isinstance(request, dict) or request.get("program") != "python":
        raise ManagedProcessError("child program is not admitted")
    return parent_plan, request


def _child_cwd(raw: str, roots: dict[str, Path]) -> Path:
    label, _, suffix = raw.partition("/")
    cwd = roots[label] / suffix
    if cwd.resolve() != cwd or not cwd.is_dir() or not cwd.is_relative_to(roots[label]):
        raise ManagedProcessError("child cwd differs from inherited grants")
    return cwd


def _child_paths(request: dict, roots: dict[str, Path]) -> list[str]:
    paths = request["python_paths"]
    if any(not any(Path(path).resolve().is_relative_to(root) for root in roots.values()) for path in paths):
        raise ManagedProcessError("child Python paths exceed inherited grants")
    return paths


def _child_prefix(prefix: str, roots: dict[str, Path]) -> None:
    if prefix:
        prefix_path = Path(prefix)
        if prefix_path.resolve() != prefix_path or not any(prefix_path.is_relative_to(root) for root in roots.values()):
            raise ManagedProcessError("child Python prefix exceeds inherited grants")


def _isolated_child_paths(paths: list[str], prefix: str, isolated: bool) -> list[str]:
    if not isolated:
        return paths
    private_site = (
        Path(prefix) / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages" if prefix else None
    )
    return [str(private_site)] if private_site is not None and private_site.is_dir() else []


def _cached_project_dependencies() -> set[str]:
    return {
        name
        for name, module in tuple(sys.modules.items())
        if name != "__main__"
        and not name.startswith("specfact_code_review")
        and (
            "site-packages" in str(getattr(module, "__file__", ""))
            or any("site-packages" in str(path) for path in getattr(module, "__path__", ()))
        )
    }


def _execute_child(request: dict, parent_plan: int, roots: dict[str, Path]) -> int:
    environment = request["environment"]
    isolated = python_launch_isolated(request["argv"])
    try:
        if environment.get("PYTHONPATH") and not isolated:
            site.execsitecustomize()
        compatibility = (
            installed_child_pytest_plugins(roots["project"], temporary=roots["temporary"])
            if parent_plan in {18, 27} and environment.get("PYTEST_VERSION") and not isolated
            else nullcontext()
        )
        with compatibility:
            return _dispatch(request["argv"], allowed_roots=tuple(roots.values()))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1


def main() -> int:
    if len(sys.argv) != 5:
        return 76
    capsule, project, output, temporary = (Path(path) for path in sys.argv[1:])
    parent_plan, request = _startup_request()
    roots = {"project": project, "output": output, "temporary": temporary}
    cwd = _child_cwd(request["cwd"], roots)
    paths = _child_paths(request, roots)
    environment = request["environment"]
    os.environ.update(HOME=str(temporary), TMPDIR=str(temporary), XDG_CACHE_HOME=str(temporary))
    os.environ.update(environment)
    _child_prefix(request["python_prefix"], roots)
    from specfact_code_review.run.native_python_environment import activate

    activate(capsule, prefix=request["python_prefix"], alias=request["python_alias"])
    paths = _isolated_child_paths(paths, request["python_prefix"], python_launch_isolated(request["argv"]))
    if environment.get("PYTHONUTF8") == "1":
        for stream in (sys.stdin, sys.stdout, sys.stderr):
            stream.reconfigure(encoding="utf-8")
    os.chdir(cwd)
    stdlib = [path for path in sys.path if path and "site-packages" not in path]
    excluded = _cached_project_dependencies()
    sys.path[:] = [*paths, *stdlib]
    with installed_subprocess(capsule, project, output, temporary):
        for name in excluded:
            sys.modules.pop(name, None)
        return _execute_child(request, parent_plan, roots)


if __name__ == "__main__":
    raise SystemExit(main())
