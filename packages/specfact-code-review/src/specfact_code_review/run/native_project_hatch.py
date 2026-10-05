"""Authentic pinned Hatch in the already confined project preparation worker."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import require
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from specfact_code_review.run.native_project_pip import environment_inventory, validate_requirement
from specfact_code_review.run.runtime_models import ProjectRuntimeError


VERSION = "1.18.0"
SCHEMA = "native-hatch-request-v1"
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


@beartype
@require(lambda project: project.is_dir())
def read_request(project: Path) -> dict[str, Any]:
    path = project / ".specfact-hatch.json"
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 1 << 20:
        raise ProjectRuntimeError("project_native_hatch_request_invalid")
    request = json.loads(path.read_text())
    if (
        not isinstance(request, dict)
        or set(request) != {"schema", "environment", "groups", "extras"}
        or request.get("schema") != SCHEMA
        or not isinstance(request.get("environment"), str)
        or not _NAME.fullmatch(request["environment"])
        or any(
            not isinstance(request.get(key), list)
            or len(request[key]) > 128
            or any(not isinstance(value, str) or not _NAME.fullmatch(value) for value in request[key])
            for key in ("groups", "extras")
        )
    ):
        raise ProjectRuntimeError("project_native_hatch_request_invalid")
    return request


@beartype
def environment_name(project: Any, requested: str) -> str:
    """Resolve a matrix root from Hatch's configurations for the admitted ABI."""
    matrix = project.config.internal_matrices.get(requested) or project.config.matrices.get(requested)
    if matrix is None:
        return requested
    abi = ".".join(map(str, sys.version_info[:2]))
    candidates = [name for name, values in matrix["envs"].items() if values.get("python", abi) == abi]
    if len(candidates) != 1:
        raise ProjectRuntimeError(f"project_native_hatch_matrix_selection_required:{requested}:{abi}")
    return candidates[0]


def _environment(project: Path, temporary: Path, request: dict[str, Any]) -> Any:
    from hatch._version import __version__
    from hatch.cli.application import Application
    from hatch.config.user import RootConfig
    from hatch.project.core import Project
    from hatch.utils.fs import Path as HatchPath

    if __version__ != VERSION:
        raise ProjectRuntimeError(f"project_native_manager_version_mismatch:hatch:{__version__}")
    app = Application(sys.exit, verbosity=-1, enable_color=False, interactive=False)
    app.config_file.model = RootConfig({})
    app.data_dir, app.cache_dir = HatchPath(temporary / "hatch-data"), HatchPath(temporary / "hatch-cache")
    app.env, app.env_active = request["environment"], False
    app.project = Project(HatchPath(project))
    app.project.set_app(app)
    app.env = environment_name(app.project, request["environment"])
    environment = app.project.get_environment(app.env)
    for key, setting in (("extras", "features"), ("groups", "dependency-groups")):
        if request[key]:
            environment.config[setting] = request[key]
    return environment


def acquisition_requirements(environment: Any, project: Path) -> list[str]:
    """Keep Hatch's exact root reference in the build domain, not acquisition."""
    dependencies = environment.all_dependencies
    if len(dependencies) > 4096:
        raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")
    root_name = canonicalize_name(environment.metadata.name)
    local_sources = {project.as_uri(): root_name}
    for member in workspace_projects(environment, project):
        local_sources[(project / member["path"]).as_uri()] = canonicalize_name(member["name"])
    result = []
    for value in dependencies:
        requirement = Requirement(value)
        if requirement.url in local_sources and canonicalize_name(requirement.name) == local_sources[requirement.url]:
            continue
        result.append(validate_requirement(value))
    return result


@beartype
def validate_workspace(project: Path, values: Any) -> list[dict[str, Any]]:
    """Accept only bounded local project descriptions inside the snapshot."""
    if not isinstance(values, list) or len(values) > 128:
        raise ProjectRuntimeError("project_native_hatch_workspace_invalid")
    seen = set()
    for value in values:
        if (
            not isinstance(value, dict)
            or set(value) != {"name", "path", "extras"}
            or not isinstance(value["name"], str)
            or not _NAME.fullmatch(value["name"])
            or not isinstance(value["path"], str)
            or not value["path"]
            or Path(value["path"]).is_absolute()
            or any(part in {".", ".."} for part in value["path"].split("/"))
            or not isinstance(value["extras"], list)
            or len(value["extras"]) > 128
            or any(not isinstance(item, str) or not _NAME.fullmatch(item) for item in value["extras"])
        ):
            raise ProjectRuntimeError("project_native_hatch_workspace_invalid")
        path = project / value["path"]
        if (
            path.resolve() != path
            or not path.is_relative_to(project)
            or not (path / "pyproject.toml").is_file()
            or (path / "pyproject.toml").is_symlink()
            or canonicalize_name(value["name"]) in seen
        ):
            raise ProjectRuntimeError("project_native_hatch_workspace_invalid")
        seen.add(canonicalize_name(value["name"]))
    return values


