"""Pinned pip operations for separate acquisition and offline worker domains."""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import re
import sys
import tomllib
import zipfile
from email.parser import BytesParser
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import require
from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import InvalidWheelFilename, parse_wheel_filename

from specfact_code_review.run.runtime_domains import native_member_dependency_graphs
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


PIP_VERSION = "26.2.1"
SCHEMA = "specfact-native-pip-request-v1"
MAX_REQUEST_BYTES = 1 << 20
MAX_WHEELS = 4096
MAX_WHEEL_BYTES = 512 << 20
MAX_REQUIREMENTS = 4096
_HASH = re.compile(r"[0-9a-f]{64}")


@beartype
@require(lambda value: bool(value))
def validate_requirement(value: str) -> str:
    """Accept named wheel resolution inputs, never pip options or source URLs."""
    if len(value.encode()) > 4096 or any(character in value for character in "\r\n\x00"):
        raise ProjectRuntimeError("project_native_dependency_source_unsupported:invalid requirement")
    try:
        requirement = Requirement(value)
    except InvalidRequirement as exc:
        raise ProjectRuntimeError(f"project_native_dependency_source_unsupported:{value}") from exc
    if requirement.url:
        raise ProjectRuntimeError(
            f"project_native_dependency_source_unsupported:{requirement.name}:direct sources need managed build support"
        )
    return value


def _consume(budget: list[int]) -> None:
    budget[0] -= 1
    if budget[0] < 0:
        raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")


def _requirements_file(
    root: Path, name: str, seen: frozenset[str] = frozenset(), budget: list[int] | None = None, constraint: bool = False
) -> tuple[list[str], list[str]]:
    budget = [MAX_REQUIREMENTS] if budget is None else budget
    path = root / name
    if (
        name in seen
        or len(seen) >= 32
        or not path.is_file()
        or path.is_symlink()
        or not path.resolve().is_relative_to(root.resolve())
        or path.stat().st_size > MAX_REQUEST_BYTES
    ):
        raise ProjectRuntimeError(f"project_native_requirements_path_unsupported:{name}")
    requirements: list[str] = []
    constraints: list[str] = []
    text = path.read_text(encoding="utf-8").replace("\\\n", "")
    for line in text.splitlines():
        value = re.split(r"\s+#", line.strip(), maxsplit=1)[0]
        if not value or value.startswith("#"):
            continue
        _consume(budget)
        nested = re.fullmatch(r"(--requirement|--constraint)(?:\s+|=)(.+)|(-[rc])\s*(?:=\s*)?(.+)", value)
        if nested:
            flag, included = nested[1] or nested[3], nested[2] or nested[4]
            selected = (Path(name).parent / included).as_posix()
            child_requirements, child_constraints = _requirements_file(
                root, selected, seen | {name}, budget, flag in {"-c", "--constraint"}
            )
            requirements.extend(child_requirements)
            constraints.extend(child_constraints)
        else:
            # Preserve pip's hash syntax, but never accept arbitrary trailing options.
            parts = re.split(r"\s+--hash=sha256:", value)
            requirement = validate_requirement(parts[0])
            if any(_HASH.fullmatch(digest) is None for digest in parts[1:]):
                raise ProjectRuntimeError("project_native_dependency_source_unsupported:invalid requirement hash")
            (constraints if constraint else requirements).append(
                requirement + "".join(f" --hash=sha256:{digest}" for digest in parts[1:])
            )
    return requirements, constraints


def _group_requirements(
    groups: dict[str, Any], name: str, seen: frozenset[str] = frozenset(), budget: list[int] | None = None
) -> list[str]:
    budget = [MAX_REQUIREMENTS] if budget is None else budget
    _consume(budget)
    if name in seen or len(seen) >= 32 or not isinstance(groups.get(name), list):
        raise ProjectRuntimeError(f"project_native_dependency_group_invalid:{name}")
    result: list[str] = []
    for entry in groups[name]:
        _consume(budget)
        if isinstance(entry, str):
            result.append(validate_requirement(entry))
        elif isinstance(entry, dict) and set(entry) == {"include-group"} and isinstance(entry["include-group"], str):
            result.extend(_group_requirements(groups, entry["include-group"], seen | {name}, budget))
        else:
            raise ProjectRuntimeError(f"project_native_dependency_group_invalid:{name}")
    return result


