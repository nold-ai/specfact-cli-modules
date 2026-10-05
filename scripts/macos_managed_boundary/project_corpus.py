"""Bound native macOS project-corpus plans and maintainer acceptance evidence.

This harness never launches a host subprocess. It maps the pinned portable
corpus to fixed managed-broker plans and classifies missing compatibility as
incomplete evidence. Production runtime selection remains outside this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import tempfile
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from scripts.macos_managed_boundary.managed_subprocess import ManagedRun, UnadaptedProcessError


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST = REPO / "tests/fixtures/portable-runtime/corpus.json"
SCHEMA = "specfact-external-python-corpus-v1"
MANAGERS = frozenset({"pip", "hatch", "uv", "poetry"})
MANAGER_VERSIONS = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
ABIS = ("3.11", "3.12", "3.13")
FIXED_ENVIRONMENT = {
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/nonexistent",
    "PIP_NO_INDEX": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
}
ALLOWED_FIELDS = frozenset(
    {
        "name",
        "url",
        "commit",
        "fixture",
        "manager",
        "groups",
        "environment",
        "paths",
        "host_pytest_args",
        "host_note",
        "native_libraries",
        "verified_imports",
        "controlled_defect",
    }
)
Transport = Callable[[dict[str, Any]], dict[str, Any]]
ManagerExecutor = Callable[[dict[str, Any]], dict[str, Any]]
MAX_PREPARED_FILES = 30000
MAX_PREPARED_BYTES = 512 * 1024 * 1024


def _canonical_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError(f"corpus {label} is invalid")
    path = Path(value)
    if path.is_absolute() or path.as_posix() != value or ".." in path.parts:
        raise ValueError(f"corpus {label} must be canonical and relative")
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError(f"corpus {label} is invalid")
    return value


def _validate_entry(entry: object, *, reconstruction: bool) -> dict[str, Any]:
    if not isinstance(entry, dict) or set(entry) - ALLOWED_FIELDS:
        raise ValueError("corpus entry contains an unsupported field")
    selected = dict(entry)
    _identifier(selected.get("name"), "name")
    manager = selected.get("manager")
    if manager not in MANAGERS:
        raise ValueError("corpus manager is unsupported")
    if reconstruction:
        _canonical_relative(selected.get("fixture"), "fixture")
    else:
        url, commit = selected.get("url"), selected.get("commit")
        if not isinstance(url, str) or not url.startswith("https://github.com/") or not url.endswith(".git"):
            raise ValueError("corpus repository URL is invalid")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("corpus commit is invalid")
    groups = selected.get("groups")
    if not isinstance(groups, list) or any(_identifier(group, "group") != group for group in groups):
        raise ValueError("corpus groups are invalid")
    _identifier(selected.get("environment"), "environment")
    paths = selected.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("corpus paths are missing")
    for path in paths:
        _canonical_relative(path, "path")
    for argument in selected.get("host_pytest_args", []):
        if not isinstance(argument, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]+", argument):
            raise ValueError("corpus pytest argument is invalid")
    return selected


def load_corpus(path: Path = MANIFEST) -> dict[str, Any]:
    """Load and validate the exact pinned portable-runtime corpus."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or payload.get("python") != list(ABIS):
        raise ValueError("corpus schema or ABI matrix is invalid")
    repositories = [_validate_entry(item, reconstruction=False) for item in payload.get("repositories", [])]
    reconstructions = [_validate_entry(item, reconstruction=True) for item in payload.get("reconstructions", [])]
    if {entry["manager"] for entry in repositories} != MANAGERS or len(repositories) != len(MANAGERS):
        raise ValueError("corpus must contain exactly one repository for every manager")
    if not reconstructions:
        raise ValueError("corpus reconstruction is missing")
    return {**payload, "repositories": repositories, "reconstructions": reconstructions}


def _identity(entry: Mapping[str, Any]) -> str:
    selected = {key: entry[key] for key in sorted(entry) if key in ALLOWED_FIELDS}
    return hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _manager_argv(
    entry: Mapping[str, Any],
    preparation: Path,
    source: Path,
    payload: Path,
    abi: str,
    acquisition: Mapping[str, str] | None = None,
) -> tuple[str, list[str]]:
    python = str(payload / "bin" / f"python{abi}")
    manager = entry["manager"]
    groups = [str(group) for group in entry["groups"]]
    if acquisition is not None:
        executable = str(payload / "bin" / f"specfact-{manager}-adapter")
        return executable, [
            executable,
            "--offline",
            "--descriptor",
            acquisition["descriptor"],
            "--lock",
            acquisition["manager_lock"],
            "--wheelhouse",
            str(Path(acquisition["root"]) / "wheelhouse"),
            "--source",
            str(source),
            "--output",
            str(preparation / "site-packages"),
        ]
    if manager == "pip":
        return python, [
            python,
            "-I",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--require-hashes",
            "--target",
            str(preparation / "site-packages"),
            "--requirement",
            str(source / "requirements.lock"),
        ]
    executable = str(payload / "bin" / f"specfact-{manager}-adapter")
    if manager == "hatch":
        return executable, [
            executable,
            "--offline",
            "--project",
            str(source),
            "env",
            "create",
            str(entry["environment"]),
        ]
    if manager == "uv":
        return executable, [
            executable,
            "sync",
            "--offline",
            "--frozen",
            "--no-default-groups",
            "--project",
            str(source),
            *[argument for group in groups for argument in ("--group", group)],
        ]
    return executable, [
        executable,
        "--offline",
        "install",
        "--no-interaction",
        "--project",
        str(source),
        "--only",
        ",".join(("main", *groups)),
    ]


