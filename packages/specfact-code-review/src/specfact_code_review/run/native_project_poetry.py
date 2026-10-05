"""Pinned Poetry operations in an already confined, network-denied worker.

The caller injects sealed manager dependencies and owns fresh output inventory.
No manager result is an identity or production eligibility authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any
from unittest.mock import patch

from beartype import beartype
from icontract import require
from packaging.utils import canonicalize_name, parse_wheel_filename

from specfact_code_review.run import native_project_source as _source
from specfact_code_review.run.native_project_pip import validate_requirement, wheel_manifest
from specfact_code_review.run.runtime_models import ProjectRuntimeError


VERSION = "2.4.3"
SCHEMA = "native-poetry-request-v1"
RESOLUTION_SCHEMA = "native-poetry-resolution-v1"
_PROJECT_METADATA = {"name", "version", "requires-python", "dependencies", "optional-dependencies"}
_POETRY_METADATA = {"name", "version", "package-mode", "dependencies", "dev-dependencies", "group", "extras"}
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


def _regular_file(path: Path, limit: int, diagnostic: str) -> None:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= limit:
        raise ProjectRuntimeError(diagnostic)


@beartype
@require(lambda project: project.is_dir())
def read_request(project: Path) -> dict[str, Any]:
    path = project / ".specfact-poetry.json"
    diagnostic = "project_native_poetry_request_invalid"
    _regular_file(path, 1 << 20, diagnostic)
    try:
        request = json.loads(path.read_text())
    except (ValueError, UnicodeError) as exc:
        raise ProjectRuntimeError(diagnostic) from exc
    if not isinstance(request, dict) or set(request) != {"schema", "groups", "extras"} or request["schema"] != SCHEMA:
        raise ProjectRuntimeError(diagnostic)
    for key in ("groups", "extras"):
        values = request[key]
        if (
            not isinstance(values, list)
            or len(values) > 128
            or any(not isinstance(value, str) or not _NAME.fullmatch(value) for value in values)
            or len({canonicalize_name(value) for value in values}) != len(values)
        ):
            raise ProjectRuntimeError(diagnostic)
    return request


def selected_groups(package: Any, request: dict[str, Any]) -> list[str]:
    groups = {canonicalize_name(value) for value in request["groups"]}
    extras = {canonicalize_name(value) for value in request["extras"]}
    if not groups <= package.dependency_group_names(include_optional=True) or not extras <= set(package.extras):
        raise ProjectRuntimeError("project_native_poetry_selection_unknown:check groups and extras")
    return sorted(({"main"} | groups) if groups else package.dependency_group_names(include_optional=False))


def validate_lock(project: Path, locker: Any) -> None:
    _regular_file(project / "poetry.lock", 16 << 20, "project_native_poetry_lock_required:provide poetry.lock")
    if not locker.is_locked():
        raise ProjectRuntimeError("project_native_poetry_lock_required:provide poetry.lock")
    if not locker.is_fresh():
        raise ProjectRuntimeError("project_native_poetry_lock_stale:regenerate with Poetry 2.4.3 before preparation")


def acquisition_requirements(operations: list[Any]) -> list[str]:
    if len(operations) > 4096:
        raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")
    result = []
    for operation in operations:
        if operation.skipped:
            continue
        package = operation.package
        if operation.job_type == "install" and package.source_type == "git":
            _source.package_declaration(package)
            continue
        if operation.job_type != "install" or package.source_type is not None:
            raise ProjectRuntimeError(
                "project_native_dependency_source_unsupported:Poetry requires admitted index wheels"
            )
        result.append(validate_requirement(f"{package.name}=={package.version}"))
    return sorted(set(result))


def acquisition_sources(operations: list[Any]) -> list[dict[str, str]]:
    result = [
        _source.package_declaration(operation.package)
        for operation in operations
        if not operation.skipped and operation.job_type == "install" and operation.package.source_type == "git"
    ]
    if len(result) > _source.MAX_SOURCES:
        raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")
    return result


def validate_resolution_request(value: Any) -> dict[str, Any]:
    """Admit dependency metadata only; no source tree, hooks or configuration."""
    diagnostic = "project_native_poetry_resolution_request_invalid"
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "pyproject", "content_hash", "groups", "extras"}
        or value["schema"] != RESOLUTION_SCHEMA
        or not isinstance(value["content_hash"], str)
        or re.fullmatch(r"[a-f0-9]{64}", value["content_hash"]) is None
        or len(json.dumps(value).encode()) > 1 << 20
    ):
        raise ProjectRuntimeError(diagnostic)
    for key in ("groups", "extras"):
        names = value[key]
        if (
            not isinstance(names, list)
            or len(names) > 128
            or any(not isinstance(name, str) or not _NAME.fullmatch(name) for name in names)
        ):
            raise ProjectRuntimeError(diagnostic)
    data = value["pyproject"]
    if not isinstance(data, dict) or not set(data) <= {"project", "tool", "dependency-groups"}:
        raise ProjectRuntimeError(diagnostic)
    project = data.get("project", {})
    tool = data.get("tool", {})
    if (
        not isinstance(project, dict)
        or not set(project) <= _PROJECT_METADATA
        or not isinstance(tool, dict)
        or not set(tool) <= {"poetry"}
    ):
        raise ProjectRuntimeError(diagnostic)
    poetry = tool.get("poetry", {})
    if not isinstance(poetry, dict) or not set(poetry) <= _POETRY_METADATA:
        raise ProjectRuntimeError(diagnostic)
    count = 0

    def pep_requirements(rows: Any) -> None:
        nonlocal count
        if not isinstance(rows, list):
            raise ProjectRuntimeError(diagnostic)
        for row in rows:
            if not isinstance(row, str):
                raise ProjectRuntimeError(diagnostic)
            validate_requirement(row)
            count += 1

    pep_requirements(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    groups = data.get("dependency-groups", {})
    if not isinstance(optional, dict) or not isinstance(groups, dict):
        raise ProjectRuntimeError(diagnostic)
    for rows in optional.values():
        pep_requirements(rows)
    for rows in groups.values():
        if not isinstance(rows, list):
            raise ProjectRuntimeError(diagnostic)
        for row in rows:
            if isinstance(row, dict) and set(row) == {"include-group"} and isinstance(row["include-group"], str):
                continue
            pep_requirements([row])

    def legacy_dependencies(rows: Any) -> None:
        nonlocal count
        if not isinstance(rows, dict):
            raise ProjectRuntimeError(diagnostic)
        for name, declarations in rows.items():
            if not _NAME.fullmatch(name):
                raise ProjectRuntimeError(diagnostic)
            for declaration in declarations if isinstance(declarations, list) else [declarations]:
                if isinstance(declaration, dict):
                    if not set(declaration) <= {
                        "version",
                        "optional",
                        "python",
                        "platform",
                        "markers",
                        "extras",
                        "allow-prereleases",
                    }:
                        raise ProjectRuntimeError(
                            "project_native_poetry_resolution_source_unsupported:unlocked direct sources require exact source admission"
                        )
                elif not isinstance(declaration, str):
                    raise ProjectRuntimeError(diagnostic)
                count += 1

    legacy_dependencies(poetry.get("dependencies", {}))
    legacy_dependencies(poetry.get("dev-dependencies", {}))
    legacy_groups = poetry.get("group", {})
    if not isinstance(legacy_groups, dict):
        raise ProjectRuntimeError(diagnostic)
    for group in legacy_groups.values():
        if not isinstance(group, dict) or not set(group) <= {"optional", "dependencies"}:
            raise ProjectRuntimeError(diagnostic)
        legacy_dependencies(group.get("dependencies", {}))
    if count > 4096:
        raise ProjectRuntimeError(diagnostic)
    return value


def resolution_request(poetry: Any, groups: list[str], extras: list[str]) -> dict[str, Any]:
    original = poetry.pyproject.data
    if set(original.get("project", {}).get("dynamic", [])) & {
        "dependencies",
        "optional-dependencies",
        "requires-python",
    }:
        raise ProjectRuntimeError("project_native_poetry_resolution_dynamic_metadata_unsupported")
    if len(poetry.package.all_requires) > 4096 or any(
        dep.source_type or dep.source_name for dep in poetry.package.all_requires
    ):
        raise ProjectRuntimeError(
            "project_native_poetry_resolution_source_unsupported:unlocked direct sources require exact source admission"
        )
    metadata = {}
    if "project" in original:
        metadata["project"] = {key: value for key, value in original["project"].items() if key in _PROJECT_METADATA}
    if "dependency-groups" in original:
        metadata["dependency-groups"] = original["dependency-groups"]
    metadata["tool"] = {
        "poetry": {
            key: value for key, value in original.get("tool", {}).get("poetry", {}).items() if key in _POETRY_METADATA
        }
    }
    # Convert TOML containers to inert JSON, preserving Locker's relevant content.
    return validate_resolution_request(
        json.loads(
            json.dumps(
                {
                    "schema": RESOLUTION_SCHEMA,
                    "pyproject": metadata,
                    "content_hash": poetry.locker._get_content_hash(),
                    "groups": groups,
                    "extras": extras,
                }
            )
        )
    )


def deny_resolution_source(*args: Any, **kwargs: Any) -> Any:
    raise ProjectRuntimeError(
        "project_native_poetry_resolution_source_unsupported:direct origins need independently authenticated source metadata"
    )


def deny_sdist_metadata(*args: Any, **kwargs: Any) -> Any:
    raise ProjectRuntimeError(
        "project_native_poetry_resolution_metadata_unavailable:source-only metadata requires a separate network-denied source build"
    )


@contextmanager
def _sealed_manager_site(site: Path) -> Any:
    if site.is_symlink() or not site.is_dir() or site.resolve() != site:
        raise ProjectRuntimeError("project_native_poetry_resolution_manager_site_invalid")
    original = list(sys.path)
    excluded = {
        name: module
        for name, module in list(sys.modules.items())
        if name != "__main__" and "site-packages" in str(getattr(module, "__file__", ""))
    }
    sys.path[:] = [str(site), *(path for path in original if path and "site-packages" not in path)]
    for name in excluded:
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        for name, module in list(sys.modules.items()):
            if "site-packages" in str(getattr(module, "__file__", "")):
                sys.modules.pop(name, None)
        sys.modules.update(excluded)
        sys.path[:] = original


def resolve_metadata(request: dict[str, Any], project: Path, output: Path, temporary: Path) -> None:
    """Authentic lock resolution in the sealed network domain, never a hook worker."""
    request = validate_resolution_request(request)
    with _sealed_manager_site(project / ".specfact-build-dependencies/site-packages"):
        from cleo.io.null_io import NullIO
        from poetry.puzzle.provider import Provider
        from poetry.puzzle.solver import Solver
        from poetry.repositories import RepositoryPool
        from poetry.repositories.http_repository import HTTPRepository
        from poetry.repositories.pypi_repository import PyPiRepository
        from tomlkit import dumps

        source = temporary / "metadata"
        source.mkdir(mode=0o700)
        (source / "pyproject.toml").write_text(dumps(request["pyproject"]))
        poetry = _project(source, temporary)
        if resolution_request(poetry, request["groups"], request["extras"]) != request:
            raise ProjectRuntimeError("project_native_poetry_resolution_binding_mismatch")
        selected_groups(poetry.package, request)
        pool = RepositoryPool(config=poetry.config)
        pool.add_repository(PyPiRepository(config=poetry.config, disable_cache=True))
        # These entry points are the only upstream metadata paths which can clone
        # or invoke a source backend. Wheel/PEP 658/PyPI JSON are parsed as data.
        with (
            patch.object(Provider, "search_for_direct_origin_dependency", deny_resolution_source),
            patch.object(HTTPRepository, "_get_info_from_sdist", deny_sdist_metadata),
        ):
            try:
                solved = Solver(poetry.package, pool, [], [], NullIO()).solve().get_solved_packages()
            except Exception as exc:
                raise ProjectRuntimeError(f"project_native_poetry_resolution_incomplete:{exc}") from exc
        if len(solved) > 4096 or any(package.source_type is not None for package in solved):
            raise ProjectRuntimeError("project_native_poetry_resolution_source_unsupported")
        poetry.locker.set_lock_data(poetry.package, solved)
        validate_lock(source, poetry.locker)
        shutil.copyfile(source / "poetry.lock", output / "poetry.lock")
        (output / "resolution.json").write_text(
            json.dumps(
                {
                    "manager": {"name": "poetry", "version": VERSION},
                    "content_hash": request["content_hash"],
                    "lock_sha256": hashlib.sha256((output / "poetry.lock").read_bytes()).hexdigest(),
                }
            )
            + "\n"
        )


def local_wheel(wheelhouse: Path, filename: str, package: Any) -> Path:
    if wheelhouse.resolve() != wheelhouse or Path(filename).name != filename or not filename.endswith(".whl"):
        raise ProjectRuntimeError("project_native_wheelhouse_invalid")
    path = wheelhouse / filename
    _regular_file(path, 512 << 20, "project_native_wheelhouse_invalid")
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    if not any(value.get("file") == filename and value.get("hash") == digest for value in package.files):
        raise ProjectRuntimeError("project_native_poetry_wheel_lock_mismatch:acquire the exact SHA256 locked wheel")
    return path


def _project(project: Path, temporary: Path) -> Any:
    from poetry.__version__ import __version__
    from poetry.config.config import Config
    from poetry.core.constraints.version import Version
    from poetry.core.factory import Factory as CoreFactory
    from poetry.factory import Factory
    from poetry.packages.locker import Locker
    from poetry.poetry import Poetry
    from poetry.toml.file import TOMLFile

    if __version__ != VERSION:
        raise ProjectRuntimeError(f"project_native_manager_version_mismatch:poetry:{__version__}")
    _regular_file(project / "pyproject.toml", 1 << 20, "project_native_poetry_project_invalid")
    # CoreFactory parses Poetry/PEP 621 semantics without global config or plugins.
    Factory()._ensure_valid_poetry_version(project)
    base = CoreFactory().create_poetry(cwd=project, with_groups=True)
    if base.local_config.get("requires-plugins") or base.local_config.get("source"):
        raise ProjectRuntimeError(
            "project_native_poetry_configuration_unsupported:plugins or custom sources need admission"
        )
    if not base.package.python_constraint.allows(Version.parse(".".join(map(str, sys.version_info[:3])))):
        raise ProjectRuntimeError("project_native_poetry_python_incompatible")
    config = Config(use_environment=False)
    local = project / "poetry.toml"
    if local.exists() or local.is_symlink():
        _regular_file(local, 1 << 20, "project_native_poetry_configuration_invalid")
        config.merge(TOMLFile(local).read())
    config.merge(
        {"cache-dir": str(temporary / "poetry-cache"), "installer": {"parallel": False}, "keyring": {"enabled": False}}
    )
    return Poetry(
        base.pyproject_path,
        base.local_config,
        base.package,
        Locker(project / "poetry.lock", base.pyproject.data),
        config,
        disable_cache=True,
    )


class _CaptureExecutor:
    enabled = True

    def __init__(self) -> None:
        self.operations: list[Any] = []

    def execute(self, operations: list[Any]) -> int:
        self.operations = operations
        return 0


def _installer(poetry: Any, environment: Any, groups: list[str], extras: list[str], executor: Any) -> Any:
    from cleo.io.null_io import NullIO
    from poetry.installation.installer import Installer
    from poetry.repositories.installed_repository import InstalledRepository

    installer = Installer(
        NullIO(),
        environment,
        poetry.package,
        poetry.locker,
        poetry.pool,
        poetry.config,
        installed=InstalledRepository(),
        executor=executor,
    )
    installer.only_groups(groups).extras(extras)
    return installer


def _offline_executor(
    poetry: Any,
    environment: Any,
    wheelhouse: Path,
    bindings: list[dict[str, Any]] | None = None,
    source_wheels: Path | None = None,
) -> Any:
    from cleo.io.null_io import NullIO
    from poetry.core.packages.utils.link import Link
    from poetry.inspection.info import PackageInfo
    from poetry.installation.executor import Executor
    from poetry.repositories import Repository, RepositoryPool

    if wheelhouse.resolve() != wheelhouse:
        raise ProjectRuntimeError("project_native_wheelhouse_invalid")
    manifest = wheel_manifest(wheelhouse)

    class WheelhouseRepository(Repository):
        def find_links_for_package(self, package: Any) -> list[Any]:
            links = []
            for filename, digest in manifest.items():
                name, version, _, _ = parse_wheel_filename(filename)
                if name == package.name and str(version) == str(package.version):
                    links.append(Link((wheelhouse / filename).as_uri() + "#sha256=" + digest))
            return links

    class OfflineExecutor(Executor):
        def _prepare_git_archive(self, operation: Any) -> Path:
            if source_wheels is None:
                raise ProjectRuntimeError("project_native_source_wheel_binding_missing")
            return _source.bound_wheel(source_wheels, operation.package, bindings or [])

        def _download_link(self, operation: Any, link: Any) -> Path:
            archive = local_wheel(wheelhouse, link.filename, operation.package)
            self._populate_hashes_dict(archive, operation.package)
            return archive

    pool = RepositoryPool(config=poetry.config)
    repository = WheelhouseRepository("pypi")
    for filename, checksum in manifest.items():
        package = PackageInfo.from_wheel(wheelhouse / filename).to_package()
        package.files = [{"file": filename, "hash": "sha256:" + checksum}]
        repository.add_package(package)
    pool.add_repository(repository)
    poetry.set_pool(pool)
    executor = OfflineExecutor(environment, pool, poetry.config, NullIO(), parallel=False, disable_cache=True)
    executor.enable_bytecode_compilation(False)
    return executor


def private_site(environment: Any, prefix: Path) -> Path:
    """Reject nonprivate wheel schemes before any installer can write."""
    sites = {Path(environment.paths[key]) for key in ("purelib", "platlib")}
    if len(sites) != 1:
        raise ProjectRuntimeError("project_native_poetry_environment_invalid:split site scheme unsupported")
    site = sites.pop()
    destinations = ("purelib", "platlib", "scripts", "data", "include")
    for value in [
        site,
        *(Path(environment.scheme_dict[key]) for key in destinations if key in environment.scheme_dict),
    ]:
        if value.resolve() != value or not value.is_relative_to(prefix):
            raise ProjectRuntimeError("project_native_poetry_environment_outside_private_root")
    if not site.is_dir():
        raise ProjectRuntimeError("project_native_poetry_environment_invalid:missing private site")
    return site


def install_root(poetry: Any, environment: Any, wheelhouse: Path | None = None) -> None:
    """Use Poetry's editable root builder inside the project execution domain."""
    from cleo.io.null_io import NullIO
    from poetry.masonry.builders.editable import EditableBuilder

    compatibility = nullcontext() if wheelhouse is None else _offline_build_environment(poetry, wheelhouse)
    with compatibility:
        EditableBuilder(poetry, environment, NullIO()).build()


