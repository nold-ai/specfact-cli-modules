"""PEP 517 hooks in the network-denied, broker-owned project domain."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import require

from specfact_code_review.run import native_project_hatch, native_project_poetry
from specfact_code_review.run.native_project_pip import validate_requirement
from specfact_code_review.run.runtime_models import ProjectRuntimeError


@beartype
@require(lambda root: root.is_dir())
def build_configuration(root: Path) -> dict[str, Any]:
    """Read declarations without importing any backend or customer module."""
    path = root / "pyproject.toml"
    metadata = tomllib.loads(path.read_text()) if path.is_file() else {}
    build = metadata.get(
        "build-system", {"requires": ["setuptools>=40.8"], "build-backend": "setuptools.build_meta:__legacy__"}
    )
    if not isinstance(build, dict):
        raise ProjectRuntimeError("project_native_build_configuration_invalid")
    requirements, backend, paths = (
        build.get("requires"),
        build.get("build-backend", "setuptools.build_meta:__legacy__"),
        build.get("backend-path", []),
    )
    if not isinstance(requirements, list) or not isinstance(backend, str) or not isinstance(paths, list):
        raise ProjectRuntimeError("project_native_build_configuration_invalid")
    for value in requirements:
        if not isinstance(value, str):
            raise ProjectRuntimeError("project_native_build_configuration_invalid")
        validate_requirement(value)
    for value in paths:
        if not isinstance(value, str) or not (root / value).resolve().is_relative_to(root.resolve()):
            raise ProjectRuntimeError("project_native_backend_path_escape")
    return {"requires": requirements, "build-backend": backend, "backend-path": paths}


@beartype
def execute_hook(
    project: Path, output: Path, temporary: Path, dependencies: Path, *, operation: str, project_subdirectory: str = ""
) -> dict[str, Any]:
    """Execute inside an already confined worker; this is not a host adapter."""
    source = temporary / "source"
    shutil.copytree(
        project, source, ignore=shutil.ignore_patterns(".specfact-build-dependencies", ".specfact-hook.json")
    )
    for directory, _children, files in os.walk(source):
        Path(directory).chmod(0o700)
        for name in files:
            path = Path(directory) / name
            path.chmod(0o700 if path.stat().st_mode & 0o111 else 0o600)
    if project_subdirectory:
        selected = source / project_subdirectory
        if (
            len(project_subdirectory.encode()) > 4096
            or Path(project_subdirectory).is_absolute()
            or any(part in {"", ".", ".."} for part in project_subdirectory.split("/"))
            or selected.resolve() != selected
            or not selected.is_relative_to(source)
            or not selected.is_dir()
        ):
            raise ProjectRuntimeError("project_native_build_subdirectory_invalid")
        source = selected
    manager_operation = operation in {"hatch.describe", "hatch.install", "poetry.describe", "poetry.install"}
    configuration = {"backend-path": []} if manager_operation else build_configuration(source)
    original_path, original_directory = list(sys.path), Path.cwd()
    # Backend dependencies precede the stdlib; sealed analyzer packages are not a build environment.
    stdlib = [value for value in sys.path if "site-packages" not in value and value not in {"", str(project)}]
    sys.path[:] = [*(str(source / value) for value in configuration["backend-path"]), str(dependencies), *stdlib]
    name, _separator, attribute = ("", "", "") if manager_operation else configuration["build-backend"].partition(":")
    # Removing import paths alone leaves already imported analyzer packages visible.
    # Production workers exit after one hook; restore modules for focused fixtures.
    excluded = {
        key: value
        for key, value in list(sys.modules.items())
        if key != "__main__"
        and (
            "site-packages" in str(getattr(value, "__file__", ""))
            or any("site-packages" in str(path) for path in getattr(value, "__path__", ()))
        )
    }
    for key in excluded:
        sys.modules.pop(key, None)
    try:
        os.chdir(source)
        if manager_operation:
            capsule = Path(sys.base_prefix).parent
            if operation.startswith("hatch."):
                return native_project_hatch.execute(
                    source, output, temporary, capsule, operation=operation, input_project=project
                )
            return native_project_poetry.execute(source, output, temporary, capsule, operation=operation)
        backend = importlib.import_module(name)
        if configuration["backend-path"]:
            origin = backend.__file__
            if not isinstance(origin, str):
                raise ProjectRuntimeError("project_native_backend_path_escape")
            location = Path(origin).resolve()
            if not any(location.is_relative_to((source / value).resolve()) for value in configuration["backend-path"]):
                raise ProjectRuntimeError("project_native_backend_path_escape")
        for segment in attribute.split(".") if attribute else ():
            backend = getattr(backend, segment)
        if operation in {"requirements", "editable-requirements"}:
            hook = getattr(
                backend,
                "get_requires_for_build_editable"
                if operation == "editable-requirements"
                else "get_requires_for_build_wheel",
                None,
            )
            values = hook(config_settings=None) if hook else []
            if (
                not isinstance(values, list)
                or len(values) > 4096
                or any(not isinstance(value, str) for value in values)
            ):
                raise ProjectRuntimeError("project_native_build_requirements_invalid")
            return {"requirements": [validate_requirement(value) for value in values]}
        if operation != "wheel":
            raise ProjectRuntimeError("project_native_build_operation_invalid")
        wheels = output / "wheels"
        wheels.mkdir(mode=0o700)
        filename = backend.build_wheel(str(wheels), config_settings=None, metadata_directory=None)
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".whl"):
            raise ProjectRuntimeError("project_native_build_wheel_invalid")
        if not (wheels / filename).is_file() or (wheels / filename).is_symlink():
            raise ProjectRuntimeError("project_native_build_wheel_invalid")
        return {"wheel": filename}
    finally:
        os.chdir(original_directory)
        sys.path[:] = original_path
        # Each production invocation exits. Keep focused in-process fixtures independent too.
        sys.modules.pop(name, None)
        for key in excluded:
            sys.modules.pop(key, None)
        sys.modules.update(excluded)


@beartype
def main() -> int:
    """Read only the broker-fixed hook request and return untrusted project output."""
    if len(sys.argv) != 5:
        return 76
    project, output, temporary = (Path(sys.argv[index]) for index in (2, 3, 4))
    from specfact_code_review.run.native_python_environment import activate

    activate(Path(sys.argv[1]))
    os.environ.update(HOME=str(temporary), TMPDIR=str(temporary), XDG_CACHE_HOME=str(temporary))
    try:
        request_path = project / ".specfact-hook.json"
        if request_path.is_symlink() or not 0 < request_path.stat().st_size <= 1 << 20:
            raise ProjectRuntimeError("project_native_build_request_invalid")
        request = json.loads(request_path.read_text())
        if (
            not isinstance(request, dict)
            or set(request) not in ({"operation", "extras"}, {"operation", "extras", "project_subdirectory"})
            or not isinstance(request.get("project_subdirectory", ""), str)
        ):
            raise ProjectRuntimeError("project_native_build_request_invalid")
        from specfact_code_review.run.native_managed_process import installed_subprocess

        with installed_subprocess(Path(sys.argv[1]), project, output, temporary):
            result = execute_hook(
                project,
                output,
                temporary,
                project / ".specfact-build-dependencies/site-packages",
                operation=request["operation"],
                project_subdirectory=request.get("project_subdirectory", ""),
            )
        (output / "hook-result.json").write_text(json.dumps(result) + "\n")
        return 0
    except SystemExit as exc:
        code = 0 if exc.code is None else exc.code if type(exc.code) is int and 0 <= exc.code <= 255 else None
        diagnostic = "project_native_build_hook_exit:" + (str(code) if code is not None else "non_integer")
        (output / "preparation-error.json").write_text(
            json.dumps({"diagnostic": diagnostic, "exit_code": code, "origin": "project"}) + "\n"
        )
        return 74
    except (ImportError, OSError, ValueError, TypeError, AttributeError) as exc:
        (output / "preparation-error.json").write_text(json.dumps({"diagnostic": str(exc)}) + "\n")
        return 74


if __name__ == "__main__":
    raise SystemExit(main())