def _validated_acquisition(acquisition: Mapping[str, Any]) -> dict[str, str]:
    if set(acquisition) != {"root", "descriptor", "manager_lock", "content_sha256"}:
        raise ValueError("acquisition binding has unsupported fields")
    selected = {key: value for key, value in acquisition.items() if isinstance(value, str)}
    if len(selected) != len(acquisition) or not re.fullmatch(r"[0-9a-f]{64}", selected["content_sha256"]):
        raise ValueError("acquisition binding identity is invalid")
    root = Path(selected["root"])
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("acquisition root is missing or unsafe")
    for field in ("descriptor", "manager_lock"):
        path = Path(selected[field])
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError(f"acquisition {field} is missing or unsafe")
        try:
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"acquisition {field} escapes its root")
        except OSError as error:
            raise ValueError(f"acquisition {field} cannot be resolved") from error
    wheelhouse = root / "wheelhouse"
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise ValueError("acquisition wheelhouse is missing or unsafe")
    return selected


def validate_acquisition_binding(plan: Mapping[str, Any], acquisition: Mapping[str, Any]) -> None:
    """Reject path or digest substitution after the plan is constructed."""
    selected = _validated_acquisition(acquisition)
    expected = {
        "root": plan.get("acquisition_root"),
        "descriptor": plan.get("acquisition_descriptor"),
        "manager_lock": plan.get("manager_lock"),
        "content_sha256": plan.get("acquisition_content_sha256"),
    }
    if selected != expected:
        raise ValueError("acquisition binding differs from immutable preparation plan")


def materialize_acquired_source(plan: Mapping[str, Any], acquisition: Mapping[str, Any]) -> None:
    """Copy authenticated source bytes into the private preparation domain."""
    validate_acquisition_binding(plan, acquisition)
    source = Path(str(acquisition["root"])) / "source"
    destination = Path(str(plan["source_root"]))
    if source.is_symlink() or not source.is_dir() or destination.exists() or destination.is_symlink():
        raise ValueError("acquisition source or preparation destination is unsafe")
    for path in source.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("acquisition source contains a link or special file")
    shutil.copytree(source, destination, symlinks=False)


def _fixed_adapter_error(plan: Mapping[str, Any]) -> str | None:
    manager = plan.get("manager")
    if manager not in MANAGERS or plan.get("manager_version") != MANAGER_VERSIONS[manager]:
        return "fixed manager adapter version differs from admitted policy"
    if plan.get("domain_kind") != "preparation" or plan.get("environment") != FIXED_ENVIRONMENT:
        return "fixed manager adapter domain or environment differs from admitted policy"
    if "acquisition_content_sha256" not in plan:
        return None
    payload = Path(str(plan["payload_root"]))
    executable = str(payload / "bin" / f"specfact-{manager}-adapter")
    expected = [
        executable,
        "--offline",
        "--descriptor",
        str(plan["acquisition_descriptor"]),
        "--lock",
        str(plan["manager_lock"]),
        "--wheelhouse",
        str(plan["wheelhouse"]),
        "--source",
        str(plan["source_root"]),
        "--output",
        str(Path(str(plan["domain"])) / "site-packages"),
    ]
    if plan.get("executable") != executable or plan.get("argv") != expected:
        return "fixed manager adapter executable or arguments differ from admitted policy"
    return None