def _offline_build_environment(poetry: Any, wheelhouse: Path) -> Any:
    """Retain Poetry's build solver and installer, restricting candidates to acquired wheels."""
    from cleo.io.null_io import NullIO
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.project_package import ProjectPackage
    from poetry.installation.installer import Installer
    from poetry.packages.locker import Locker
    from poetry.repositories.installed_repository import InstalledRepository
    from poetry.utils.isolated_build import IsolatedEnv

    def install(isolated: Any, requirements: Any, *, constraints: Any = None) -> None:
        if constraints:
            raise ProjectRuntimeError("project_native_poetry_build_constraints_unsupported")
        if len(requirements) > 4096:
            raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")
        environment = isolated._env
        private_site(environment, environment.path)
        package = ProjectPackage("specfact-build-environment", "0.0.0")
        package.python_versions = ".".join(map(str, environment.version_info[:3]))
        for value in requirements:
            dependency = Dependency.create_from_pep_508(validate_requirement(value))
            if dependency.marker.validate(environment.marker_env):
                package.add_dependency(dependency)
        executor = _offline_executor(poetry, environment, wheelhouse)
        installer = Installer(
            NullIO(),
            environment,
            package,
            Locker(environment.path / "poetry.lock", {}),
            poetry.pool,
            poetry.config,
            installed=InstalledRepository.load(environment),
            executor=executor,
        )
        installer.update(True)
        if installer.run() != 0:
            raise ProjectRuntimeError("project_native_poetry_build_install_failed:missing acquired build wheel")

    return patch.object(IsolatedEnv, "install", install)


