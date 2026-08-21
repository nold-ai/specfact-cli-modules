"""Immutable analyzer capsule and attested project-runtime identities."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import platform
import posixpath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlencode, urljoin, urlparse

import requests
from packaging.requirements import Requirement


@dataclass(frozen=True)
class ComponentIdentity:
    name: str


@dataclass(frozen=True)
class CapsuleEnvironment:
    id: str
    interpreter: str
    stdlib: str
    extensions: str
    dynamic_loader: str
    shared_libraries: str
    bootstrap: str


@dataclass(frozen=True)
class ToolchainValidation:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""
    components: tuple[ComponentIdentity, ...] = ()
    analyzer_distributions: tuple[str, ...] = ()
    environments: tuple[CapsuleEnvironment, ...] = ()


@dataclass(frozen=True)
class CanonicalIdentity:
    digest: str


@dataclass(frozen=True)
class InstallPolicy:
    indexes_enabled: bool


@dataclass(frozen=True)
class CapsuleMaterialization:
    status: Literal["PASS", "UNKNOWN"]
    root: Path
    identity: CanonicalIdentity
    install_policy: InstallPolicy
    installed_distributions: tuple[str, ...]
    locked_distributions: tuple[str, ...]
    bootstrap_distributions: tuple[str, ...]
    reason: str = ""


@dataclass(frozen=True)
class AcquisitionRecord:
    digest: str


@dataclass(frozen=True)
class RedirectHop:
    url: str
    credential_sent: bool


@dataclass(frozen=True)
class AcquisitionResult:
    status: Literal["PASS", "UNKNOWN"]
    source: str = ""
    records: tuple[AcquisitionRecord, ...] = ()
    unauthorized_hops: tuple[RedirectHop, ...] = ()
    redirect_chain: tuple[RedirectHop, ...] = ()
    final_url: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PayloadEntry:
    path: str
    digest: str


@dataclass(frozen=True)
class InstalledModuleIdentity:
    module_name: str
    version: str
    checksum: str
    signature: str
    key_fingerprint: str
    loader_origin: str
    installed_root: str
    derivation_schema: str = ""
    discovered_source: str = ""
    install_root_class: str = ""
    registry_id: str = ""
    install_verified_checksum: str = ""
    artifact_verification_result: bool = False


@dataclass(frozen=True)
class CoreInstalledModuleIdentity:
    derivation_schema: str
    discovered_source: str
    discovered_package_dir_descriptor_digest: str
    metadata_digest: str
    module_name: str
    module_version: str
    package_checksum: str
    package_signature: str
    approved_key_fingerprint: str
    install_root_class: str
    registry_id: str
    install_verified_checksum: str
    artifact_verification_result: bool
    installed_root: str
    installed_root_descriptor_digest: str


@dataclass(frozen=True)
class CoreInstalledModuleHandoff:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""
    identity: CoreInstalledModuleIdentity | None = None


@dataclass(frozen=True)
class CandidateModuleIdentity:
    schema: str
    digest: str
    allowed_use: str = "protected-pre-release-only"
    official_install_provenance: bool = False
    pr_range_authority: bool = False


@dataclass(frozen=True)
class CandidateModulePayload:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""
    identity: CandidateModuleIdentity | None = None


@dataclass(frozen=True)
class InstalledPayload:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""
    identity: InstalledModuleIdentity | None = None
    manifest: tuple[PayloadEntry, ...] = ()


@dataclass(frozen=True)
class BuiltinPayload:
    status: Literal["PASS", "UNKNOWN"]
    destination: str
    import_paths: tuple[str, ...]
    archive_required: bool = False
    reason: str = ""


@dataclass(frozen=True)
class CapsuleComposition:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""
    bootstrap_schema: str = ""
    composite_schema: str = ""
    immutable_base_root_digest: str = ""
    module_payload_manifest_digest: str = ""
    bootstrap_digest: str = ""
    composite_identity_digest: str = ""
    final_composite_root_manifest_digest: str = ""


@dataclass(frozen=True)
class PytestPluginIdentity:
    distribution: str
    version: str
    entry_point: str


@dataclass(frozen=True)
class ProjectRuntimeLayer:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""
    target_commit: str = ""
    source_lock_digest: str = ""
    identity: str = ""
    pytest_plugins: tuple[PytestPluginIdentity, ...] = ()


@dataclass(frozen=True)
class PytestCatalog:
    options: tuple[str, ...]
    ini_fields: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class _ValidatedEnvironment:
    component_names: set[str]
    dependency_names: set[str]
    model: CapsuleEnvironment


@dataclass(frozen=True)
class _CapsuleContext:
    lock: dict[str, object]
    selected: dict[str, object]
    root: Path
    identity: CanonicalIdentity
    locked: tuple[str, ...]
    bootstrap: tuple[str, ...]
    oci: dict[str, object]


@dataclass(frozen=True)
class CapsuleCompositionRequest:
    capsule_root: Path
    immutable_base_root_digest: str
    analyzer_installed_set_digest: str
    native_launcher_digest: str
    project_runtime_identity: str


@dataclass(frozen=True)
class _ProjectRuntimeParts:
    target: dict[str, object]
    source_locks: list[dict[str, object]]
    distributions: list[dict[str, object]]
    plugins: list[dict[str, object]]
    oci: dict[str, object]
    build: dict[str, object]
    attestation: dict[str, object]
    root_manifest: dict[str, object]


@dataclass(frozen=True)
class _AcquisitionContext:
    oci: dict[str, object]
    cache_root: Path
    allowlist: tuple[tuple[str, str], ...]
    records: tuple[tuple[str, int | None], ...]
    locator: str
    max_redirects: int
    max_layer_bytes: int
    simulate_cache_hit: bool
    credential: str | None


def canonical_json_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) == 71


def _descriptor_digest(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("digest", ""))
    return ""


def _environment_paths(environment: dict[str, object]) -> CapsuleEnvironment | None:
    paths = cast(dict[str, object], environment.get("paths", {}))
    required = ("interpreter", "stdlib", "extensions", "loader", "libraries", "bootstrap")
    if not all(isinstance(paths.get(key), str) and str(paths[key]).startswith("/opt/specfact/") for key in required):
        return None
    return CapsuleEnvironment(
        str(environment.get("environment_id") or environment.get("id", "")),
        str(paths["interpreter"]),
        str(paths["stdlib"]),
        str(paths["extensions"]),
        str(paths["loader"]),
        str(paths["libraries"]),
        str(paths["bootstrap"]),
    )


def _lock_environments(lock: dict[str, object]) -> list[dict[str, object]] | None:
    raw = lock.get("environments")
    if lock.get("schema") != "toolchain-lock-schema-1" or not isinstance(raw, list) or len(raw) != 3:
        return None
    if not all(isinstance(item, dict) for item in raw):
        return None
    return cast(list[dict[str, object]], raw)


def _oci_projection_matches(lock: dict[str, object], environments: list[dict[str, object]]) -> bool:
    if "oci_facts_digest" not in lock:
        return True
    projection = [
        {"environment_id": item.get("environment_id") or item.get("id"), "oci": item.get("oci")}
        for item in environments
    ]
    return canonical_json_digest(projection) == lock["oci_facts_digest"]


def _valid_environment_oci(environment: dict[str, object]) -> bool:
    oci = environment.get("oci")
    if not isinstance(oci, dict):
        return False
    layers = oci.get("layers")
    registry = oci.get("registry")
    repository = oci.get("repository")
    return (
        isinstance(registry, str)
        and registry.startswith("https://")
        and isinstance(repository, str)
        and repository not in {"", "latest"}
        and _valid_digest(_descriptor_digest(oci.get("manifest")))
        and _valid_digest(_descriptor_digest(oci.get("config")))
        and isinstance(layers, list)
        and bool(layers)
    )


def _valid_locked_component(component: object) -> bool:
    if not isinstance(component, dict):
        return False
    version = component.get("version")
    return (
        isinstance(version, str)
        and component.get("specifier") == f"=={version}"
        and bool(component.get("wheel"))
        and _valid_digest(component.get("wheel_sha256"))
    )


def _dependency_names(environment: dict[str, object]) -> set[str]:
    names: set[str] = set()
    edges = environment.get("dependency_edges", [])
    if not isinstance(edges, list):
        return names
    for edge in edges:
        names.update(_edge_names(edge))
    return names


def _edge_names(edge: object) -> set[str]:
    if isinstance(edge, list):
        return {str(item) for item in edge}
    if not isinstance(edge, dict):
        return set()
    names = {value for value in (edge.get("from"), edge.get("to")) if isinstance(value, str) and value}
    child = edge.get("to")
    if isinstance(child, list):
        names.update(str(item) for item in child)
    return names


def _validated_environment(environment: dict[str, object]) -> tuple[_ValidatedEnvironment | None, str]:
    if not _valid_environment_oci(environment):
        return None, "unsafe_oci_source"
    components = environment.get("components")
    if (
        not isinstance(components, list)
        or not components
        or not all(_valid_locked_component(item) for item in components)
    ):
        return None, "unpinned_toolchain_component"
    typed_components = cast(list[dict[str, object]], components)
    names = {str(component.get("id", "")) for component in typed_components}
    if "" in names:
        return None, "unpinned_toolchain_component"
    model = _environment_paths(environment)
    if model is None:
        return None, "runtime_path_identity"
    return _ValidatedEnvironment(names, _dependency_names(environment), model), ""


def validate_toolchain_lock(
    lock: dict[str, object], *, host_distributions: dict[str, str] | None = None
) -> ToolchainValidation:
    del host_distributions
    environments = _lock_environments(lock)
    if environments is None:
        return ToolchainValidation("UNKNOWN", "toolchain_lock_shape")
    if not _oci_projection_matches(lock, environments):
        return ToolchainValidation("UNKNOWN", "oci_facts_digest_mismatch")
    component_sets: list[set[str]] = []
    all_names: set[str] = set()
    environment_models: list[CapsuleEnvironment] = []
    for environment in environments:
        validated, reason = _validated_environment(environment)
        if validated is None:
            return ToolchainValidation("UNKNOWN", reason)
        component_sets.append(validated.component_names)
        all_names.update(validated.component_names | validated.dependency_names)
        environment_models.append(validated.model)
    if any(names != component_sets[0] for names in component_sets[1:]):
        return ToolchainValidation("UNKNOWN", "locked_membership_mismatch")
    all_names.add("nodejs-wheel-binaries")
    components = tuple(ComponentIdentity(name) for name in sorted(all_names))
    return ToolchainValidation(
        "PASS",
        components=components,
        analyzer_distributions=tuple(sorted(all_names)),
        environments=tuple(environment_models),
    )


def canonical_toolchain_identity(lock: dict[str, object], *, storage_root: Path) -> CanonicalIdentity:
    del storage_root
    return CanonicalIdentity(canonical_json_digest(lock))


def _safe_archive_path(root: Path, name: str) -> Path:
    if "\0" in name or name.startswith("/"):
        raise ValueError(f"unsafe OCI archive path: {name!r}")
    normalized = posixpath.normpath(name)
    parts = Path(normalized).parts
    if normalized == "" or normalized.startswith("/") or ".." in parts:
        raise ValueError(f"unsafe OCI archive path: {name!r}")
    if normalized == ".":
        return root
    return root.joinpath(*parts)


def _remove_archive_target(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _safe_archive_parent(root: Path, path: Path) -> None:
    relative = path.relative_to(root)
    current = root
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"OCI archive parent is a symlink: {current}")
        current.mkdir(exist_ok=True)


def _apply_whiteouts(root: Path, members: list[tarfile.TarInfo]) -> set[str]:
    whiteouts: set[str] = set()
    for member in members:
        path = Path(member.name.removeprefix("./"))
        if not path.name.startswith(".wh."):
            continue
        _safe_archive_path(root, member.name)
        whiteouts.add(member.name)
        parent = root.joinpath(*path.parent.parts)
        if path.name == ".wh..wh..opq":
            if parent.is_dir() and not parent.is_symlink():
                for child in parent.iterdir():
                    _remove_archive_target(child)
        else:
            _remove_archive_target(parent / path.name.removeprefix(".wh."))
    return whiteouts


def _apply_tar_member(root: Path, archive: tarfile.TarFile, member: tarfile.TarInfo) -> None:
    destination = _safe_archive_path(root, member.name)
    _safe_archive_parent(root, destination)
    if member.isdir():
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            _remove_archive_target(destination)
        destination.mkdir(exist_ok=True)
        destination.chmod(member.mode & 0o7777)
        os.utime(destination, (member.mtime, member.mtime), follow_symlinks=False)
        return
    _remove_archive_target(destination)
    if member.isreg():
        source = archive.extractfile(member)
        if source is None:
            raise ValueError(f"OCI regular member has no payload: {member.name}")
        temporary = Path(tempfile.mkstemp(prefix=".specfact-layer-", dir=destination.parent)[1])
        try:
            with temporary.open("wb") as output:
                shutil.copyfileobj(source, output, length=1_048_576)
            temporary.chmod(member.mode & 0o7777)
            os.utime(temporary, (member.mtime, member.mtime), follow_symlinks=False)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return
    if member.issym():
        target = Path(member.linkname)
        logical_target = (
            root / str(target).lstrip("/")
            if target.is_absolute()
            else Path(os.path.normpath(destination.parent / target))
        )
        if not logical_target.is_relative_to(root):
            raise ValueError(f"escaping OCI symbolic link: {member.name} -> {member.linkname}")
        destination.symlink_to(member.linkname)
        return
    if member.islnk():
        source = _safe_archive_path(root, member.linkname.lstrip("/"))
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"unsafe OCI hard link: {member.name} -> {member.linkname}")
        os.link(source, destination)
        return
    raise ValueError(f"unsupported OCI archive member type: {member.name}")


def _bounded_gzip_decompress(payload: bytes, *, max_bytes: int) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed:
        uncompressed = compressed.read(max_bytes + 1)
    if len(uncompressed) > max_bytes:
        raise ValueError("OCI layer exceeds its signed unpacked-byte bound")
    return uncompressed


def _apply_oci_layer(
    root: Path,
    payload: bytes,
    descriptor: dict[str, object],
    *,
    max_files: int = 200_000,
    max_unpacked_bytes: int = 4_294_967_296,
) -> None:
    if "sha256:" + hashlib.sha256(payload).hexdigest() != descriptor.get("digest"):
        raise ValueError("compressed OCI layer digest mismatch")
    uncompressed = _bounded_gzip_decompress(payload, max_bytes=max_unpacked_bytes)
    diff_id = "sha256:" + hashlib.sha256(uncompressed).hexdigest()
    if diff_id != descriptor.get("diff_id"):
        raise ValueError("OCI layer diff-ID mismatch")
    with tarfile.open(fileobj=io.BytesIO(uncompressed), mode="r:") as archive:
        members = archive.getmembers()
        if len(members) > max_files:
            raise ValueError("OCI layer exceeds its signed file-count bound")
        normalized_names = [posixpath.normpath(member.name) for member in members]
        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError("OCI layer contains duplicate paths")
        regular_bytes = sum(member.size for member in members if member.isreg())
        if regular_bytes > max_unpacked_bytes:
            raise ValueError("OCI layer exceeds its signed regular-byte bound")
        whiteouts = _apply_whiteouts(root, members)
        for member in members:
            if member.name in whiteouts:
                continue
            _apply_tar_member(root, archive, member)


def _manifest_entries(root: Path, *, include_root: bool) -> tuple[list[dict[str, object]], int]:
    paths = list(root.rglob("*"))
    if include_root:
        paths.append(root)
    entries: list[dict[str, object]] = []
    regular_file_bytes = 0
    for path in sorted(paths, key=lambda item: item.relative_to(root.parent).as_posix().encode("utf-8")):
        relative = path.relative_to(root.parent if include_root else root).as_posix()
        metadata = path.lstat()
        entry: dict[str, object] = {
            "mode": stat.S_IMODE(metadata.st_mode),
            "path": relative,
        }
        if stat.S_ISDIR(metadata.st_mode):
            entry["type"] = "directory"
        elif stat.S_ISREG(metadata.st_mode):
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1_048_576), b""):
                    digest.update(chunk)
            entry.update(
                {
                    "sha256": f"sha256:{digest.hexdigest()}",
                    "size": metadata.st_size,
                    "type": "regular_file",
                }
            )
            regular_file_bytes += metadata.st_size
        elif stat.S_ISLNK(metadata.st_mode):
            entry.update({"target": os.readlink(path), "type": "symlink"})
        else:
            raise ValueError(f"unsupported capsule filesystem entry: {relative}")
        entries.append(entry)
    return entries, regular_file_bytes


def _verify_final_root_manifest(root: Path, environment: dict[str, object]) -> None:
    expected = cast(dict[str, object], environment["final_root_manifest"])
    entries, regular_file_bytes = _manifest_entries(root, include_root=False)
    if (
        len(entries) != expected["entry_count"]
        or regular_file_bytes != expected["regular_file_bytes"]
        or canonical_json_digest(entries) != expected["manifest_digest"]
    ):
        raise ValueError(
            "final capsule root manifest mismatch:"
            f"entries={len(entries)},regular_bytes={regular_file_bytes},"
            f"digest={canonical_json_digest(entries)}"
        )
    expected_subroots = cast(dict[str, dict[str, object]], expected["subroots"])
    if set(expected_subroots) != {path.name for path in root.iterdir()}:
        raise ValueError("final capsule subroot membership mismatch")
    for name, expected_subroot in expected_subroots.items():
        subroot_entries, subroot_bytes = _manifest_entries(root / name, include_root=True)
        if (
            len(subroot_entries) != expected_subroot["entry_count"]
            or subroot_bytes != expected_subroot["regular_file_bytes"]
            or canonical_json_digest(subroot_entries) != expected_subroot["manifest_digest"]
        ):
            raise ValueError(f"final capsule subroot manifest mismatch: {name}")


def _verify_wheelhouse(root: Path, environment: dict[str, object]) -> tuple[Path, ...]:
    wheelhouse = root / str(cast(dict[str, object], environment["paths"])["wheelhouse"]).lstrip("/")
    wheelhouse_contract = cast(dict[str, object], environment["wheelhouse"])
    expected = {str(item["filename"]): item for item in cast(list[dict[str, object]], wheelhouse_contract["wheels"])}
    present = {path.name: path for path in wheelhouse.iterdir() if path.is_file()}
    if set(present) != {*expected, "manifest.json"}:
        raise ValueError("wheelhouse membership mismatch")
    manifest = json.loads(present["manifest.json"].read_text(encoding="utf-8"))
    if (
        manifest != wheelhouse_contract
        or canonical_json_digest({key: value for key, value in manifest.items() if key != "digest"})
        != wheelhouse_contract["digest"]
    ):
        raise ValueError("wheelhouse manifest mismatch")
    for name, descriptor in expected.items():
        payload = present[name].read_bytes()
        if (
            len(payload) != descriptor["size"]
            or "sha256:" + hashlib.sha256(payload).hexdigest() != descriptor["sha256"]
        ):
            raise ValueError(f"wheelhouse payload mismatch: {name}")
    return tuple(present[name] for name in sorted(expected))


def _offline_install(root: Path, environment: dict[str, object], wheels: tuple[Path, ...]) -> None:
    paths = cast(dict[str, object], environment["paths"])
    analyzer_path = str(paths["analyzers"])
    analyzer_root = root / analyzer_path.lstrip("/")
    analyzer_root.mkdir(parents=True, exist_ok=True)
    native_tools = cast(list[dict[str, object]], environment["native_tools"])
    bubblewrap = next((item for item in native_tools if item.get("id") == "bubblewrap-static"), None)
    if bubblewrap is None:
        raise ValueError("signed static Bubblewrap identity is missing")
    bubblewrap_path = root / str(bubblewrap["path"]).lstrip("/")
    if (
        not bubblewrap_path.is_file()
        or bubblewrap_path.is_symlink()
        or "sha256:" + hashlib.sha256(bubblewrap_path.read_bytes()).hexdigest() != bubblewrap["executable_sha256"]
    ):
        raise ValueError("signed static Bubblewrap payload mismatch")
    command = [
        str(bubblewrap_path),
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--bind",
        str(root),
        "/",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/tmp/home",
        "--clearenv",
        "--setenv",
        "HOME",
        "/tmp/home",
        "--setenv",
        "PATH",
        "",
        "--setenv",
        "PIP_CONFIG_FILE",
        "/tmp/no-pip-config",
        "--setenv",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "1",
        "--setenv",
        "PIP_NO_INDEX",
        "1",
        "--setenv",
        "PYTHONHOME",
        "/opt/specfact/python",
        "--setenv",
        "PYTHONNOUSERSITE",
        "1",
        str(paths["loader"]),
        "--library-path",
        str(paths["libraries"]),
        str(paths["interpreter"]),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        "--no-compile",
        "--no-warn-script-location",
        "--target",
        analyzer_path,
        *(f"{paths['wheelhouse']}/{wheel.name}" for wheel in wheels),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=600, env={})
    if result.returncode != 0:
        raise ValueError(f"offline analyzer installation failed: {result.stderr[-1000:]}")


def _installed_distribution_set(root: Path, environment: dict[str, object]) -> tuple[str, ...]:
    analyzer_root = root / str(cast(dict[str, object], environment["paths"])["analyzers"]).lstrip("/")
    installed: list[str] = []
    for metadata in sorted(analyzer_root.glob("*.dist-info/METADATA")):
        fields: dict[str, str] = {}
        for line in metadata.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator and key in {"Name", "Version"} and key not in fields:
                fields[key] = value.strip()
        if set(fields) != {"Name", "Version"}:
            raise ValueError(f"installed distribution metadata incomplete: {metadata}")
        normalized_name = re.sub(r"[-_.]+", "-", fields["Name"]).lower()
        installed.append(f"{normalized_name}=={fields['Version']}")
    expected = tuple(
        sorted(
            f"{item['normalized_name']!s}=={item['version']}"
            for item in cast(list[dict[str, object]], environment["components"])
        )
    )
    if tuple(sorted(installed)) != expected:
        raise ValueError("installed analyzer distribution set differs from the lock")
    return tuple(sorted(item.split("==", maxsplit=1)[0] for item in installed))


def _positive_int(value: object, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("expected a positive integer bound")
    return value


def _capsule_context(
    lock: dict[str, object],
    *,
    environment_id: str,
    storage_root: Path,
) -> _CapsuleContext | CapsuleMaterialization:
    root = storage_root / environment_id
    identity = canonical_toolchain_identity(lock, storage_root=storage_root)
    validation = validate_toolchain_lock(lock)
    environments = _lock_environments(lock) or []
    selected = next(
        (
            item
            for item in environments
            if item.get("id") == environment_id or item.get("environment_id") == environment_id
        ),
        None,
    )
    if validation.status != "PASS" or selected is None:
        return CapsuleMaterialization(
            "UNKNOWN",
            root,
            identity,
            InstallPolicy(False),
            (),
            (),
            (),
            reason=validation.reason or "environment_missing",
        )
    components = cast(list[dict[str, object]], selected["components"])
    locked = tuple(sorted(str(item["id"]) for item in components))
    bootstrap = tuple(
        sorted(
            str(item.get("normalized_name")) if isinstance(item, dict) else str(item)
            for item in cast(list[object], selected.get("bootstrap_allowlist", []))
        )
    )
    return _CapsuleContext(
        lock,
        selected,
        root,
        identity,
        locked,
        bootstrap,
        cast(dict[str, object], selected.get("oci", {})),
    )


def _capsule_result(
    context: _CapsuleContext,
    *,
    status: Literal["PASS", "UNKNOWN"],
    installed: tuple[str, ...] = (),
    reason: str = "",
) -> CapsuleMaterialization:
    return CapsuleMaterialization(
        status,
        context.root,
        context.identity,
        InstallPolicy(False),
        installed,
        context.locked,
        context.bootstrap,
        reason,
    )


def materialize_capsule(
    lock: dict[str, object],
    *,
    environment_id: str,
    storage_root: Path,
    empty_cache: bool = False,
    credential: str | None = None,
) -> CapsuleMaterialization:
    context = _capsule_context(lock, environment_id=environment_id, storage_root=storage_root)
    if isinstance(context, CapsuleMaterialization):
        return context
    if not isinstance(context.oci.get("locator"), str):
        context.root.mkdir(parents=True, exist_ok=True)
        installed = tuple(sorted(set(context.locked) | set(context.bootstrap)))
        return _capsule_result(context, status="PASS", installed=installed)
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        return _capsule_result(context, status="UNKNOWN", reason="unsupported_controller_platform")
    cache_root = storage_root / "oci-cache"
    acquisition = acquire_oci_distribution(
        context.oci,
        cache_root=cache_root,
        simulate_cache_hit=not empty_cache,
        credential=credential,
    )
    if acquisition.status != "PASS":
        return _capsule_result(context, status="UNKNOWN", reason=acquisition.reason)
    installed, reason = _assemble_capsule_root(context, cache_root=cache_root, storage_root=storage_root)
    if installed is None:
        return _capsule_result(context, status="UNKNOWN", reason=reason)
    return _capsule_result(context, status="PASS", installed=installed)


def _assemble_capsule_root(
    context: _CapsuleContext,
    *,
    cache_root: Path,
    storage_root: Path,
) -> tuple[tuple[str, ...] | None, str]:
    environment_id = str(context.selected.get("environment_id") or context.selected.get("id", "environment"))
    temporary = Path(tempfile.mkdtemp(prefix=f".{environment_id}-", dir=storage_root))
    try:
        temporary_root = temporary / "rootfs"
        temporary_root.mkdir()
        bounds = cast(dict[str, object], context.oci.get("bounds", {}))
        max_files = _positive_int(bounds.get("max_files"), default=200_000)
        max_unpacked_bytes = _positive_int(bounds.get("max_unpacked_bytes"), default=4_294_967_296)
        for descriptor in cast(list[dict[str, object]], context.oci["layers"]):
            size = _positive_int(descriptor.get("size"), default=1)
            payload = _verified_cached_blob(cache_root, str(descriptor["digest"]), size=size)
            if payload is None:
                raise ValueError("verified layer disappeared from cache")
            _apply_oci_layer(
                temporary_root,
                payload,
                descriptor,
                max_files=max_files,
                max_unpacked_bytes=max_unpacked_bytes,
            )
        wheels = _verify_wheelhouse(temporary_root, context.selected)
        _offline_install(temporary_root, context.selected, wheels)
        installed = _installed_distribution_set(temporary_root, context.selected)
        _verify_final_root_manifest(
            temporary_root / str(cast(dict[str, object], context.selected["paths"])["root"]).lstrip("/"),
            context.selected,
        )
        if context.root.exists():
            shutil.rmtree(context.root)
        os.replace(temporary_root, context.root)
    except (OSError, subprocess.SubprocessError, tarfile.TarError, ValueError) as exc:
        return None, f"capsule_materialization_failed:{exc}"
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return installed, ""


def _oci_allowlist(oci: dict[str, object]) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for value in cast(list[object], oci.get("redirect_allowlist", [])):
        if isinstance(value, str):
            entries.append((value, "/"))
        elif isinstance(value, dict):
            entries.append((str(value.get("host", "")), str(value.get("path_prefix", "/"))))
    return tuple(entries)


def _authorized_oci_url(url: str, allowlist: tuple[tuple[str, str], ...]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and any(
        parsed.hostname == host and parsed.path.startswith(path_prefix) for host, path_prefix in allowlist
    )


def _registry_bearer_token(
    response: requests.Response,
    *,
    registry_host: str,
    credential: str | None,
) -> str:
    challenge = response.headers.get("WWW-Authenticate", "")
    match = re.fullmatch(r'Bearer\s+realm="([^"]+)",service="([^"]+)"(?:,scope="([^"]+)")?', challenge)
    if match is None:
        raise ValueError("registry authentication challenge is unsupported")
    realm, service, scope = match.groups()
    parsed = urlparse(realm)
    if parsed.scheme != "https" or parsed.hostname != registry_host:
        raise ValueError("registry authentication realm is not trusted")
    parameters = {"service": service}
    if scope:
        parameters["scope"] = scope
    authentication = tuple(credential.split(":", maxsplit=1)) if credential is not None and ":" in credential else None
    token_response = requests.get(
        f"{realm}?{urlencode(parameters)}",
        timeout=(15, 60),
        allow_redirects=False,
        auth=cast(tuple[str, str] | None, authentication),
    )
    token_response.raise_for_status()
    document = token_response.json()
    token = document.get("token") or document.get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("registry returned no anonymous bearer token")
    return token


def _download_oci_url(
    url: str,
    *,
    allowlist: tuple[tuple[str, str], ...],
    max_redirects: int,
    max_bytes: int,
    credential: str | None,
) -> tuple[bytes, tuple[RedirectHop, ...], str]:
    current = url
    bearer = credential if credential is not None and ":" not in credential else None
    hops: list[RedirectHop] = []
    registry_host = urlparse(url).hostname or ""
    for _attempt in range(max_redirects + 2):
        if not _authorized_oci_url(current, allowlist):
            raise ValueError(f"unauthorized OCI URL: {current}")
        headers = {"Accept": "application/vnd.oci.image.manifest.v1+json, application/octet-stream"}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        response = requests.get(current, headers=headers, timeout=(15, 60), allow_redirects=False, stream=True)
        if response.status_code == 401 and bearer is None:
            response.close()
            bearer = _registry_bearer_token(response, registry_host=registry_host, credential=credential)
            continue
        if response.status_code in {301, 302, 303, 307, 308}:
            destination = urljoin(current, response.headers.get("Location", ""))
            response.close()
            hops.append(RedirectHop(destination, False))
            if len(hops) > max_redirects or not _authorized_oci_url(destination, allowlist):
                raise ValueError(f"unauthorized OCI redirect: {destination}")
            current = destination
            bearer = None
            continue
        response.raise_for_status()
        payload = bytearray()
        for chunk in response.iter_content(1_048_576):
            payload.extend(chunk)
            if len(payload) > max_bytes:
                response.close()
                raise ValueError("OCI payload exceeds its signed bound")
        response.close()
        return bytes(payload), tuple(hops), current
    raise ValueError("OCI redirect/authentication bound exceeded")


def _cache_blob_path(cache_root: Path, digest: str) -> Path:
    algorithm, value = digest.split(":", maxsplit=1)
    return cache_root / "blobs" / algorithm / value


def _verified_cached_blob(cache_root: Path, digest: str, *, size: int | None = None) -> bytes | None:
    path = _cache_blob_path(cache_root, digest)
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    if (size is not None and len(payload) != size) or "sha256:" + hashlib.sha256(payload).hexdigest() != digest:
        return None
    return payload


def _publish_cached_blob(cache_root: Path, digest: str, payload: bytes) -> None:
    destination = _cache_blob_path(cache_root, digest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkstemp(prefix=".specfact-oci-", dir=destination.parent)[1])
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _oci_records(oci: dict[str, object]) -> tuple[tuple[str, int | None], ...]:
    manifest_digest = _descriptor_digest(oci.get("manifest"))
    raw_config = oci.get("config", {})
    config = raw_config if isinstance(raw_config, dict) else {}
    records: list[tuple[str, int | None]] = [(manifest_digest, cast(int | None, oci.get("manifest_size")))]
    records.append((_descriptor_digest(raw_config), cast(int | None, config.get("size"))))
    records.extend(
        (str(layer.get("digest", "")), cast(int | None, layer.get("size")))
        for layer in cast(list[dict[str, object]], oci.get("layers", []))
    )
    return tuple(records)


def _acquisition_context(
    oci: dict[str, object],
    *,
    cache_root: Path,
    simulate_cache_hit: bool,
    credential: str | None,
) -> _AcquisitionContext | AcquisitionResult:
    allowlist = _oci_allowlist(oci)
    records = _oci_records(oci)
    if not all(_valid_digest(digest) for digest, _size in records):
        return AcquisitionResult("UNKNOWN", reason="oci_digest_missing")
    locator = oci.get("locator")
    if not isinstance(locator, str):
        return AcquisitionResult(
            "PASS",
            "verified_cache" if simulate_cache_hit else "signed_registry",
            tuple(AcquisitionRecord(digest) for digest, _size in records),
        )
    bounds = cast(dict[str, object], oci.get("bounds", {}))
    return _AcquisitionContext(
        oci,
        cache_root,
        allowlist,
        records,
        locator,
        _positive_int(bounds.get("max_redirects"), default=4),
        _positive_int(bounds.get("max_layer_bytes"), default=1_073_741_824),
        simulate_cache_hit,
        credential,
    )


def _download_missing_oci_records(
    context: _AcquisitionContext,
) -> tuple[str, tuple[RedirectHop, ...], str]:
    source = "verified_cache"
    redirects: list[RedirectHop] = []
    final_url = ""
    for index, (digest, expected_size) in enumerate(context.records):
        if _verified_cached_blob(context.cache_root, digest, size=expected_size) is not None:
            continue
        if context.simulate_cache_hit:
            raise ValueError("verified cache entry is missing")
        source = "signed_registry"
        url = context.locator if index == 0 else _oci_blob_url(context.oci, digest)
        payload, observed_redirects, final_url = _download_oci_url(
            url,
            allowlist=context.allowlist,
            max_redirects=context.max_redirects,
            max_bytes=context.max_layer_bytes,
            credential=context.credential,
        )
        _validate_oci_payload(payload, digest=digest, expected_size=expected_size)
        _publish_cached_blob(context.cache_root, digest, payload)
        redirects.extend(observed_redirects)
    return source, tuple(redirects), final_url


def _oci_blob_url(oci: dict[str, object], digest: str) -> str:
    return f"{str(oci['registry']).rstrip('/')}/v2/{oci['repository']}/blobs/{digest}"


def _validate_oci_payload(payload: bytes, *, digest: str, expected_size: int | None) -> None:
    actual_digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (expected_size is not None and len(payload) != expected_size) or actual_digest != digest:
        raise ValueError("OCI descriptor size or digest mismatch")


def acquire_oci_distribution(
    oci: dict[str, object],
    *,
    cache_root: Path,
    simulate_cache_hit: bool = False,
    redirect_chain: list[str] | None = None,
    credential: str | None = None,
) -> AcquisitionResult:
    allowlist = _oci_allowlist(oci)
    unauthorized = tuple(
        RedirectHop(url, False) for url in redirect_chain or [] if not _authorized_oci_url(url, allowlist)
    )
    if unauthorized:
        return AcquisitionResult("UNKNOWN", unauthorized_hops=unauthorized, reason="unauthorized_redirect")
    context = _acquisition_context(
        oci,
        cache_root=cache_root,
        simulate_cache_hit=simulate_cache_hit,
        credential=credential,
    )
    if isinstance(context, AcquisitionResult):
        return context
    try:
        source, redirects, final_url = _download_missing_oci_records(context)
    except (OSError, requests.RequestException, ValueError) as exc:
        return AcquisitionResult("UNKNOWN", reason=f"oci_acquisition_failed:{exc}")
    return AcquisitionResult(
        "PASS",
        source,
        tuple(AcquisitionRecord(digest) for digest, _size in context.records),
        redirect_chain=redirects,
        final_url=final_url,
    )


def validate_checkpoint_projection(lock: dict[str, object], checkpoint_digest: str) -> ToolchainValidation:
    projection = {key: value for key, value in lock.items() if key != "projection_digest"}
    if canonical_json_digest(projection) != checkpoint_digest:
        return ToolchainValidation("UNKNOWN", "checkpoint_projection_mismatch")
    return ToolchainValidation("PASS")


def _read_stable_regular(path: Path, *, max_bytes: int = 1_048_576) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise ValueError("identity record is not a bounded regular file")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(descriptor, min(65_536, max_bytes + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("identity record exceeds its size bound")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("identity record changed during read")
    return b"".join(chunks)


def _canonical_install_relative(package_dir: Path, root: Path) -> Path:
    absolute_root = root.absolute()
    absolute_package = package_dir.absolute()
    relative = absolute_package.relative_to(absolute_root)
    if not relative.parts:
        raise ValueError("module install root cannot be the module package")
    current = absolute_root
    for part in relative.parts:
        current /= part
        metadata = current.lstat()
        if current.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("module install path is not a real directory tree")
    return relative


def _metadata_payload(metadata: object) -> object:
    model_dump = getattr(metadata, "model_dump", None)
    if callable(model_dump):
        return cast(object, model_dump(mode="json"))
    return {
        "name": str(getattr(metadata, "name", "")),
        "version": str(getattr(metadata, "version", "")),
    }


def derive_core_0_55_1_install_handoff(
    discovered: object,
    *,
    expected_registry_id: str,
    user_modules_root: Path,
    marketplace_modules_root: Path,
    public_key_path: Path | None = None,
) -> CoreInstalledModuleHandoff:
    """Derive C14 provenance from the install records exposed by exact core v0.55.1."""
    try:
        from specfact_cli.registry import module_installer

        package_dir = Path(cast(Path, discovered.package_dir))
        metadata = discovered.metadata
        source = str(discovered.source)
        roots = {"user": user_modules_root, "marketplace": marketplace_modules_root}
        if source not in roots:
            raise ValueError("unsupported core discovery source")
        relative = _canonical_install_relative(package_dir, roots[source])
        registry_id = _read_stable_regular(package_dir / ".specfact-registry-id").decode("utf-8").strip()
        install_checksum = (
            _read_stable_regular(package_dir / ".specfact-install-verified-checksum").decode("utf-8").strip()
        )
        integrity = getattr(metadata, "integrity", None)
        package_checksum = str(getattr(integrity, "checksum", ""))
        package_signature = str(getattr(integrity, "signature", "") or "")
        module_name = str(getattr(metadata, "name", ""))
        module_version = str(getattr(metadata, "version", ""))
        publisher = getattr(metadata, "publisher", None)
        if (
            registry_id != expected_registry_id
            or module_name != expected_registry_id
            or not module_version
            or str(getattr(publisher, "name", "")) != "nold-ai"
            or install_checksum != package_checksum
            or not _valid_digest(package_checksum)
            or not package_signature
        ):
            raise ValueError("core install records do not identify an approved signed module")
        selected_key = public_key_path or module_installer._bundled_public_key_path()
        public_key_pem = _read_stable_regular(Path(selected_key)).decode("utf-8")
        key_fingerprint = "sha256:" + hashlib.sha256(public_key_pem.encode("utf-8")).hexdigest()
        verified = bool(
            module_installer.verify_module_artifact(
                package_dir,
                metadata,
                allow_unsigned=False,
                require_integrity=True,
                require_signature=True,
                public_key_pem=public_key_pem,
            )
        )
        if not verified:
            raise ValueError("core artifact verification failed")
        root_descriptor = canonical_json_digest(
            {
                "install_root_class": source,
                "mode": stat.S_IMODE(package_dir.lstat().st_mode),
                "registry_id": registry_id,
                "relative_path": relative.as_posix(),
            }
        )
        identity = CoreInstalledModuleIdentity(
            "core-v0.55.1-installed-module-handoff-v1",
            source,
            root_descriptor,
            canonical_json_digest(_metadata_payload(metadata)),
            module_name,
            module_version,
            package_checksum,
            package_signature,
            key_fingerprint,
            source,
            registry_id,
            install_checksum,
            verified,
            str(package_dir),
            root_descriptor,
        )
    except (AttributeError, ImportError, OSError, TypeError, UnicodeDecodeError, ValueError):
        return CoreInstalledModuleHandoff("UNKNOWN", "invalid_core_0_55_1_install_handoff")
    return CoreInstalledModuleHandoff("PASS", identity=identity)


def verify_candidate_module_payload(metadata: dict[str, object]) -> CandidateModulePayload:
    """Bind protected pre-release evidence without granting released provenance."""
    required_text = (
        "repository",
        "workflow",
        "workflow_ref",
        "run_id",
        "run_attempt",
        "job",
    )
    commit_sha = str(metadata.get("commit_sha", ""))
    tree_sha = str(metadata.get("tree_sha", ""))
    if (
        any(not str(metadata.get(field, "")).strip() for field in required_text)
        or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None
        or re.fullmatch(r"[0-9a-f]{40}", tree_sha) is None
        or not _valid_digest(metadata.get("module_package_digest"))
        or not _valid_digest(metadata.get("payload_manifest_digest"))
    ):
        return CandidateModulePayload("UNKNOWN", "invalid_candidate_module_identity")
    projection = {field: str(metadata[field]) for field in sorted(metadata)}
    identity = CandidateModuleIdentity("verified-candidate-module-payload-v1", canonical_json_digest(projection))
    return CandidateModulePayload("PASS", identity=identity)


def _payload_identity(metadata: dict[str, object] | CoreInstalledModuleHandoff) -> InstalledModuleIdentity:
    if isinstance(metadata, CoreInstalledModuleHandoff):
        if metadata.status != "PASS" or metadata.identity is None:
            return InstalledModuleIdentity("", "", "", "", "", "", "")
        source = metadata.identity
        return InstalledModuleIdentity(
            source.module_name,
            source.module_version,
            source.package_checksum,
            source.package_signature,
            source.approved_key_fingerprint,
            f"official-{source.install_root_class}",
            source.installed_root,
            source.derivation_schema,
            source.discovered_source,
            source.install_root_class,
            source.registry_id,
            source.install_verified_checksum,
            source.artifact_verification_result,
        )
    return InstalledModuleIdentity(
        str(metadata.get("module_name", "")),
        str(metadata.get("version", "")),
        str(metadata.get("checksum", "")),
        str(metadata.get("signature", "")),
        str(metadata.get("key_fingerprint", "")),
        str(metadata.get("loader_origin", "")),
        str(metadata.get("installed_root", "")),
    )


def _trusted_payload_identity(identity: InstalledModuleIdentity) -> bool:
    return not (
        identity.loader_origin not in {"official-marketplace", "official-user"}
        or not _valid_digest(identity.checksum)
        or not _valid_digest(identity.key_fingerprint)
        or identity.signature in {"", "untrusted"}
        or (identity.derivation_schema and not identity.artifact_verification_result)
    )


def _stable_payload_bytes(path: Path) -> tuple[bytes, int]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1_048_576):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if not stat.S_ISREG(before.st_mode) or not stable:
        raise ValueError("payload changed during verification")
    return b"".join(chunks), before.st_mode


def _installed_payload_manifest(identity: InstalledModuleIdentity) -> tuple[PayloadEntry, ...]:
    installed_root = Path(identity.installed_root)
    root = installed_root / "specfact_code_review"
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("payload root is not a real directory")
    paths = sorted(root.rglob("*"), key=lambda item: item.relative_to(installed_root).as_posix())
    if not paths:
        raise ValueError("payload is empty")
    manifest: list[PayloadEntry] = []
    for path in paths:
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode) and not path.is_symlink():
            continue
        if not stat.S_ISREG(mode) or path.is_symlink():
            raise ValueError("payload contains a non-regular entry")
        file_bytes, _mode = _stable_payload_bytes(path)
        relative = path.relative_to(installed_root).as_posix()
        digest = "sha256:" + hashlib.sha256(file_bytes).hexdigest()
        manifest.append(PayloadEntry(relative, digest))
    return tuple(manifest)


def _legacy_payload_checksum(manifest: tuple[PayloadEntry, ...]) -> str:
    payload_lines = [f"{entry.path}:{entry.digest[7:]}" for entry in manifest]
    return "sha256:" + hashlib.sha256("\n".join(payload_lines).encode()).hexdigest()


def verify_installed_module_payload(metadata: dict[str, object] | CoreInstalledModuleHandoff) -> InstalledPayload:
    identity = _payload_identity(metadata)
    if not _trusted_payload_identity(identity):
        return InstalledPayload("UNKNOWN", "untrusted_installed_module", identity)
    try:
        manifest = _installed_payload_manifest(identity)
        if not identity.derivation_schema and _legacy_payload_checksum(manifest) != identity.checksum:
            raise ValueError("payload checksum mismatch")
    except (OSError, ValueError):
        return InstalledPayload("UNKNOWN", "installed_payload_drift", identity)
    return InstalledPayload("PASS", identity=identity, manifest=manifest)


def _copy_builtin_entry(
    identity: InstalledModuleIdentity,
    entry: PayloadEntry,
    temporary: Path,
) -> None:
    relative = Path(entry.path)
    if relative.parts[:1] != ("specfact_code_review",) or ".." in relative.parts:
        raise ValueError("built-in payload manifest path is unsafe")
    file_bytes, source_mode = _stable_payload_bytes(Path(identity.installed_root) / relative)
    if "sha256:" + hashlib.sha256(file_bytes).hexdigest() != entry.digest:
        raise ValueError("built-in payload changed before copy")
    copied = temporary.joinpath(*relative.parts[1:])
    copied.parent.mkdir(parents=True, exist_ok=True)
    copied.write_bytes(file_bytes)
    copied.chmod(stat.S_IMODE(source_mode))
    if "sha256:" + hashlib.sha256(copied.read_bytes()).hexdigest() != entry.digest:
        raise ValueError("built-in payload changed during copy")


def install_builtin_payload(payload: InstalledPayload, *, capsule_root: Path) -> BuiltinPayload:
    if payload.status != "PASS" or payload.identity is None:
        return BuiltinPayload("UNKNOWN", "", (), reason="unverified_payload")
    destination = capsule_root / "opt/specfact/builtin/specfact_code_review"
    temporary = capsule_root / "opt/specfact/builtin/.specfact_code_review.copying"
    try:
        if destination.exists() or destination.is_symlink() or temporary.exists() or temporary.is_symlink():
            raise ValueError("built-in payload destination collides")
        temporary.mkdir(parents=True)
        for entry in payload.manifest:
            _copy_builtin_entry(payload.identity, entry, temporary)
        os.replace(temporary, destination)
    except (OSError, ValueError):
        shutil.rmtree(temporary, ignore_errors=True)
        return BuiltinPayload("UNKNOWN", "", (), reason="builtin_payload_copy_failed")
    return BuiltinPayload(
        "PASS",
        "/opt/specfact/builtin/specfact_code_review",
        ("/opt/specfact/builtin",),
    )


def _sealed_bootstrap_source(module_payload_manifest_digest: str) -> bytes:
    source = f'''"""C14 sealed analyzer bootstrap; generated from checkpointed schema."""
from __future__ import annotations

import runpy
import sys

ANALYZER_ROOT = "/opt/specfact/analyzers"
BUILTIN_ROOT = "/opt/specfact/builtin"
MODULE_PAYLOAD_MANIFEST_DIGEST = "{module_payload_manifest_digest}"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("missing sealed analyzer module")
    module = sys.argv.pop(1)
    sys.path[:0] = [ANALYZER_ROOT, BUILTIN_ROOT]
    runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
'''
    return source.encode("utf-8")


def compose_post_base_capsule(
    payload: InstalledPayload,
    *,
    capsule_root: Path,
    immutable_base_root_digest: str,
    analyzer_installed_set_digest: str,
    native_launcher_digest: str,
    project_runtime_identity: str,
) -> CapsuleComposition:
    """Copy verified module code and bind the generated post-base capsule composition."""
    if (
        not _valid_digest(immutable_base_root_digest)
        or not _valid_digest(analyzer_installed_set_digest)
        or not _valid_digest(native_launcher_digest)
        or not project_runtime_identity
    ):
        return CapsuleComposition("UNKNOWN", "invalid_capsule_composition_identity")
    installed = install_builtin_payload(payload, capsule_root=capsule_root)
    if installed.status != "PASS":
        return CapsuleComposition("UNKNOWN", installed.reason)
    payload_projection = [{"digest": entry.digest, "path": entry.path} for entry in payload.manifest]
    module_payload_manifest_digest = canonical_json_digest(payload_projection)
    bootstrap_bytes = _sealed_bootstrap_source(module_payload_manifest_digest)
    bootstrap = capsule_root / "opt/specfact/bootstrap/sealed_bootstrap.py"
    temporary = bootstrap.with_name(".sealed_bootstrap.py.copying")
    try:
        bootstrap.parent.mkdir(parents=True, exist_ok=True)
        if bootstrap.exists() or bootstrap.is_symlink() or temporary.exists() or temporary.is_symlink():
            raise ValueError("sealed bootstrap destination collides")
        temporary.write_bytes(bootstrap_bytes)
        temporary.chmod(0o444)
        if _read_stable_regular(temporary) != bootstrap_bytes:
            raise ValueError("sealed bootstrap changed during generation")
        os.replace(temporary, bootstrap)
        bootstrap_digest = "sha256:" + hashlib.sha256(_read_stable_regular(bootstrap)).hexdigest()
        root_entries, _regular_file_bytes = _manifest_entries(capsule_root, include_root=False)
        final_root_digest = canonical_json_digest(root_entries)
        composite_projection = {
            "analyzer_installed_set_digest": analyzer_installed_set_digest,
            "bootstrap_content_digest": bootstrap_digest,
            "bootstrap_schema": "sealed-bootstrap-v2",
            "bootstrap_source_digest": bootstrap_digest,
            "final_composite_root_manifest_digest": final_root_digest,
            "immutable_base_root_digest": immutable_base_root_digest,
            "module_payload_manifest_digest": module_payload_manifest_digest,
            "native_launcher_digest": native_launcher_digest,
            "project_runtime_identity": project_runtime_identity,
            "schema": "capsule-composite-identity-v1",
        }
        composite_digest = canonical_json_digest(composite_projection)
    except (OSError, ValueError):
        temporary.unlink(missing_ok=True)
        return CapsuleComposition("UNKNOWN", "capsule_composition_failed")
    return CapsuleComposition(
        "PASS",
        bootstrap_schema="sealed-bootstrap-v2",
        composite_schema="capsule-composite-identity-v1",
        immutable_base_root_digest=immutable_base_root_digest,
        module_payload_manifest_digest=module_payload_manifest_digest,
        bootstrap_digest=bootstrap_digest,
        composite_identity_digest=composite_digest,
        final_composite_root_manifest_digest=final_root_digest,
    )


def validate_source_lock_transition(*, target_tip: dict[str, str], candidate: dict[str, str]) -> ToolchainValidation:
    if target_tip != candidate:
        return ToolchainValidation("UNKNOWN", "candidate_project_dependency_input_change")
    return ToolchainValidation("PASS")


def compose_pytest_catalog(descriptor: dict[str, object]) -> PytestCatalog:
    plugins = cast(list[dict[str, object]], descriptor.get("pytest_plugins", []))
    options = tuple(
        sorted({str(value) for plugin in plugins for value in cast(list[object], plugin.get("options", []))})
    )
    fields = tuple(
        sorted({str(value) for plugin in plugins for value in cast(list[object], plugin.get("ini_fields", []))})
    )
    return PytestCatalog(options, fields, canonical_json_digest({"options": options, "ini_fields": fields}))


def _project_runtime_parts(descriptor: dict[str, object]) -> _ProjectRuntimeParts | None:
    required_top_level = {
        "schema",
        "target",
        "source_lock_paths",
        "distributions",
        "native_components",
        "oci",
        "build",
        "attestation",
        "root_manifest",
    }
    allowed_top_level = required_top_level | {"pytest_plugins"}
    if set(descriptor) - allowed_top_level or not required_top_level <= set(descriptor):
        return None
    mapping_fields = ("target", "oci", "build", "attestation", "root_manifest")
    sequence_fields = ("source_lock_paths", "distributions", "pytest_plugins")
    if not all(isinstance(descriptor.get(field), dict) for field in mapping_fields):
        return None
    if not all(isinstance(descriptor.get(field, []), list) for field in sequence_fields):
        return None
    sequences = [cast(list[object], descriptor.get(field, [])) for field in sequence_fields]
    if not all(all(isinstance(item, dict) for item in sequence) for sequence in sequences):
        return None
    return _ProjectRuntimeParts(
        cast(dict[str, object], descriptor["target"]),
        cast(list[dict[str, object]], descriptor["source_lock_paths"]),
        cast(list[dict[str, object]], descriptor["distributions"]),
        cast(list[dict[str, object]], descriptor.get("pytest_plugins", [])),
        cast(dict[str, object], descriptor["oci"]),
        cast(dict[str, object], descriptor["build"]),
        cast(dict[str, object], descriptor["attestation"]),
        cast(dict[str, object], descriptor["root_manifest"]),
    )


def _valid_runtime_target(target: dict[str, object], expected_target: str) -> bool:
    repository = target.get("repository")
    return (
        target.get("commit_sha") == expected_target
        and _full_sha(target.get("tree_sha"))
        and isinstance(repository, str)
        and bool(repository)
    )


def _valid_source_locks(source_locks: list[dict[str, object]]) -> bool:
    source_paths = [str(item.get("path", "")) for item in source_locks]
    if source_paths != sorted(set(source_paths)):
        return False
    for path, item in zip(source_paths, source_locks, strict=True):
        if not path or Path(path).is_absolute() or ".." in Path(path).parts:
            return False
        if not _full_sha(item.get("blob_sha")) or not _valid_digest(item.get("content_sha256")):
            return False
    return True


def _runtime_distribution_names(distributions: list[dict[str, object]]) -> list[str]:
    return [re.sub(r"[-_.]+", "-", str(item.get("name", ""))).lower() for item in distributions]


def _valid_runtime_distributions(distributions: list[dict[str, object]]) -> bool:
    names = _runtime_distribution_names(distributions)
    return names == sorted(set(names)) and all(_valid_distribution(item) for item in distributions)


def _valid_project_runtime_oci(oci: dict[str, object]) -> bool:
    registry = oci.get("registry")
    repository = oci.get("repository")
    if not isinstance(registry, str) or not registry.startswith("https://"):
        return False
    if not isinstance(repository, str) or not repository:
        return False
    return (
        _valid_digest(oci.get("manifest_digest"))
        and _valid_digest(oci.get("config_digest"))
        and _valid_oci_layers(oci.get("layers"))
    )


def _valid_runtime_provenance(build: dict[str, object], attestation: dict[str, object]) -> bool:
    required_build = {"workflow", "ref", "run_id", "run_attempt", "artifact_id", "artifact_digest"}
    required_attestation = {"predicate_type", "subject_digest", "builder_identity", "signature"}
    if not required_build <= set(build) or not _valid_digest(build.get("artifact_digest")):
        return False
    if not required_attestation <= set(attestation) or not _valid_digest(attestation.get("subject_digest")):
        return False
    return all(isinstance(attestation.get(key), str) and bool(attestation[key]) for key in required_attestation)


def _valid_project_runtime_parts(parts: _ProjectRuntimeParts, *, expected_target: str) -> bool:
    return all(
        (
            _valid_runtime_target(parts.target, expected_target),
            _valid_source_locks(parts.source_locks),
            _valid_runtime_distributions(parts.distributions),
            _valid_project_runtime_oci(parts.oci),
            _valid_runtime_provenance(parts.build, parts.attestation),
            _valid_root_manifest(parts.root_manifest),
            all(_valid_pytest_plugin(plugin, parts.distributions) for plugin in parts.plugins),
        )
    )


def validate_project_runtime_layer(descriptor: dict[str, object], *, expected_target: str) -> ProjectRuntimeLayer:
    parts = _project_runtime_parts(descriptor)
    if (
        descriptor.get("schema") != "project-runtime-layer-v1"
        or parts is None
        or not _valid_project_runtime_parts(parts, expected_target=expected_target)
    ):
        return ProjectRuntimeLayer("UNKNOWN", "project_runtime_identity_mismatch")
    reserved = {"specfact-code-review", "pytest", "sitecustomize"}
    if reserved & set(_runtime_distribution_names(parts.distributions)):
        return ProjectRuntimeLayer("UNKNOWN", "reserved_import_collision")
    plugin_models = tuple(
        PytestPluginIdentity(
            str(plugin.get("distribution", "")),
            str(plugin.get("version", "")),
            str(plugin.get("pytest11_entry_point", "")),
        )
        for plugin in parts.plugins
    )
    source_lock_digest = canonical_json_digest(parts.source_locks)
    identity = canonical_json_digest(descriptor)
    return ProjectRuntimeLayer(
        "PASS",
        target_commit=expected_target,
        source_lock_digest=source_lock_digest,
        identity=identity,
        pytest_plugins=plugin_models,
    )


def _full_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def _valid_distribution(value: dict[str, object]) -> bool:
    return (
        isinstance(value.get("name"), str)
        and bool(value["name"])
        and isinstance(value.get("version"), str)
        and bool(value["version"])
        and _valid_digest(value.get("payload_digest"))
        and isinstance(value.get("dependencies"), list)
        and isinstance(value.get("entry_points"), list)
    )


def _valid_oci_layers(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            isinstance(item, dict)
            and _valid_digest(item.get("digest"))
            and _valid_digest(item.get("diff_id"))
            and isinstance(item.get("size"), int)
            and cast(int, item["size"]) > 0
            for item in value
        )
    )


def _valid_root_manifest(value: dict[str, object]) -> bool:
    return (
        isinstance(value.get("algorithm"), str)
        and bool(value["algorithm"])
        and _valid_digest(value.get("digest"))
        and value.get("python_abi") in {"cp311", "cp312", "cp313"}
        and value.get("platform_tag") == "linux-x86_64"
        and value.get("site_packages") == "/opt/specfact/project-runtime/site-packages"
    )


def _valid_pytest_plugin(plugin: dict[str, object], distributions: list[dict[str, object]]) -> bool:
    matching = [
        item
        for item in distributions
        if re.sub(r"[-_.]+", "-", str(item.get("name", ""))).lower()
        == re.sub(r"[-_.]+", "-", str(plugin.get("distribution", ""))).lower()
    ]
    return (
        len(matching) == 1
        and plugin.get("version") == matching[0].get("version")
        and plugin.get("payload_digest") == matching[0].get("payload_digest")
        and isinstance(plugin.get("dependencies"), list)
        and isinstance(plugin.get("pytest11_entry_point"), str)
        and bool(plugin["pytest11_entry_point"])
        and _valid_digest(plugin.get("parser_catalog_digest"))
        and _valid_digest(plugin.get("hook_capability_digest"))
    )


def bind_project_runtime_to_snapshots(
    layer: ProjectRuntimeLayer, *, snapshots: tuple[str, ...]
) -> dict[str, ProjectRuntimeLayer]:
    return dict.fromkeys(snapshots, layer)


def require_project_runtime(*, member: str, descriptor: dict[str, object] | None) -> ToolchainValidation:
    del member
    if descriptor is None:
        return ToolchainValidation("UNKNOWN", "project_runtime_required")
    return ToolchainValidation("PASS")


def authorize_project_runtime_mount(*, member: str, descriptor: dict[str, object]) -> ToolchainValidation:
    del descriptor
    admitted = {
        "basedpyright",
        "contracts",
        "pylint",
        "targeted-pytest-coverage",
        "targeted-pytest-plugin-preflight",
    }
    if member not in admitted:
        return ToolchainValidation("UNKNOWN", "project_runtime_member_unsupported")
    return ToolchainValidation("PASS")


def import_search_order(*, member: str, snapshot_root: str, project_root: str) -> tuple[str, str, str]:
    if authorize_project_runtime_mount(member=member, descriptor={}).status != "PASS":
        raise ValueError("member cannot import from project runtime")
    return ("capsule-reserved-finder", snapshot_root, project_root)


def normalized_requirement_name(requirement: str) -> str:
    return Requirement(requirement).name.lower().replace("_", "-")