def build_plans(
    entry: Mapping[str, Any],
    root: Path,
    payload: Path,
    abi: str,
    *,
    acquisition: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive two fixed plans; project data never becomes an executable command."""
    selected = _validate_entry(dict(entry), reconstruction="fixture" in entry)
    if abi not in ABIS or not payload.is_absolute():
        raise ValueError("corpus ABI or payload root is invalid")
    project = root / selected["name"]
    preparation = project / "preparation"
    execution = project / "execution"
    source = preparation / "source"
    preparation.mkdir(parents=True, exist_ok=True)
    execution.mkdir(parents=True, exist_ok=True)
    identity = _identity(selected)
    admitted_acquisition = _validated_acquisition(acquisition) if acquisition is not None else None
    executable, preparation_argv = _manager_argv(selected, preparation, source, payload, abi, admitted_acquisition)
    tests = [path for path in selected["paths"] if path.startswith("tests/")]
    sources = [path for path in selected["paths"] if not path.startswith("tests/")]
    if not tests or not sources:
        raise ValueError("corpus entry requires source and test paths")
    base = {
        "corpus_identity": identity,
        "manager": selected["manager"],
        "project": selected["name"],
        "project_environment": selected["environment"],
        "source_root": str(source),
        "source_identity": selected.get("commit", f"fixture:{selected.get('fixture', '')}"),
        "payload_root": str(payload),
        "abi": abi,
        "environment": dict(FIXED_ENVIRONMENT),
        "tests": tests,
        "sources": sources,
    }
    preparation_plan = {
        **base,
        "plan_id": f"project-preparation-v1:{selected['manager']}",
        "domain_kind": "preparation",
        "domain": str(preparation),
        "prepared_output": str(preparation / "sealed-output"),
        "executable": executable,
        "argv": preparation_argv,
        "manager_version": MANAGER_VERSIONS[selected["manager"]],
    }
    if admitted_acquisition is not None:
        preparation_plan.update(
            {
                "acquisition_root": admitted_acquisition["root"],
                "acquisition_descriptor": admitted_acquisition["descriptor"],
                "acquisition_content_sha256": admitted_acquisition["content_sha256"],
                "manager_lock": admitted_acquisition["manager_lock"],
                "wheelhouse": str(Path(admitted_acquisition["root"]) / "wheelhouse"),
            }
        )
    observer = str(payload / "trusted" / "project_corpus_observer.py")
    python = str(payload / "bin" / f"python{abi}")
    execution_plan = {
        **base,
        "plan_id": "project-execution-v1:pytest-coverage-native-extension",
        "domain_kind": "execution",
        "domain": str(execution),
        "prepared_input": str(execution / "sealed-input"),
        "executable": python,
        "argv": [python, "-I", "-S", "-B", observer, "sealed-project-descriptor.json"],
    }
    return preparation_plan, execution_plan


def materialize_local_reconstruction(entry: Mapping[str, Any], destination: Path) -> None:
    """Materialize the repository-owned reconstruction without executing hooks."""
    selected = _validate_entry(dict(entry), reconstruction=True)
    source = MANIFEST.parent / selected["fixture"]
    if source.is_symlink() or not source.is_dir() or destination.exists() or destination.is_symlink():
        raise ValueError("local corpus reconstruction source or destination is unsafe")
    destination.mkdir(parents=True)
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("local corpus reconstruction contains a symlink")
        relative = path.relative_to(source)
        if path.is_dir():
            (destination / relative).mkdir(exist_ok=True)
            continue
        if not path.is_file():
            raise ValueError("local corpus reconstruction contains a special file")
        output = destination / (relative.with_suffix("") if relative.suffix == ".in" else relative)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(path.read_bytes())


def _prepared_inventory(root: Path) -> dict[str, dict[str, Any]]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("prepared output inventory root is unsafe")
    inventory: dict[str, dict[str, Any]] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        details = path.lstat()
        if stat.S_ISLNK(details.st_mode) or not (stat.S_ISDIR(details.st_mode) or stat.S_ISREG(details.st_mode)):
            raise ValueError("prepared output inventory contains a link or special file")
        if stat.S_ISDIR(details.st_mode):
            continue
        data = path.read_bytes()
        total += len(data)
        if len(inventory) >= MAX_PREPARED_FILES or total > MAX_PREPARED_BYTES:
            raise ValueError("prepared output inventory exceeds fixed bounds")
        inventory[relative] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "mode": stat.S_IMODE(details.st_mode),
        }
    if not inventory:
        raise ValueError("prepared output inventory is empty")
    return inventory


def verify_prepared_output(root: Path, expected: Mapping[str, Any]) -> None:
    """Reject every prepared-output path, byte or mode difference."""
    if _prepared_inventory(root) != expected:
        raise ValueError("prepared output inventory mismatch")


def copy_declared_project(plan: Mapping[str, Any], destination: Path) -> None:
    """Copy the already selected project into a private preparation output."""
    source = Path(plan["source_root"])
    error = _source_error(plan)
    if error:
        raise ValueError(error)
    if destination.exists() or destination.is_symlink():
        raise ValueError("prepared output destination already exists")
    destination.mkdir(parents=True)
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("project preparation source contains a symlink")
        relative = path.relative_to(source)
        output = destination / relative
        if path.is_dir():
            output.mkdir(exist_ok=True)
        elif path.is_file():
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(path.read_bytes())
            output.chmod(stat.S_IMODE(path.stat().st_mode))
        else:
            raise ValueError("project preparation source contains a special file")


def seal_prepared_output(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Bind deterministic prepared bytes to both declared execution domains."""
    inventory = _prepared_inventory(Path(plan["prepared_output"]))
    inventory_sha256 = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    descriptor = {
        "schema": "specfact-macos-project-preparation-v1",
        "plan_id": plan["plan_id"],
        "manager": plan["manager"],
        "corpus_identity": plan["corpus_identity"],
        "source_identity": plan["source_identity"],
        "preparation_domain": plan["domain"],
        "execution_domain": str(Path(plan["domain"]).parent / "execution"),
        "inventory_sha256": inventory_sha256,
    }
    descriptor_sha256 = hashlib.sha256(
        json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        **descriptor,
        "descriptor_sha256": descriptor_sha256,
        "inventory": inventory,
    }


def handoff_prepared_output(
    preparation: Mapping[str, Any], execution: Mapping[str, Any], descriptor: Mapping[str, Any]
) -> dict[str, Any]:
    """Copy only verified sealed bytes to the descriptor-bound execution domain."""
    if preparation["corpus_identity"] != execution["corpus_identity"]:
        raise ValueError("prepared descriptor corpus identity mismatch")
    if descriptor.get("preparation_domain") != preparation["domain"]:
        raise ValueError("prepared descriptor preparation domain mismatch")
    if descriptor.get("execution_domain") != execution["domain"]:
        raise ValueError("prepared descriptor execution domain mismatch")
    expected_descriptor = seal_prepared_output(preparation)
    if descriptor != expected_descriptor:
        raise ValueError("prepared output inventory or descriptor mismatch")
    source = Path(preparation["prepared_output"])
    destination = Path(execution["prepared_input"])
    if destination.exists() or destination.is_symlink():
        raise ValueError("execution input destination already exists")
    shutil.copytree(source, destination, symlinks=False)
    verify_prepared_output(destination, descriptor["inventory"])
    descriptor_path = Path(execution["domain"]) / "sealed-project-descriptor.json"
    descriptor_path.write_text(json.dumps(descriptor, sort_keys=True, separators=(",", ":")))
    return dict(descriptor)


def _installed_distributions(payload: Path) -> set[str]:
    selected: set[str] = set()
    for metadata in (payload / "site-packages").glob("*.dist-info/METADATA"):
        for line in metadata.read_text(errors="strict").splitlines():
            if line.startswith("Name: "):
                selected.add(re.sub(r"[-_.]+", "-", line[6:]).lower())
                break
    return selected


def _hatch_dependencies(source: Path, environment: str) -> set[str]:
    path = source / "hatch.toml"
    if not path.is_file() or path.is_symlink():
        return set()
    payload = tomllib.loads(path.read_text())
    dependencies = payload.get("envs", {}).get(environment, {}).get("dependencies", [])
    return {
        re.sub(r"[-_.]+", "-", match.group(0)).lower()
        for item in dependencies
        if isinstance(item, str) and (match := re.match(r"[A-Za-z0-9_.-]+", item))
    }


def _external_toolchain_required(source: Path) -> bool:
    native_suffixes = {".c", ".cc", ".cpp", ".cxx", ".m", ".mm", ".rs"}
    if any(path.is_file() and path.suffix.lower() in native_suffixes for path in source.rglob("*")):
        return True
    pyproject = source / "pyproject.toml"
    if not pyproject.is_file() or pyproject.is_symlink():
        return False
    text = pyproject.read_text().lower()
    return any(token in text for token in ("maturin", "meson", "scikit-build", "cmake", "setuptools-rust"))


def _manager_blockers(plan: Mapping[str, Any]) -> list[str]:
    source = Path(plan["source_root"])
    payload = Path(plan["payload_root"])
    manager = plan["manager"]
    if "acquisition_content_sha256" in plan:
        required = {
            "descriptor": Path(str(plan["acquisition_descriptor"])),
            "manager-lock": Path(str(plan["manager_lock"])),
            "wheelhouse": Path(str(plan["wheelhouse"])),
        }
        missing = [
            f"acquisition:{name}"
            for name, path in required.items()
            if path.is_symlink() or not (path.is_dir() if name == "wheelhouse" else path.is_file())
        ]
    else:
        locks = {
            "pip": ("requirements.lock",),
            "hatch": ("pyproject.toml", "hatch.toml", "hatch.lock"),
            "uv": ("pyproject.toml", "uv.lock"),
            "poetry": ("pyproject.toml", "poetry.lock"),
        }[manager]
        missing = [f"lock:{name}" for name in locks if not (source / name).is_file()]
    executable = Path(plan["executable"])
    if not executable.is_file() or executable.is_symlink():
        missing.append(f"sealed-executable:{executable.name}")
    if manager == "pip" and "acquisition_content_sha256" not in plan and not (payload / "site-packages/pip").is_dir():
        missing.append("sealed-distribution:pip")
    if manager == "hatch" and "acquisition_content_sha256" not in plan:
        installed = _installed_distributions(payload)
        for dependency in sorted(_hatch_dependencies(source, str(plan["project_environment"])) - installed):
            missing.append(f"sealed-distribution:{dependency}")
    return sorted(missing)


def prepare_with_fixed_adapter(plan: dict[str, Any], *, execute: ManagerExecutor | None = None) -> dict[str, Any]:
    """Run one exact broker adapter and seal its private output or fail incomplete."""
    fixed_error = _fixed_adapter_error(plan)
    if fixed_error:
        return {**_incomplete(fixed_error), "manager": plan.get("manager"), "missing_artifacts": []}
    source = Path(plan["source_root"])
    source_error = _source_error(plan)
    if source_error:
        return {**_incomplete(source_error), "manager": plan["manager"], "missing_artifacts": []}
    if _external_toolchain_required(source):
        return {
            "outcome": "INCOMPLETE",
            "reason": "external SDK/toolchain required; no host fallback",
            "manager": plan["manager"],
            "missing_artifacts": [],
        }
    if "acquisition_content_sha256" in plan:
        try:
            validate_acquisition_binding(
                plan,
                {
                    "root": plan["acquisition_root"],
                    "descriptor": plan["acquisition_descriptor"],
                    "manager_lock": plan["manager_lock"],
                    "content_sha256": plan["acquisition_content_sha256"],
                },
            )
        except ValueError as error:
            return {**_incomplete(str(error)), "manager": plan["manager"], "missing_artifacts": []}
    missing = _manager_blockers(plan)
    if missing:
        return {
            **_incomplete("missing sealed manager or lock artifact: " + ",".join(missing)),
            "manager": plan["manager"],
            "missing_artifacts": missing,
        }
    if execute is None:
        return {
            **_incomplete("broker-owned fixed manager executor is unavailable"),
            "manager": plan["manager"],
            "missing_artifacts": [],
        }
    prepared_output = Path(plan["prepared_output"])
    copy_declared_project(plan, prepared_output)
    try:
        response = execute(plan)
    except (OSError, ValueError, UnadaptedProcessError) as error:
        shutil.rmtree(prepared_output, ignore_errors=True)
        return {**_incomplete(str(error)), "manager": plan["manager"], "missing_artifacts": []}
    stderr = str(response.get("stderr", "")).lower()
    if response.get("returncode") and any(
        token in stderr for token in ("compiler", "xcode", "cmake", "meson", "rustc", "linker", "sdk")
    ):
        shutil.rmtree(prepared_output, ignore_errors=True)
        return {
            "outcome": "INCOMPLETE",
            "reason": "external SDK/toolchain required; no host fallback",
            "manager": plan["manager"],
            "missing_artifacts": [],
        }
    reason = _binding_error(plan, response)
    if reason:
        shutil.rmtree(prepared_output, ignore_errors=True)
        return {**_incomplete(reason), "manager": plan["manager"], "missing_artifacts": []}
    descriptor = seal_prepared_output(plan)
    return {
        "outcome": "PASS",
        "manager": plan["manager"],
        "missing_artifacts": [],
        **descriptor,
    }


def run_fixed_entry(
    entry: Mapping[str, Any],
    plans: tuple[dict[str, Any], dict[str, Any]],
    prepare: ManagerExecutor,
    execute: Transport,
) -> dict[str, Any]:
    """Run fixed preparation, verify/copy its seal, then issue execution."""
    preparation = prepare_with_fixed_adapter(plans[0], execute=prepare)
    if preparation["outcome"] != "PASS":
        return preparation
    try:
        sealed = seal_prepared_output(plans[0])
        if any(preparation.get(key) != value for key, value in sealed.items()):
            raise ValueError("prepared adapter result differs from sealed output inventory")
        descriptor = handoff_prepared_output(plans[0], plans[1], sealed)
        execution_plan = {
            **plans[1],
            "descriptor_sha256": descriptor["descriptor_sha256"],
            "inventory_sha256": descriptor["inventory_sha256"],
        }
        execution = _execute_plan(execution_plan, execute)
    except (OSError, ValueError) as error:
        return _incomplete(str(error))
    reason = _binding_error(execution_plan, execution) or _execution_error(execution_plan, execution)
    if execution.get("descriptor_sha256") != descriptor["descriptor_sha256"]:
        reason = reason or "execution result descriptor differs from sealed preparation"
    if execution.get("inventory_sha256") != descriptor["inventory_sha256"]:
        reason = reason or "execution result inventory differs from sealed preparation"
    if reason:
        return _incomplete(reason)
    return {
        "outcome": "PASS",
        "manager": plans[0]["manager"],
        "project": entry["name"],
        "descriptor_sha256": descriptor["descriptor_sha256"],
        "inventory_sha256": descriptor["inventory_sha256"],
        "production_approved": False,
    }


def native_manager_executor(root: Path, candidate: dict[str, Any]) -> ManagerExecutor:
    """Create a broker-only executor for the four fixed manager command shapes."""
    from scripts.macos_managed_boundary import python_analyzers

    def execute(plan: dict[str, Any]) -> dict[str, Any]:
        if Path(plan["payload_root"]) != candidate["payload"]:
            raise ValueError("fixed manager plan payload differs from verified candidate")
        if plan["manager"] == "pip" and "acquisition_content_sha256" not in plan:
            arguments = plan["argv"][4:]
            code = f"from pip._internal.cli.main import main; raise SystemExit(main({arguments!r}))"
            result = _physical_execute(root, candidate, Path(plan["domain"]), code)
        else:
            target = Path(plan["executable"])
            request = {
                "kind": "project-preparation",
                "manager": plan["manager"],
                "plan_id": plan["plan_id"],
                "corpus_identity": plan["corpus_identity"],
            }
            result = python_analyzers.execute(
                root,
                candidate,
                Path(plan["domain"]),
                target,
                list(plan["argv"]),
                request=request,
            )
        return {
            "broker_verified": result["broker_verified"],
            "plan_id": plan["plan_id"],
            "domain": plan["domain"],
            "corpus_identity": plan["corpus_identity"],
            "source_identity": plan["source_identity"],
            "returncode": result["returncode"],
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
        }

    return execute


def available_manager_matrix(root: Path, payload: Path, abi: str) -> dict[str, Any]:
    """Report exact local source/lock/executable blockers without host lookup."""
    rows = []
    for entry in load_corpus()["repositories"]:
        plan = build_plans(entry, root, payload, abi)[0]
        missing = _manager_blockers(plan)
        if _source_error(plan):
            missing.insert(0, f"pinned-source:{entry['name']}@{entry['commit']}")
        missing = sorted(set(missing))
        rows.append(
            {
                "manager": entry["manager"],
                "project": entry["name"],
                "outcome": "INCOMPLETE",
                "missing_artifacts": missing,
                "reason": "missing local pinned source or sealed artifact: " + ",".join(missing) + "; no host fallback",
            }
        )
    return {
        "schema": "specfact-macos-manager-availability-v1",
        "abi": abi,
        "rows": rows,
        "passed": 0,
        "incomplete": len(rows),
        "production_approved": False,
    }


def _incomplete(reason: str) -> dict[str, Any]:
    suffix = reason if "no host fallback" in reason else f"{reason}; no host fallback"
    return {"outcome": "INCOMPLETE", "reason": suffix}


def _execute_plan(plan: dict[str, Any], transport: Transport) -> dict[str, Any]:
    captured: list[dict[str, Any]] = []

    def invoke(request: dict[str, Any]) -> dict[str, Any]:
        expected = {"tool": plan["plan_id"], "argv": plan["argv"], "cwd": plan["domain"]}
        if request != expected:
            raise UnadaptedProcessError("request differs from immutable project plan")
        response = transport({"schema": "specfact-managed-project-plan-v1", "plan": plan, "request": request})
        captured.append(response)
        return response

    runner = ManagedRun(
        {plan["executable"]: plan["plan_id"]},
        invoke,
        cwd=plan["domain"],
        environment=plan["environment"],
    )
    runner.run(
        plan["argv"],
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
        cwd=plan["domain"],
        env=plan["environment"],
    )
    if len(captured) != 1:
        raise UnadaptedProcessError("broker did not return exactly one plan result")
    return captured[0]


def _binding_error(plan: Mapping[str, Any], evidence: Mapping[str, Any]) -> str | None:
    if evidence.get("incomplete"):
        return str(evidence["incomplete"])
    if evidence.get("broker_verified") is not True:
        return "project result lacks verified broker ownership"
    for field in ("plan_id", "domain", "corpus_identity"):
        if evidence.get(field) != plan[field]:
            return f"project result {field} differs from its declared domain"
    if evidence.get("returncode") != 0:
        return "managed project worker did not complete"
    if plan["domain_kind"] == "preparation" and evidence.get("source_identity") != plan["source_identity"]:
        return "prepared source identity differs from the pinned corpus"
    return None


def _source_error(plan: Mapping[str, Any]) -> str | None:
    source = Path(plan["source_root"])
    if source.is_symlink() or not source.is_dir():
        return "pinned project source root is missing or unsafe"
    for relative in (*plan["sources"], *plan["tests"]):
        path = source / relative
        if path.is_symlink() or not path.is_file():
            return "pinned project source or test path is missing or unsafe"
        try:
            if not path.resolve().is_relative_to(source.resolve()):
                return "pinned project path escapes its source root"
        except OSError:
            return "pinned project source path cannot be resolved"
    return None


def _execution_error(plan: Mapping[str, Any], evidence: Mapping[str, Any]) -> str | None:
    required = ("collected", "executed", "pytest_plugins", "coverage_files", "native_extension")
    if any(field not in evidence for field in required):
        return "required execution evidence is missing"
    if any(
        not isinstance(evidence[field], list) or any(not isinstance(item, str) for item in evidence[field])
        for field in ("collected", "executed", "pytest_plugins", "coverage_files")
    ):
        return "required execution evidence is malformed"
    if not set(evidence["collected"]) & set(plan["tests"]) or not set(evidence["executed"]) & set(plan["tests"]):
        return "required execution evidence has no declared test execution"
    if not evidence["pytest_plugins"] or not set(evidence["coverage_files"]) & set(plan["sources"]):
        return "required execution evidence lacks plugin or coverage proof"
    extension = evidence["native_extension"]
    if not isinstance(extension, dict) or any(
        extension.get(field) is not True for field in ("imported", "generic_arm64", "closure_admitted")
    ):
        return "required execution evidence lacks an admitted ARM64 extension"
    if extension.get("architecture") != "arm64":
        return "required execution evidence contains an incompatible extension"
    return None


def run_entry(
    entry: Mapping[str, Any], plans: tuple[dict[str, Any], dict[str, Any]], transport: Transport
) -> dict[str, Any]:
    """Run one fixed preparation/execution pair and preserve incomplete evidence."""
    if entry.get("name") != plans[0]["project"] or plans[0]["domain_kind"] != "preparation":
        return _incomplete("project plan does not match selected corpus entry")
    if plans[1]["domain_kind"] != "execution" or plans[0]["domain"] == plans[1]["domain"]:
        return _incomplete("preparation and execution domains are not separate")
    source_reason = _source_error(plans[0])
    if source_reason:
        return _incomplete(source_reason)
    try:
        preparation = _execute_plan(plans[0], transport)
        reason = _binding_error(plans[0], preparation)
        if (
            reason
            or preparation.get("prepared") is not True
            or not re.fullmatch(r"[0-9a-f]{64}", str(preparation.get("descriptor_sha256", "")))
        ):
            return _incomplete(reason or "preparation descriptor is missing")
        execution = _execute_plan(plans[1], transport)
    except (OSError, ValueError) as error:
        return _incomplete(str(error))
    reason = _binding_error(plans[1], execution) or _execution_error(plans[1], execution)
    if reason:
        return _incomplete(reason)
    return {
        "outcome": "PASS",
        "manager": plans[0]["manager"],
        "project": plans[0]["project"],
        "corpus_identity": plans[0]["corpus_identity"],
    }


def run_matrix(
    root: Path,
    payload: Path,
    abi: str,
    transport: Transport,
    *,
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run exactly one pinned repository for each supported manager."""
    selected = corpus or load_corpus()
    results = [
        run_entry(entry, build_plans(entry, root, payload, abi), transport) for entry in selected["repositories"]
    ]
    passed = sum(item["outcome"] == "PASS" for item in results)
    return {
        "schema": "specfact-macos-project-corpus-v1",
        "abi": abi,
        "managers": sorted(entry["manager"] for entry in selected["repositories"]),
        "projects": len(results),
        "passed": passed,
        "incomplete": len(results) - passed,
        "candidate_passed": passed == len(MANAGERS),
        "production_approved": False,
    }


def _observer_code(domain: Path, extension: str, source: str, test: str) -> str:
    result = domain / "project-result.json"
    coverage = domain / "coverage.json"
    return f"""import importlib, json, pathlib, pytest
from coverage import Coverage
domain = pathlib.Path({str(domain)!r})
native = importlib.import_module({extension!r})
cov = Coverage(source=[str(domain)])
cov.start()
status = pytest.main(['-q', '-p', 'fixture_plugin', {test!r}])
cov.stop(); cov.save(); cov.json_report(outfile={str(coverage)!r})
coverage_data = json.loads(pathlib.Path({str(coverage)!r}).read_text())
pathlib.Path({str(result)!r}).write_text(json.dumps({{
  'status': status,
  'plugin_loaded': (domain / 'plugin-loaded').is_file(),
  'coverage_recorded': any(name.endswith({source!r}) for name in coverage_data.get('files', {{}})),
  'native_extension_imported': native is not None,
}}))
raise SystemExit(status)
"""


def _physical_execute(root: Path, candidate: dict[str, Any], domain: Path, code: str) -> dict[str, Any]:
    from scripts.macos_managed_boundary import python_analyzers

    request = {
        "kind": "tool",
        "tool": "pytestcoverage",
        "abi": [int(item) for item in candidate["version"].split(".")],
        "version": candidate["version"],
        "argv": [str(candidate["target"]), "-c", code, "test_fixture.py::test_increment"],
        "plan_id": "project-corpus-observer-v1",
    }
    return python_analyzers.execute(root, candidate, domain, candidate["target"], [], request=request)


def run_physical_reconstruction_admission(candidate_path: Path) -> dict[str, Any]:
    """Admit the real local Hatch fixture and retain exact dependency blockers."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("physical project reconstruction requires native macOS ARM64")
    from scripts.macos_managed_boundary import python_analyzers

    candidate = python_analyzers.load_candidate(candidate_path.parent)
    entry = load_corpus()["reconstructions"][0]
    root = Path(tempfile.mkdtemp(prefix="sf-project-hatch-", dir="/private/tmp"))
    plans = build_plans(entry, root, candidate["payload"], candidate["version"])
    source = Path(plans[0]["source_root"])
    materialize_local_reconstruction(entry, source)
    expected = sorted(_hatch_dependencies(source, str(plans[0]["project_environment"])))
    result_path = Path(plans[0]["domain"]) / "adapter-admission.json"
    code = f"""import json, pathlib, tomllib
source = pathlib.Path({str(source)!r})
project = tomllib.loads((source / 'pyproject.toml').read_text())
hatch = tomllib.loads((source / 'hatch.toml').read_text())
assert project['project']['name'] == 'specfact-472-reconstructed-fixture'
review = hatch['envs']['review']
assert review['detached'] is True
assert sorted({expected!r}) == sorted([item.split('=', 1)[0].split('<', 1)[0].split('>', 1)[0] for item in review['dependencies']])
pathlib.Path({str(result_path)!r}).write_text(json.dumps({{'manager': 'hatch', 'environment': 'review'}}))
"""
    execution = _physical_execute(root, candidate, Path(plans[0]["domain"]), code)
    admitted = execution["broker_verified"] and execution["returncode"] == 0 and result_path.is_file()
    missing = _manager_blockers(plans[0])
    if not admitted:
        missing.append("managed-boundary:hatch-reconstruction-admission")
    missing = sorted(set(missing))
    shutil.rmtree(root)
    return {
        "manager": "hatch",
        "broker_verified": execution["broker_verified"],
        "outcome": "INCOMPLETE" if missing else "PASS",
        "missing_artifacts": missing,
        "reason": (
            "missing sealed Hatch preparation artifact: " + ",".join(missing) + "; no host fallback" if missing else ""
        ),
        "production_approved": False,
    }


def run_physical_observer(candidate_path: Path) -> dict[str, Any]:
    """Run separate preparation and execution observers through the native broker."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("physical project observer requires native macOS ARM64")
    from scripts.macos_managed_boundary import python_analyzers

    candidate = python_analyzers.load_candidate(candidate_path.parent)
    extension_record = next(
        (
            image
            for image in candidate["native_closure"]["images"]
            if image["path"].startswith("site-packages/_cffi_backend.")
            and image["path"].endswith(".so")
            and image.get("architectures") == ["arm64"]
        ),
        None,
    )
    if extension_record is None:
        raise ValueError("candidate lacks a generic ARM64 native extension")
    root = Path(tempfile.mkdtemp(prefix="sf-project-corpus-", dir="/private/tmp"))
    preparation = root / "preparation"
    execution = root / "execution"
    preparation.mkdir(mode=0o700)
    execution.mkdir(mode=0o700)
    (preparation / "project.json").write_text(json.dumps({"manager": "hatch", "offline": True}))
    preparation_code = (
        "import hashlib,json,pathlib; p=pathlib.Path('project.json'); "
        "assert json.loads(p.read_text()) == {'manager':'hatch','offline':True}; "
        "pathlib.Path('descriptor.json').write_text(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))"
    )
    prepared = _physical_execute(root, candidate, preparation, preparation_code)
    if (
        not prepared["broker_verified"]
        or prepared["returncode"] != 0
        or not (preparation / "descriptor.json").is_file()
    ):
        raise ValueError("managed preparation observer did not complete")
    for name, content in {
        "fixture.py": "def increment(value):\n    return value + 1\n",
        "test_fixture.py": "from fixture import increment\n\ndef test_increment():\n    assert increment(1) == 2\n",
        "fixture_plugin.py": (
            "from pathlib import Path\n\ndef pytest_configure(config):\n    Path('plugin-loaded').write_text('loaded')\n"
        ),
    }.items():
        (execution / name).write_text(content)
    code = _observer_code(execution, "_cffi_backend", "fixture.py", "test_fixture.py::test_increment")
    observed = _physical_execute(root, candidate, execution, code)
    result_file = execution / "project-result.json"
    if not observed["broker_verified"] or observed["returncode"] != 0 or not result_file.is_file():
        raise ValueError("managed execution observer did not complete")
    private = json.loads(result_file.read_text())
    shutil.rmtree(root)
    return {
        "broker_verified": True,
        "pytest_executed": private.get("status") == 0,
        "plugin_loaded": private.get("plugin_loaded") is True,
        "coverage_recorded": private.get("coverage_recorded") is True,
        "native_extension_imported": private.get("native_extension_imported") is True,
        "native_extension_architecture": "arm64",
        "preparation_domain_separate": True,
        "production_approved": False,
    }


def main() -> int:
    candidate = os.environ.get("SPECFACT_MACOS_PROJECT_CANDIDATE")
    if not candidate:
        raise SystemExit("SPECFACT_MACOS_PROJECT_CANDIDATE must identify a verified candidate.json")
    print(json.dumps(run_physical_observer(Path(candidate)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