@beartype
@require(lambda plan: plan.root.is_dir())
def dependency_request(plan: ProjectPlan, *, built_requirements: list[str] | None = None) -> dict[str, Any]:
    """Synthesize acquisition declarations without exposing the project source."""
    if plan.manager != "pip":
        raise ProjectRuntimeError(f"project_native_managed_launch_required:{plan.manager}")
    metadata = plan.root / "pyproject.toml"
    document = tomllib.loads(metadata.read_text(encoding="utf-8")) if metadata.is_file() else {}
    project = document.get("project", {})
    if built_requirements is None and any(
        name in project.get("dynamic", []) for name in ("dependencies", "optional-dependencies")
    ):
        raise ProjectRuntimeError("project_native_build_hook_required:dynamic dependencies")
    if (
        built_requirements is None
        and any((plan.root / name).is_file() for name in ("setup.py", "setup.cfg"))
        and not project
    ):
        raise ProjectRuntimeError("project_native_build_hook_required:legacy project metadata")
    requirements = [
        validate_requirement(value)
        for value in (built_requirements if built_requirements is not None else project.get("dependencies", []))
    ]
    constraints: list[str] = []
    budget = [MAX_REQUIREMENTS - len(requirements)]
    for extra in plan.extras if built_requirements is None else ():
        values = project.get("optional-dependencies", {}).get(extra)
        if not isinstance(values, list):
            raise ProjectRuntimeError(f"project_native_dependency_extra_invalid:{extra}")
        requirements.extend(validate_requirement(value) for value in values)
        budget[0] -= len(values)
        if budget[0] < 0:
            raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")
    for group in plan.groups:
        requirements.extend(_group_requirements(document.get("dependency-groups", {}), group, budget=budget))
    for name in plan.requirements:
        selected, limits = _requirements_file(plan.root, name, budget=budget)
        requirements.extend(selected)
        constraints.extend(limits)
    for name in plan.constraints:
        selected, limits = _requirements_file(plan.root, name, budget=budget, constraint=True)
        requirements.extend(selected)
        constraints.extend(limits)
    if len(requirements) + len(constraints) > MAX_REQUIREMENTS:
        raise ProjectRuntimeError("project_native_dependency_bounds_exceeded")
    return {"schema": SCHEMA, "requirements": requirements, "constraints": constraints}


def _pip(arguments: list[str], expected: str | None) -> None:
    import pip
    from pip._internal.cli.main import main
    from pip._internal.operations import prepare

    if expected is not None and pip.__version__ != expected:
        raise ProjectRuntimeError(f"project_native_manager_version_mismatch:pip:{pip.__version__}")
    original = prepare._get_prepared_distribution
    original_importers = list(sys.meta_path)
    original_import = builtins.__import__

    def wheels_only(requirement: Any, *args: Any, **kwargs: Any) -> Any:
        if requirement.link is None or not requirement.link.is_wheel or requirement.editable:
            raise ProjectRuntimeError("project_native_build_hook_required:source dependency")
        return original(requirement, *args, **kwargs)

    prepare._get_prepared_distribution = wheels_only
    try:
        exit_code = main(["--isolated", *arguments])
    finally:
        prepare._get_prepared_distribution = original
        sys.meta_path[:] = original_importers
        builtins.__import__ = original_import
    if exit_code != 0:
        raise ProjectRuntimeError(f"project_native_pip_failed:exit={exit_code}; inspect preparation diagnostics")


