#!/usr/bin/env python3
"""Assemble verified analyzer and native-component inputs into a capsule root.

This maintainer-only step copies bytes. It never builds, signs, downloads, or
executes an input and never mutates either source tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
CODE_REVIEW_SOURCE = REPOSITORY_ROOT / "packages/specfact-code-review/src"
if str(CODE_REVIEW_SOURCE) not in sys.path:
    sys.path.insert(0, str(CODE_REVIEW_SOURCE))

from scripts import (  # noqa: E402
    build_macos_managed_uv as managed_uv_builder,
    build_macos_native_capsule as artifact_builder,
)
from specfact_code_review.run import runtime_native  # noqa: E402
from specfact_code_review.run.native_capsule import CHUNK, inspect_native_signature  # noqa: E402


SUPPORTED_ENVIRONMENTS = {f"darwin-arm64-cp{minor}" for minor in (311, 312, 313)}
REQUIRED_COMPONENT_FILES = frozenset(
    {
        "bin/specfact-native-broker",
        "bin/specfact-native-bootstrap",
        "bin/specfact-native-self-test",
        "bin/specfact-native-verifier",
        "policy/profile.sb",
    }
)
REQUIRED_COMPONENT_OUTPUTS = frozenset(name for name in REQUIRED_COMPONENT_FILES if name.startswith("bin/"))
NATIVE_COMPONENT_OUTPUTS = REQUIRED_COMPONENT_OUTPUTS
TRUSTED_RUNTIME_MODULES = {
    "specfact_code_review.run.native_child_worker": "trusted/specfact_code_review/run/native_child_worker.py",
    "specfact_code_review.run.native_managed_process": "trusted/specfact_code_review/run/native_managed_process.py",
    "specfact_code_review.run.native_analyzer_view": "trusted/specfact_code_review/run/native_analyzer_view.py",
    "specfact_code_review.run.native_project_pip": "trusted/specfact_code_review/run/native_project_pip.py",
    "specfact_code_review.run.native_project_hooks": "trusted/specfact_code_review/run/native_project_hooks.py",
    "specfact_code_review.run.native_project_manager": "trusted/specfact_code_review/run/native_project_manager.py",
    "specfact_code_review.run.native_tool_worker": "trusted/specfact_code_review/run/native_tool_worker.py",
    "specfact_code_review.run.native_worker": "trusted/specfact_code_review/run/native_worker.py",
}
PROJECT_TRUST_INPUT = "trusted/specfact_code_review/resources/keys/project-acquisition-public.pem"
LICENSE_MARKERS = frozenset({"copying", "copyright", "license", "notice"})
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")
IDENTITY = re.compile(r"[a-z0-9][a-z0-9.-]{0,127}")
FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class AssemblyError(ValueError):
    """An input cannot be assembled without weakening its recorded contract."""


@dataclass(frozen=True)
class AssemblyResult:
    runtime_root: Path
    closure: Path
    runtime_digest: str
    file_count: int


SignatureInspector = Callable[[Path], Mapping[str, object]]
InventoryRecord = dict[str, int | str]


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    descriptor = os.open(path, FILE_OPEN_FLAGS)
    try:
        while chunk := os.read(descriptor, CHUNK):
            digest.update(chunk)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _json_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024**2:
        raise AssemblyError(f"{label} metadata must be a bounded regular file")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssemblyError(f"{label} metadata is invalid JSON") from exc
    if not isinstance(value, dict):
        raise AssemblyError(f"{label} metadata must be an object")
    return value


def _canonical_directory(path: Path, label: str) -> Path:
    absolute = path.absolute()
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise AssemblyError(f"{label} must already exist") from exc
    if resolved != absolute or absolute.is_symlink() or not absolute.is_dir():
        raise AssemblyError(f"{label} must be a canonical ordinary directory")
    return absolute


def _path_profile(name: str) -> None:
    try:
        artifact_builder._safe_name(name, label="assembled payload")
    except (UnicodeEncodeError, ValueError) as exc:
        raise AssemblyError(f"noncanonical builder path: {name}") from exc


def _scan(root: Path, label: str) -> dict[str, InventoryRecord]:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise AssemblyError(f"{label} root must be an absolute ordinary directory")
    records: dict[str, InventoryRecord] = {".": {"kind": "directory", "mode": stat.S_IMODE(root.stat().st_mode)}}
    aliases: dict[str, str] = {".": "."}
    for directory, names, filenames in os.walk(root, topdown=True, followlinks=False):
        names.sort()
        filenames.sort()
        current = Path(directory)
        for name in [*names, *filenames]:
            path = current / name
            relative = path.relative_to(root).as_posix()
            folded = relative.casefold()
            if folded in aliases and aliases[folded] != relative:
                raise AssemblyError(f"{label} case-insensitive path collision: {aliases[folded]} and {relative}")
            aliases[folded] = relative
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise AssemblyError(f"{label} contains a symlink: {relative}")
            mode = stat.S_IMODE(metadata.st_mode)
            if name in names:
                if not stat.S_ISDIR(metadata.st_mode):
                    raise AssemblyError(f"{label} contains a special directory entry: {relative}")
                records[relative] = {"kind": "directory", "mode": mode}
            elif stat.S_ISREG(metadata.st_mode):
                records[relative] = {
                    "kind": "file",
                    "mode": mode,
                    "size": metadata.st_size,
                    "sha256": _sha_file(path),
                }
            else:
                raise AssemblyError(f"{label} contains a special file: {relative}")
    return records


def _inventory(value: object) -> dict[str, InventoryRecord]:
    if not isinstance(value, dict) or not value:
        raise AssemblyError("analyzer inventory is missing")
    normalized: dict[str, InventoryRecord] = {}
    aliases: dict[str, str] = {}
    for name, raw in value.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise AssemblyError("analyzer inventory is malformed")
        folded = name.casefold()
        if folded in aliases and aliases[folded] != name:
            raise AssemblyError(f"analyzer inventory case-insensitive collision: {aliases[folded]} and {name}")
        aliases[folded] = name
        kind = raw.get("kind")
        mode = raw.get("mode")
        if kind == "directory" and set(raw) == {"kind", "mode"} and type(mode) is int:
            normalized[name] = {"kind": kind, "mode": mode}
        elif (
            kind == "file"
            and set(raw) == {"kind", "mode", "size", "sha256"}
            and type(mode) is int
            and type(raw.get("size")) is int
            and isinstance(raw.get("sha256"), str)
            and HEX_DIGEST.fullmatch(str(raw["sha256"])) is not None
        ):
            normalized[name] = {
                "kind": kind,
                "mode": mode,
                "size": int(raw["size"]),
                "sha256": str(raw["sha256"]),
            }
        else:
            raise AssemblyError(f"analyzer inventory record is malformed: {name}")
    return normalized


def _default_signature(path: Path) -> Mapping[str, object]:
    signature = inspect_native_signature(path)
    metadata = runtime_native._macho_metadata(path)
    return {**signature, "architecture": tuple(metadata["architectures"])}


def _architecture(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (tuple, list)) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise AssemblyError("native signature architecture metadata is missing")


def _verify_observed_signature(path: Path, inspector: SignatureInspector) -> None:
    observed = inspector(path)
    try:
        architecture = _architecture(observed.get("architecture"))
    except AttributeError as exc:
        raise AssemblyError("native signature metadata is malformed") from exc
    if (
        observed.get("format") != "mach-o"
        or observed.get("mode") != "adhoc"
        or observed.get("hardened_runtime") is not True
        or "arm64" not in architecture
    ):
        raise AssemblyError(f"native signature or architecture mismatch: {path.name}")


def _verify_managed_uv_input(payload: Path, candidate: dict[str, Any], observed: dict[str, Any]) -> None:
    uv_members = any(name.startswith("uv/") for name in observed)
    if uv_members or "managed_uv" in candidate:
        if not uv_members or "managed_uv" not in candidate:
            raise AssemblyError("managed uv input lacks complete provenance")
        if managed_uv_builder.validate_artifact(payload / "uv") != candidate["managed_uv"]:
            raise AssemblyError("managed uv candidate provenance differs from installed input")


def _analyzer_input(root: Path, environment_id: str, inspector: SignatureInspector) -> tuple[Path, dict[str, Any]]:
    candidate = _json_object(root / "candidate.json", "analyzer candidate")
    version = candidate.get("version")
    expected_version = f"3.{environment_id.removeprefix('darwin-arm64-cp3')}"
    if environment_id not in SUPPORTED_ENVIRONMENTS or not isinstance(version, str) or version != expected_version:
        raise AssemblyError("analyzer ABI does not match the selected environment")
    if candidate.get("platform_evidence") != {"system": "Darwin", "machine": "arm64"}:
        raise AssemblyError("analyzer platform metadata does not identify Darwin ARM64")
    if any(
        not isinstance(candidate.get(field), str) or IDENTITY.fullmatch(str(candidate[field])) is None
        for field in ("profile_id", "semgrep_plan_id")
    ):
        raise AssemblyError("analyzer policy identity metadata is malformed")
    payload = root / "payload"
    observed = _scan(payload, "analyzer payload")
    declared = _inventory(candidate.get("inventory"))
    if observed != declared:
        raise AssemblyError("analyzer payload does not match its complete inventory")
    _verify_managed_uv_input(payload, candidate, observed)
    interpreter = f"bin/python{version}"
    interpreter_records = [name for name in observed if name.startswith("bin/python3.")]
    if interpreter_records != [interpreter] or observed.get(interpreter, {}).get("kind") != "file":
        raise AssemblyError("analyzer payload lacks the exact selected ABI interpreter")
    landmarks = {
        f"lib/python{version.replace('.', '')}.zip": "file",
        f"lib/python{version}/os.py": "file",
        f"lib/python{version}/lib-dynload": "directory",
    }
    if any(observed.get(name, {}).get("kind") != kind for name, kind in landmarks.items()):
        raise AssemblyError("analyzer payload lacks the relocated isolated getpath landmarks")
    if any(observed.get(name, {}).get("kind") != "file" for name in TRUSTED_RUNTIME_MODULES.values()) or (
        observed.get(PROJECT_TRUST_INPUT, {}).get("kind") != "file"
    ):
        raise AssemblyError("analyzer payload lacks trusted worker/package inputs")

    native_closure = candidate.get("native_closure")
    closure_images = native_closure.get("images") if isinstance(native_closure, dict) else None
    if not isinstance(closure_images, list):
        raise AssemblyError("analyzer native architecture inventory is missing")
    architecture_paths: set[str] = set()
    for record in closure_images:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise AssemblyError("analyzer native architecture inventory is malformed")
        if "arm64" not in record.get("architectures", []):
            raise AssemblyError("analyzer native architecture metadata mismatch")
        architecture_paths.add(str(record["path"]))

    signed = candidate.get("signed_images")
    if not isinstance(signed, list):
        raise AssemblyError("analyzer signed-image inventory is missing")
    signed_paths: set[str] = set()
    for record in signed:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise AssemblyError("analyzer signed-image record is malformed")
        name = str(record["path"])
        file_record = observed.get(name)
        signing = record.get("signing")
        if (
            name in signed_paths
            or not isinstance(file_record, dict)
            or file_record.get("kind") != "file"
            or record.get("sha256") != file_record.get("sha256")
            or not isinstance(signing, str)
            or "Signature=adhoc" not in signing
            or "(adhoc,runtime)" not in signing
            or "arm64" not in signing
        ):
            raise AssemblyError(f"analyzer signature metadata mismatch: {name}")
        signed_paths.add(name)
        _verify_observed_signature(payload / name, inspector)
    if signed_paths != architecture_paths or interpreter not in signed_paths:
        raise AssemblyError("analyzer signed-image and architecture inventories differ")
    return payload, candidate


def _component_input(root: Path, inspector: SignatureInspector) -> dict[str, Any]:
    metadata = _json_object(root / "component.json", "native component")
    signing = metadata.get("signing")
    if (
        metadata.get("schema") != "specfact-native-component-v1"
        or metadata.get("platform") != "darwin-arm64"
        or metadata.get("protocol") != 1
        or not isinstance(signing, dict)
        or signing.get("mode") != "adhoc"
        or signing.get("hardened_runtime") is not True
        or signing.get("customer_signing_required") is not False
    ):
        raise AssemblyError("native component platform or signing metadata mismatch")
    outputs = metadata.get("outputs")
    broker_requirement = metadata.get("broker_designated_requirement")
    if not isinstance(outputs, list) or set(outputs) != REQUIRED_COMPONENT_OUTPUTS:
        raise AssemblyError("native component output set is partial")
    if (
        not isinstance(broker_requirement, str)
        or not broker_requirement
        or len(broker_requirement.encode("utf-8")) > 4096
    ):
        raise AssemblyError("native component broker requirement is missing")
    plans = metadata.get("plans")
    if (
        metadata.get("status") != "candidate"
        or not isinstance(metadata.get("minimum_macos"), str)
        or re.fullmatch(r"[0-9]{1,2}\.[0-9]{1,2}", str(metadata["minimum_macos"])) is None
        or not isinstance(plans, list)
        or not plans
        or len(plans) != len(set(plans))
        or any(not isinstance(plan, str) or IDENTITY.fullmatch(plan) is None for plan in plans)
    ):
        raise AssemblyError("native component bounded plan metadata is malformed")
    files = metadata.get("files")
    if not isinstance(files, dict) or set(files) != REQUIRED_COMPONENT_FILES:
        raise AssemblyError("native component file inventory is partial")
    observed = _scan(root, "native component")
    observed_files = {name for name, record in observed.items() if record["kind"] == "file"}
    if observed_files != {*REQUIRED_COMPONENT_FILES, "component.json"}:
        raise AssemblyError("native component contains undeclared files")
    for name, digest in files.items():
        if not isinstance(digest, str) or HEX_DIGEST.fullmatch(digest) is None:
            raise AssemblyError(f"native component digest is malformed: {name}")
        if observed[name].get("sha256") != digest:
            raise AssemblyError(f"native component digest mismatch: {name}")
        if name in NATIVE_COMPONENT_OUTPUTS:
            _verify_observed_signature(root / name, inspector)
    return metadata


def _mkdirs(root: Path, relative: str) -> None:
    current = root
    for part in Path(relative).parts[:-1]:
        current /= part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError as exc:
            metadata = current.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise AssemblyError(f"assembly parent is not an ordinary directory: {current}") from exc


def _copy(source: Path, root: Path, relative: str, *, executable: bool) -> str:
    _path_profile(relative)
    _mkdirs(root, relative)
    destination = root / relative
    source_fd = os.open(source, FILE_OPEN_FLAGS)
    try:
        source_metadata = os.fstat(source_fd)
        if not stat.S_ISREG(source_metadata.st_mode):
            raise AssemblyError(f"assembly source is not a regular file: {source}")
        destination_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o500 if executable else 0o400,
        )
        digest = hashlib.sha256()
        try:
            copied = 0
            while chunk := os.read(source_fd, CHUNK):
                digest.update(chunk)
                copied += len(chunk)
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_fd, view)
                    if written <= 0:
                        raise AssemblyError("short assembly write")
                    view = view[written:]
            os.fsync(destination_fd)
        finally:
            os.close(destination_fd)
    finally:
        os.close(source_fd)
    if copied != source_metadata.st_size:
        raise AssemblyError(f"assembly source changed while copying: {source}")
    return digest.hexdigest()


def _write(root: Path, relative: str, payload: bytes) -> None:
    _path_profile(relative)
    _mkdirs(root, relative)
    descriptor = os.open(root / relative, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise AssemblyError("short assembly metadata write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _site_root(version: str) -> str:
    return f"python/lib/python{version}/site-packages"


def _mapped_analyzer_path(name: str, version: str) -> str:
    if name.startswith("git/"):
        relative = name.removeprefix("git/")
        try:
            return artifact_builder.GIT_RUNTIME_FILES[relative]
        except KeyError as exc:
            raise AssemblyError("undeclared managed Git input mapping") from exc
    if name == f"bin/python{version}":
        return "python/bin/python3"
    if name == "bin/ruff":
        return "tools/ruff"
    if name == "node/bin/node":
        return "tools/node"
    if name == "uv/bin/uv":
        return "tools/uv"
    if name == "site-packages/semgrep/bin/semgrep-core":
        return "tools/semgrep-core"
    semgrep_library_prefix = "site-packages/semgrep/bin/libs/"
    if name.startswith(semgrep_library_prefix):
        return f"tools/libs/{name.removeprefix(semgrep_library_prefix)}"
    if name == PROJECT_TRUST_INPUT:
        return "trust/project-acquisition-public.pem"
    if name.startswith("site-packages/"):
        return f"{_site_root(version)}/{name.removeprefix('site-packages/')}"
    if name.startswith("trusted/"):
        return f"{_site_root(version)}/{name.removeprefix('trusted/')}"
    return f"python/{name}"


def isolated_cpython_search_paths(runtime_root: Path, environment_id: str) -> tuple[Path, ...]:
    """Model the fixed `-I` relocated getpath roots; no process or environment is consulted."""
    if environment_id not in SUPPORTED_ENVIRONMENTS:
        raise AssemblyError("unsupported isolated CPython environment")
    version = f"3.{environment_id.removeprefix('darwin-arm64-cp3')}"
    root = runtime_root.absolute()
    return (
        root / f"python/lib/python{version.replace('.', '')}.zip",
        root / f"python/lib/python{version}",
        root / f"python/lib/python{version}/lib-dynload",
        root / f"{_site_root(version)}",
    )


def fixed_module_source(search_paths: tuple[Path, ...], module: str) -> Path:
    """Resolve one dotted fixed module from admitted getpath roots without importing it."""
    if re.fullmatch(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*", module) is None:
        raise AssemblyError("fixed module name is invalid")
    relative = Path(*module.split(".")).with_suffix(".py")
    matches = [root / relative for root in search_paths if (root / relative).is_file()]
    if len(matches) != 1:
        raise AssemblyError("fixed module is missing or ambiguous in isolated getpath")
    return matches[0]


def _component_provenance(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": metadata["schema"],
        "platform": metadata["platform"],
        "status": metadata.get("status"),
        "minimum_macos": metadata.get("minimum_macos"),
        "protocol": metadata["protocol"],
        "broker_designated_requirement": metadata["broker_designated_requirement"],
        "signing": metadata["signing"],
        "outputs": sorted(metadata["outputs"]),
        "plans": sorted(metadata.get("plans", [])),
        "production_eligible": False,
        "files": {name: metadata["files"][name] for name in sorted(metadata["files"])},
    }


def _closure_group(name: str) -> str:
    if name == "tools/git":
        return "managed-git-v1"
    if name.startswith("bin/specfact-native-") or name == "policy/profile.sb":
        return "native-component-v1"
    if name.startswith("trust/"):
        return "trusted-worker-v1"
    site_marker = "/site-packages/"
    if site_marker in name and (
        name.endswith("/python_analyzer_worker.py") or f"{site_marker}specfact_code_review/" in name
    ):
        return "trusted-worker-v1"
    if site_marker in name:
        return "analyzers-v1"
    if name == "python/bin/python3" or name.startswith(("python/lib/", "tools/")):
        return "python-runtime-v1"
    if name.startswith(("python/managers/", "python/wheelhouse/")):
        return "project-managers-v1"
    if name.startswith("provenance/"):
        return "provenance-v1"
    if name.startswith("licenses/"):
        return "licenses-v1"
    return "analyzers-v1"


def _runtime_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        name = path.relative_to(root).as_posix()
        digest.update(name.encode("ascii"))
        digest.update(b"\0")
        digest.update(stat.S_IMODE(path.stat().st_mode).to_bytes(2, "big"))
        digest.update(bytes.fromhex(_sha_file(path)))
    return digest.hexdigest()


def _owned_output(path: Path, identity: tuple[int, int] | None) -> bool:
    if identity is None:
        return False
    try:
        observed = path.lstat()
    except OSError:
        return False
    return (observed.st_dev, observed.st_ino) == identity


def _analyzer_provenance(candidate: dict[str, Any], environment_id: str, inventory_digest: str) -> dict[str, Any]:
    version = str(candidate["version"])
    provenance = {
        "schema": "specfact-analyzer-assembly-input-v1",
        "environment_id": environment_id,
        "platform": "darwin-arm64",
        "abi": f"cp{version.replace('.', '')}",
        "inventory_sha256": inventory_digest,
        "profile_id": candidate.get("profile_id"),
        "semgrep_plan_id": candidate.get("semgrep_plan_id"),
        "signed_images": [
            {"path": record["path"], "sha256": record["sha256"]}
            for record in sorted(candidate["signed_images"], key=lambda item: item["path"])
        ],
        "production_eligible": False,
    }
    if "managed_uv" in candidate:
        provenance["managed_uv"] = candidate["managed_uv"]
    return provenance


def assemble_macos_native_capsule(
    *,
    analyzer_root: Path,
    component_root: Path,
    output_root: Path,
    environment_id: str,
    signature_inspector: SignatureInspector = _default_signature,
) -> AssemblyResult:
    """Create one fresh capsule root and its complete external closure JSON."""
    analyzer = _canonical_directory(analyzer_root, "analyzer input")
    component = _canonical_directory(component_root, "native component input")
    destination = output_root.absolute()
    _canonical_directory(destination.parent, "output parent")
    closure_path = destination.parent / f"{destination.name}.closure.json"
    if destination.exists() or destination.is_symlink():
        raise AssemblyError("output root must not exist")
    if closure_path.exists() or closure_path.is_symlink():
        raise AssemblyError("output closure must not exist")
    if (
        destination in (analyzer, component)
        or destination.is_relative_to(analyzer)
        or destination.is_relative_to(component)
    ):
        raise AssemblyError("output root must be disjoint from inputs")

    payload, candidate = _analyzer_input(analyzer, environment_id, signature_inspector)
    component_metadata = _component_input(component, signature_inspector)
    git_receipt = None
    if any(name.startswith("git/") for name in candidate["inventory"]):
        git_receipt = artifact_builder.verify_managed_git_input(
            payload / "git", signature_inspector=signature_inspector
        )
        if candidate.get("managed_git") != git_receipt:
            raise AssemblyError("Git candidate receipt differs from installed input")
        artifact_builder.verify_managed_git_binding(
            component / "bin/specfact-native-broker",
            git_receipt["signing"]["requirement"],
            component_metadata["broker_designated_requirement"],
            signature_inspector=signature_inspector,
        )
    elif "managed_git" in candidate:
        raise AssemblyError("Git candidate receipt has no installed image")
    version = str(candidate["version"])
    work = destination.parent / f".{destination.name}.assemble-{uuid.uuid4().hex}"
    work.mkdir(mode=0o700)
    work_metadata = work.lstat()
    work_identity = (work_metadata.st_dev, work_metadata.st_ino)
    runtime_identity: tuple[int, int] | None = None
    closure_identity: tuple[int, int] | None = None
    copied: dict[str, str] = {}
    try:
        analyzer_records = _inventory(candidate["inventory"])
        for name, record in sorted(analyzer_records.items()):
            if record["kind"] != "file":
                continue
            output_name = _mapped_analyzer_path(name, version)
            digest = _copy(payload / name, work, output_name, executable=bool(int(record["mode"]) & 0o111))
            if digest != record["sha256"]:
                raise AssemblyError(f"analyzer input changed while copying: {name}")
            copied[output_name] = digest
        for name in sorted(REQUIRED_COMPONENT_FILES):
            digest = _copy(component / name, work, name, executable=name in NATIVE_COMPONENT_OUTPUTS)
            if digest != component_metadata["files"][name]:
                raise AssemblyError(f"native component changed while copying: {name}")
            copied[name] = digest

        licenses = [
            {"path": name, "sha256": digest}
            for name, digest in sorted(copied.items())
            if any(marker in Path(name).name.lower() for marker in LICENSE_MARKERS)
        ]
        if not licenses:
            raise AssemblyError("analyzer closure contains no declared license bytes")
        inventory_digest = hashlib.sha256(_canonical(candidate["inventory"])).hexdigest()
        analyzer_provenance = _analyzer_provenance(candidate, environment_id, inventory_digest)
        native_provenance = _component_provenance(component_metadata)
        if git_receipt is not None:
            native_provenance["managed_tool_requirements"] = {"tools/git": git_receipt["signing"]["requirement"]}
        assembly_provenance = {
            "schema": "specfact-native-assembly-v1",
            "environment_id": environment_id,
            "analyzer_inventory_sha256": inventory_digest,
            "native_component_files": native_provenance["files"],
            "fixed_worker_modules": sorted(TRUSTED_RUNTIME_MODULES),
            "isolated_getpath": [
                path.relative_to(work).as_posix() for path in isolated_cpython_search_paths(work, environment_id)
            ],
            "copy_only": True,
            "production_eligible": False,
        }
        generated = {
            "licenses/inventory.json": _canonical({"schema": "specfact-license-inventory-v1", "files": licenses})
            + b"\n",
            f"python/lib/python{version}/lib-dynload/.specfact-empty": b"",
            "provenance/analyzer.json": _canonical(analyzer_provenance) + b"\n",
            "provenance/assembly.json": _canonical(assembly_provenance) + b"\n",
            "provenance/native-component.json": _canonical(native_provenance) + b"\n",
        }
        for name, data in generated.items():
            _write(work, name, data)
            copied[name] = hashlib.sha256(data).hexdigest()

        search_paths = isolated_cpython_search_paths(work, environment_id)
        for module, input_name in TRUSTED_RUNTIME_MODULES.items():
            source = fixed_module_source(search_paths, module)
            expected = copied[_mapped_analyzer_path(input_name, version)]
            if _sha_file(source) != expected:
                raise AssemblyError("trusted native worker changed while binding fixed module layout")

        closure: dict[str, list[str]] = {}
        for name in sorted(copied):
            closure.setdefault(_closure_group(name), []).append(name)
        observed_files = sorted(path.relative_to(work).as_posix() for path in work.rglob("*") if path.is_file())
        declared_files = sorted(name for members in closure.values() for name in members)
        if observed_files != declared_files or len(declared_files) != len(set(declared_files)):
            raise AssemblyError("assembled closure does not declare every file exactly once")
        required_groups = {
            "native-component-v1",
            "python-runtime-v1",
            "trusted-worker-v1",
            "analyzers-v1",
            "project-managers-v1",
            "provenance-v1",
            "licenses-v1",
        }
        if not required_groups <= set(closure):
            raise AssemblyError("assembled closure is incomplete")

        runtime_digest = _runtime_digest(work)
        os.replace(work, destination)
        runtime_identity = work_identity
        descriptor = os.open(closure_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            metadata = os.fstat(descriptor)
            closure_identity = (metadata.st_dev, metadata.st_ino)
            data = _canonical({name: closure[name] for name in sorted(closure)}) + b"\n"
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise AssemblyError("short closure write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return AssemblyResult(destination, closure_path, runtime_digest, len(copied))
    except BaseException:
        if _owned_output(work, work_identity):
            shutil.rmtree(work)
        if _owned_output(destination, runtime_identity):
            shutil.rmtree(destination)
        if _owned_output(closure_path, closure_identity):
            closure_path.unlink()
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyzer-root", type=Path, required=True)
    parser.add_argument("--component-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--environment-id", choices=sorted(SUPPORTED_ENVIRONMENTS), required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = assemble_macos_native_capsule(
        analyzer_root=args.analyzer_root,
        component_root=args.component_root,
        output_root=args.output_root,
        environment_id=args.environment_id,
    )
    print(
        json.dumps(
            {
                "closure": str(result.closure),
                "file_count": result.file_count,
                "production_eligible": False,
                "runtime_digest": result.runtime_digest,
                "runtime_root": str(result.runtime_root),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