@beartype
@require(lambda project: project.is_dir())
def execute(project: Path, output: Path, temporary: Path, capsule: Path, *, operation: str) -> dict[str, Any]:
    """Describe first, then install authentic Poetry decisions from locked wheels."""
    if operation not in {"poetry.describe", "poetry.install"}:
        raise ProjectRuntimeError("project_native_poetry_operation_invalid")
    request = read_request(project)
    poetry = _project(project, temporary)
    groups = selected_groups(poetry.package, request)
    extras = [canonicalize_name(value) for value in request["extras"]]
    lock = project / "poetry.lock"
    if operation == "poetry.describe" and not lock.exists() and not lock.is_symlink():
        return {
            "locked": False,
            "lock_preserved": False,
            "requirements": [],
            "sources": [],
            "groups": groups,
            "extras": extras,
            "package_mode": poetry.is_package_mode,
            "manager": {"name": "poetry", "version": VERSION},
            "resolution": resolution_request(poetry, groups, extras),
            "hook_provenance": "local_build",
            "production_eligible": False,
        }
    validate_lock(project, poetry.locker)
    from poetry.utils.env import SystemEnv

    capture = _CaptureExecutor()
    if _installer(poetry, SystemEnv(Path(sys.prefix)), groups, extras, capture).run() != 0:
        raise ProjectRuntimeError("project_native_poetry_describe_failed:inspect preparation diagnostics")
    requirements = acquisition_requirements(capture.operations)
    result = {
        "requirements": requirements,
        "sources": acquisition_sources(capture.operations),
        "groups": groups,
        "extras": extras,
        "locked": True,
        "lock_preserved": True,
        "package_mode": poetry.is_package_mode,
        "manager": {"name": "poetry", "version": VERSION},
        "hook_provenance": "local_build",
        "production_eligible": False,
    }
    if operation == "poetry.describe":
        return result
    from poetry.utils.env import EnvManager, VirtualEnv

    prefix = temporary / "poetry-env"
    if temporary.resolve() != temporary or prefix.exists() or prefix.is_symlink():
        raise ProjectRuntimeError("project_native_poetry_environment_invalid:use a fresh canonical temporary root")
    EnvManager.build_venv(prefix, executable=Path(sys.executable), with_pip=False)
    environment = VirtualEnv(prefix)
    site = private_site(environment, prefix)
    binding_path = project / ".specfact-poetry-sources.json"
    bindings = []
    if binding_path.exists() or binding_path.is_symlink():
        _regular_file(binding_path, 1 << 20, "project_native_source_wheel_binding_invalid")
        bindings = json.loads(binding_path.read_text())
        if (
            not isinstance(bindings, list)
            or len(bindings) > 64
            or any(not isinstance(value, dict) for value in bindings)
        ):
            raise ProjectRuntimeError("project_native_source_wheel_binding_invalid")
    executor = _offline_executor(
        poetry, environment, project / "wheelhouse", bindings, project / ".specfact-poetry-source-wheels"
    )
    if _installer(poetry, environment, groups, extras, executor).run() != 0:
        raise ProjectRuntimeError(
            "project_native_poetry_install_failed:inspect managed probe or locked wheel diagnostics"
        )
    if poetry.is_package_mode:
        install_root(poetry, environment, project / "wheelhouse")
    private_site(environment, prefix)
    shutil.copytree(site, output / "site-packages", symlinks=True)
    return {**result, "status": "COMPLETE"}