@beartype
@require(lambda root: root.is_dir())
def wheel_manifest(root: Path) -> dict[str, str]:
    """Bind a bounded wheel closure to the bytes acquired by the sealed manager."""
    result: dict[str, str] = {}
    total = 0
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".whl" or path.stat().st_nlink != 1:
            raise ProjectRuntimeError("project_native_wheelhouse_invalid")
        total += path.stat().st_size
        if len(result) >= MAX_WHEELS or total > MAX_WHEEL_BYTES:
            raise ProjectRuntimeError("project_native_wheelhouse_bounds_exceeded")
        result[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


@beartype
def install_wheels(
    wheelhouse: Path, output: Path, manifest: dict[str, str], *, expected_pip: str | None = PIP_VERSION
) -> None:
    """Use real pip's offline wheel scheme; never run hooks or compile bytecode."""
    if wheel_manifest(wheelhouse) != manifest:
        raise ProjectRuntimeError("project_native_wheel_digest_mismatch")
    target = output / "site-packages"
    if manifest:
        _pip(
            [
                "install",
                "--no-index",
                "--no-deps",
                "--no-compile",
                "--no-cache-dir",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--target",
                str(target),
                *(str(wheelhouse / name) for name in sorted(manifest)),
            ],
            expected_pip,
        )
    else:
        target.mkdir(parents=True, mode=0o700)
    if wheel_manifest(wheelhouse) != manifest:
        raise ProjectRuntimeError("project_native_wheel_digest_mismatch")


def _acquire(request: dict[str, Any], output: Path, *, local_wheels: Path | None = None) -> None:
    if (
        not isinstance(request, dict)
        or set(request) != {"schema", "requirements", "constraints"}
        or request["schema"] != SCHEMA
    ):
        raise ProjectRuntimeError("project_native_pip_request_invalid")
    for key in ("requirements", "constraints"):
        values = request[key]
        if not isinstance(values, list) or len(values) > MAX_REQUIREMENTS:
            raise ProjectRuntimeError("project_native_pip_request_invalid")
        for value in values:
            if not isinstance(value, str):
                raise ProjectRuntimeError("project_native_pip_request_invalid")
            parts = re.split(r"\s+--hash=sha256:", value)
            validate_requirement(parts[0])
            if any(_HASH.fullmatch(digest) is None for digest in parts[1:]):
                raise ProjectRuntimeError("project_native_pip_request_invalid")
    wheels = output / "wheels"
    wheels.mkdir(mode=0o700)
    local = []
    hashed = any(" --hash=sha256:" in value for key in ("requirements", "constraints") for value in request[key])
    if local_wheels is not None and local_wheels.is_dir():
        manifest = wheel_manifest(local_wheels)
        names: set[str] = set()
        for filename in manifest:
            try:
                name, _version, _build, _tags = parse_wheel_filename(filename)
            except InvalidWheelFilename as exc:
                raise ProjectRuntimeError("project_native_build_wheel_invalid") from exc
            if name in names:
                raise ProjectRuntimeError("project_native_build_wheel_conflict")
            names.add(name)
            # Explicit local candidates also satisfy transitive workspace
            # requirements, without resolving their names from an index.
            local.append(
                f"{name} @ {(local_wheels / filename).resolve().as_uri()}"
                + (f" --hash=sha256:{manifest[filename]}" if hashed else "")
            )
    if request["requirements"] or local:
        requirements = output / "requirements.txt"
        constraints = output / "constraints.txt"
        requirements.write_text("\n".join([*local, *request["requirements"]]) + "\n")
        constraints.write_text("\n".join(request["constraints"]) + "\n")
        _pip(
            [
                "download",
                "--only-binary=:all:",
                "--no-cache-dir",
                "--disable-pip-version-check",
                "--progress-bar",
                "off",
                "--use-deprecated=legacy-certs",
                "--index-url",
                "https://pypi.org/simple",
                "--dest",
                str(wheels),
                "--requirement",
                str(requirements),
                "--constraint",
                str(constraints),
            ],
            PIP_VERSION,
        )
    (output / "wheel-manifest.json").write_text(json.dumps(wheel_manifest(wheels), sort_keys=True) + "\n")


def inspect_wheel(wheel: Path, extras: list[str], sources: list[dict[str, str]] | None = None) -> list[str]:
    """Inspect in a fresh sealed target interpreter, without importing wheel code."""
    if (
        not isinstance(extras, list)
        or len(extras) > MAX_REQUIREMENTS
        or any(not isinstance(value, str) for value in extras)
    ):
        raise ProjectRuntimeError("project_native_build_request_invalid")
    with zipfile.ZipFile(wheel) as archive:
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1 or archive.getinfo(metadata[0]).file_size > MAX_REQUEST_BYTES:
            raise ProjectRuntimeError("project_native_build_metadata_invalid")
        message = BytesParser().parsebytes(archive.read(metadata[0]))
    values = message.get_all("Requires-Dist", [])
    if len(values) > MAX_REQUIREMENTS:
        raise ProjectRuntimeError("project_native_build_requirements_invalid")
    requirements = []
    for value in values:
        requirement = Requirement(value)
        if requirement.marker is None or any(requirement.marker.evaluate({"extra": extra}) for extra in ("", *extras)):
            requirement.marker = None
            if requirement.url and sources:
                from packaging.utils import canonicalize_name

                from specfact_code_review.run.native_project_source import validate_declaration

                admitted = [validate_declaration(value) for value in sources]
                if any(
                    canonicalize_name(requirement.name) == value["name"]
                    and requirement.url
                    in {
                        "git+" + value["url"],
                        "git+" + value["url"] + "@" + value["reference"],
                        "git+" + value["url"] + "@" + value["commit"],
                    }
                    for value in admitted
                ):
                    continue
            requirements.append(validate_requirement(str(requirement)))
    return requirements


@beartype
@require(lambda site_packages: site_packages.is_dir())
def environment_inventory(site_packages: Path, analyzer_root: Path) -> dict[str, Any]:
    """Read distribution metadata in the target interpreter without project imports."""
    installed = [
        {
            "metadata": {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "requires_dist": list(dist.requires or []),
            }
        }
        for dist in distributions(path=[str(site_packages)])
    ]
    if len(installed) > MAX_WHEELS or any(not row["metadata"]["name"] for row in installed):
        raise ProjectRuntimeError("project_native_inventory_invalid")
    inventory = {
        "installed": sorted(installed, key=lambda row: row["metadata"]["name"]),
        "environment": default_environment(),
    }
    graphs, conflicts = native_member_dependency_graphs(inventory, analyzer_root)
    return {**inventory, "member_graphs": graphs, "analyzer_conflicts": conflicts}


@beartype
def main() -> int:
    """Run one broker-fixed acquisition or installation with no caller argv."""
    if len(sys.argv) != 6 or sys.argv[5] not in {"acquire", "install", "inspect"}:
        return 76
    project, output, temporary = (Path(sys.argv[index]) for index in (2, 3, 4))
    os.environ.update(HOME=str(temporary), TMPDIR=str(temporary), XDG_CACHE_HOME=str(temporary))
    request_path = project / "request.json"
    try:
        if request_path.is_symlink() or not 0 < request_path.stat().st_size <= MAX_REQUEST_BYTES:
            raise ProjectRuntimeError("project_native_pip_request_invalid")
        request = json.loads(request_path.read_text())
        if sys.argv[5] == "acquire":
            from specfact_code_review.run import native_project_poetry, native_project_source

            if isinstance(request, dict) and request.get("schema") == native_project_poetry.RESOLUTION_SCHEMA:
                native_project_poetry.resolve_metadata(request, project, output, temporary)
            elif isinstance(request, dict) and request.get("schema") == native_project_source.REQUEST_SCHEMA:
                if set(request) != {"schema", "declaration"}:
                    raise ProjectRuntimeError("project_native_source_request_invalid")
                native_project_source.acquire(request["declaration"], output)
            else:
                _acquire(request, output, local_wheels=project / "wheels")
        elif sys.argv[5] == "inspect":
            if request == {"schema": "native-site-inventory-v1"}:
                site = project / "site-packages"
                if site.is_symlink() or not site.is_dir():
                    raise ProjectRuntimeError("project_native_inventory_invalid")
                capsule = Path(sys.argv[1])
                analyzer = capsule / f"python/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
                inventory = environment_inventory(site, analyzer)
                (output / "environment-inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
                return 0
            manifest = wheel_manifest(project / "wheels")
            if (
                len(manifest) != 1
                or not isinstance(request, dict)
                or set(request) not in ({"extras"}, {"extras", "sources"})
            ):
                raise ProjectRuntimeError("project_native_build_request_invalid")
            requirements = inspect_wheel(
                project / "wheels" / next(iter(manifest)), request["extras"], request.get("sources")
            )
            (output / "wheel-requirements.json").write_text(json.dumps({"requirements": requirements}) + "\n")
        else:
            install_wheels(project / "wheels", output, request)
            capsule = Path(sys.argv[1])
            analyzer = capsule / f"python/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
            inventory = environment_inventory(output / "site-packages", analyzer)
            (output / "environment-inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        (output / "preparation-error.json").write_text(json.dumps({"diagnostic": str(exc)}) + "\n")
        return 74


if __name__ == "__main__":
    raise SystemExit(main())