def workspace_projects(environment: Any, project: Path) -> list[dict[str, Any]]:
    workspace = getattr(environment, "workspace", None)
    values = []
    for member in workspace.members if workspace is not None else ():
        path = Path(member.project.location)
        if not path.is_relative_to(project):
            raise ProjectRuntimeError("project_native_hatch_workspace_invalid")
        values.append(
            {"name": member.name, "path": path.relative_to(project).as_posix(), "extras": list(member.features)}
        )
    return validate_workspace(project, values)


def configure_installer(environment: Any, project: Path, temporary: Path, capsule: Path) -> None:
    """Bind Hatch's selected uv installer to the packaged image and private inputs."""
    if not environment.use_uv:
        return
    tool = capsule / "tools/uv"
    if tool.resolve() != tool or tool.is_symlink() or not tool.is_file() or tool.stat().st_mode & 0o222:
        raise ProjectRuntimeError("project_native_uv_image_not_admitted")
    wheelhouse = project / "wheelhouse"
    if wheelhouse.resolve() != wheelhouse or not wheelhouse.is_dir():
        raise ProjectRuntimeError("project_native_uv_wheelhouse_not_admitted")
    environment.config["uv-path"] = str(tool)
    for setting in ("explicit_uv_path", "uv_path"):
        environment.__dict__.pop(setting, None)
    # Hatch's explicit environment setting takes precedence over uv-path.
    os.environ["HATCH_ENV_TYPE_VIRTUAL_UV_PATH"] = str(tool)
    os.environ.update(
        UV_OFFLINE="1",
        UV_NO_INDEX="1",
        UV_FIND_LINKS=str(wheelhouse),
        UV_CACHE_DIR=str(temporary / "uv-cache"),
        UV_PYTHON_DOWNLOADS="never",
        UV_KEYRING_PROVIDER="disabled",
        UV_LINK_MODE="copy",
    )


@beartype
@require(lambda project: project.is_dir())
def execute(
    project: Path, output: Path, temporary: Path, capsule: Path, *, operation: str, input_project: Path | None = None
) -> dict[str, Any]:
    """Use upstream decisions and lifecycle, never reconstruct a Hatch environment."""
    request = read_request(project)
    environment = _environment(project, temporary, request)
    if operation == "hatch.describe":
        return {
            "requirements": acquisition_requirements(environment, project),
            "extras": list(environment.features),
            "groups": list(environment.dependency_groups),
            "skip_install": environment.skip_install,
            "dev_mode": environment.dev_mode,
            "locked": environment.locked,
            "workspace": workspace_projects(environment, project),
        }
    if operation != "hatch.install":
        raise ProjectRuntimeError("project_native_hatch_operation_invalid")
    # The hook source is writable; installer wheels retain the original worker
    # input identity independently enforced by the managed subprocess adapter.
    inputs = project if input_project is None else input_project
    configure_installer(environment, inputs, temporary, capsule)
    os.environ.update(
        PIP_NO_INDEX="1",
        PIP_FIND_LINKS=str(inputs / "wheelhouse"),
        PIP_DISABLE_PIP_VERSION_CHECK="1",
        PIP_NO_COMPILE="1",
    )
    environment.check_compatibility()
    environment.app.project.prepare_environment(environment, keep_env=False)
    site = (
        Path(environment.virtual_env_path)
        / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    if site.resolve() != site or not site.is_dir() or not site.is_relative_to(temporary):
        raise ProjectRuntimeError("project_native_hatch_environment_outside_private_root")
    # Console launchers and interpreter aliases stay invocation-private. Only
    # inventoried project imports enter the reusable environment.
    shutil.copytree(site, output / "site-packages", symlinks=True)
    analyzer = capsule / f"python/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    inventory = environment_inventory(output / "site-packages", analyzer)
    (output / "environment-inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
    return {"manager": {"name": "hatch", "version": VERSION}, "status": "COMPLETE"}
