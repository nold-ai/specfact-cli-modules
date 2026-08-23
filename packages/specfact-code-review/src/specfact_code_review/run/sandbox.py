"""Closed snapshot invocation and operating-system isolation boundary."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from icontract import ensure, require


ScopeStatus = Literal["PASS", "UNKNOWN"]
_DEFAULT_RESERVED_IMPORT_PREFIXES = ("pytest", "sitecustomize", "specfact_code_review")
_PROJECT_RUNTIME_MEMBERS = frozenset(
    {
        "basedpyright",
        "contracts",
        "pylint",
        "targeted-pytest-coverage",
        "targeted-pytest-plugin-preflight",
    }
)


def _canonical_digest(values: object) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


@dataclass(frozen=True)
class SnapshotInvocationContext:
    """All immutable roots and launch identities for one analyzer side."""

    member: str
    snapshot_root: Path
    config_roots: tuple[Path, ...]
    output_root: Path
    temporary_root: Path
    capsule_root: Path
    interpreter: str
    bootstrap: str
    project_runtime_root: Path | None
    network: Literal["none"]
    control_root: Path | None
    environment_id: str = ""
    reserved_import_prefixes: tuple[str, ...] = _DEFAULT_RESERVED_IMPORT_PREFIXES

    @property
    def digest(self) -> str:
        return _canonical_digest(
            {
                "bootstrap": self.bootstrap,
                "capsule_root": str(self.capsule_root),
                "config_roots": [str(path) for path in self.config_roots],
                "control_root": None if self.control_root is None else str(self.control_root),
                "interpreter": self.interpreter,
                "environment_id": self.environment_id,
                "member": self.member,
                "network": self.network,
                "output_root": str(self.output_root),
                "project_runtime_root": (None if self.project_runtime_root is None else str(self.project_runtime_root)),
                "reserved_import_prefixes": sorted(set(self.reserved_import_prefixes)),
                "snapshot_root": str(self.snapshot_root),
                "temporary_root": str(self.temporary_root),
            }
        )

    @require(lambda roots: all(root.is_absolute() for root in roots), "config roots must be absolute")
    @ensure(lambda self, result: result.member == self.member)
    def with_config_roots(self, roots: tuple[Path, ...]) -> SnapshotInvocationContext:
        return replace(self, config_roots=roots)


@dataclass(frozen=True)
class SandboxMount:
    """One declared source-to-capsule mount."""

    name: str
    role: str
    source: Path
    destination: str
    read_only: bool


@dataclass(frozen=True)
class SandboxLaunchPlan:
    """Canonical launch data consumed by the Linux isolation backend."""

    context_digest: str
    cwd: str
    argv: tuple[str, ...]
    startup_sys_path: tuple[Path, ...]
    root_mode: str
    root_source: str
    network: Literal["none"]
    capabilities: tuple[str, ...]
    writable_roots: tuple[str, ...]
    mounts: tuple[SandboxMount, ...]
    host_runtime_mounts: tuple[Path, ...] = ()

    def mount_for(self, name: str) -> SandboxMount:
        try:
            return next(mount for mount in self.mounts if mount.name == name)
        except StopIteration as exc:
            raise KeyError(name) from exc


@dataclass(frozen=True)
class PreflightResult:
    """Reserved-import preflight outcome."""

    status: ScopeStatus
    reason: str = ""
    collisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class BubblewrapIdentity:
    """Signed identity of the one admitted native namespace launcher."""

    path: str
    format: str
    architecture: str
    linkage: str
    interpreter: tuple[str, ...]
    needed: tuple[str, ...]
    sha256: str
    descriptor_digest: str


@dataclass(frozen=True)
class IsolationValidation:
    """Closed validation outcome for one isolation primitive."""

    status: ScopeStatus
    reason: str = ""
    host_loader_objects: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeObservationScope:
    """Explicit trust limit for runtime observer evidence."""

    adversarial_candidate_resistance: bool
    limitation: str
    status_on_policy_uncertainty: Literal["UNKNOWN"]


@dataclass(frozen=True)
class SandboxExecution:
    """OS-observed result from one fresh isolated analyzer process."""

    status: ScopeStatus
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    reason: str = ""


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def validate_bubblewrap(identity: BubblewrapIdentity) -> IsolationValidation:
    """Require the canonical static Linux x86_64 Bubblewrap descriptor."""

    expected = {
        "path": "/opt/specfact/bin/bwrap-static",
        "architecture": "x86_64",
    }
    actual = {
        "path": identity.path,
        "architecture": identity.architecture,
    }
    digest_fields_valid = all(
        value.startswith("sha256:") and len(value) == 71 for value in (identity.sha256, identity.descriptor_digest)
    )
    admitted_format = identity.format in {"ELF", "ELF64"}
    admitted_linkage = identity.linkage in {"static", "static-pie"}
    if (
        actual != expected
        or not admitted_format
        or not admitted_linkage
        or identity.interpreter
        or identity.needed
        or not digest_fields_valid
    ):
        return IsolationValidation("UNKNOWN", "bubblewrap_identity_mismatch")
    return IsolationValidation("PASS")


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def validate_pre_namespace_objects(objects: tuple[dict[str, str], ...]) -> IsolationValidation:
    """Reject user-space loader mappings before the namespace boundary exists."""

    admitted_kinds = {"static_executable", "kernel_object"}
    host_objects = tuple(item.get("path", "") for item in objects if item.get("kind", "") not in admitted_kinds)
    if host_objects:
        return IsolationValidation("UNKNOWN", "pre_namespace_host_object", host_objects)
    return IsolationValidation("PASS")


def runtime_observation_scope(context: SnapshotInvocationContext) -> RuntimeObservationScope:
    """Declare that runtime observation does not resist hostile candidate Python."""

    return RuntimeObservationScope(
        adversarial_candidate_resistance=False,
        limitation=(
            f"{context.member} runtime evidence assumes candidate Python does not actively forge "
            "or evade controller observations."
        ),
        status_on_policy_uncertainty="UNKNOWN",
    )


def _mounts(context: SnapshotInvocationContext) -> tuple[SandboxMount, ...]:
    mounts = [
        *(
            SandboxMount(
                "policy" if index == 0 else f"policy-{index}",
                "config",
                root,
                f"/opt/specfact/config/{index}",
                True,
            )
            for index, root in enumerate(context.config_roots)
        ),
        SandboxMount("output", "output", context.output_root, "/opt/specfact/output", False),
        SandboxMount("temporary", "temporary", context.temporary_root, "/opt/specfact/tmp", False),
    ]
    if context.member != "targeted-pytest-plugin-preflight":
        mounts.insert(0, SandboxMount("snapshot", "snapshot", context.snapshot_root, "/opt/specfact/snapshot", True))
    if context.member == "radon":
        control_root = context.control_root
        if (
            control_root is None
            or control_root.is_symlink()
            or not control_root.exists()
            or not control_root.is_dir()
            or any(control_root.iterdir())
        ):
            raise ValueError("Radon control root must be an empty real directory")
        mounts.append(SandboxMount("control", "control", control_root, "/opt/specfact/control", True))
    if context.project_runtime_root is not None and context.member in _PROJECT_RUNTIME_MEMBERS:
        mounts.append(
            SandboxMount(
                "project-runtime",
                "project-runtime",
                context.project_runtime_root,
                "/opt/specfact/project-runtime",
                True,
            )
        )
    return tuple(mounts)


@require(lambda context: context.network == "none", "initial profile forbids network")
@ensure(lambda result: result.capabilities == ())
def build_launch_plan(context: SnapshotInvocationContext) -> SandboxLaunchPlan:
    """Build isolated Python bootstrap launch data without importing snapshot code."""

    cwd = (
        "/opt/specfact/control"
        if context.member == "radon"
        else "/opt/specfact/tmp"
        if context.member == "targeted-pytest-plugin-preflight"
        else "/opt/specfact/snapshot"
    )
    return SandboxLaunchPlan(
        context_digest=context.digest,
        cwd=cwd,
        argv=(context.interpreter, "-I", "-S", context.bootstrap),
        startup_sys_path=(context.capsule_root,),
        root_mode="empty-bwrap-root",
        root_source="verified-capsule-root",
        network=context.network,
        capabilities=(),
        writable_roots=("/opt/specfact/output", "/opt/specfact/tmp"),
        mounts=_mounts(context),
    )


def _verified_bubblewrap_descriptor(capsule_root: Path, identity: BubblewrapIdentity) -> int:
    executable = capsule_root / identity.path.lstrip("/")
    descriptor = os.open(
        executable,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1_048_576):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) == (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_mode,
        )
        digest = "sha256:" + hashlib.sha256(b"".join(chunks)).hexdigest()
        if not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111 or not stable or digest != identity.sha256:
            raise ValueError("bubblewrap descriptor identity mismatch")
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _bubblewrap_command(
    descriptor: int,
    plan: SandboxLaunchPlan,
    *,
    extra_argv: tuple[str, ...],
) -> list[str]:
    command = [
        f"/proc/self/fd/{descriptor}",
        "--unshare-all",
        "--cap-drop",
        "ALL",
        "--die-with-parent",
        "--new-session",
        "--ro-bind",
        str(plan.startup_sys_path[0]),
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
    ]
    for mount in plan.mounts:
        command.extend(("--dir", mount.destination))
        command.extend(("--ro-bind" if mount.read_only else "--bind", str(mount.source), mount.destination))
    command.extend(
        (
            "--clearenv",
            "--setenv",
            "PATH",
            "/opt/specfact/analyzers/bin:/opt/specfact/python/bin",
            "--setenv",
            "PYTHONHOME",
            "/opt/specfact/python",
            "--setenv",
            "PYTHONNOUSERSITE",
            "1",
            "--setenv",
            "HOME",
            "/opt/specfact/tmp",
            "--chdir",
            plan.cwd,
            *plan.argv,
            *extra_argv,
        )
    )
    return command


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def execute_launch_plan(
    plan: SandboxLaunchPlan,
    identity: BubblewrapIdentity,
    *,
    extra_argv: tuple[str, ...],
    timeout: int = 300,
) -> SandboxExecution:
    """Execute one analyzer with the verified static launcher and no host fallback."""

    if validate_bubblewrap(identity).status != "PASS" or not plan.startup_sys_path:
        return SandboxExecution("UNKNOWN", reason="bubblewrap_identity_mismatch")
    descriptor: int | None = None
    try:
        descriptor = _verified_bubblewrap_descriptor(plan.startup_sys_path[0], identity)
        command = _bubblewrap_command(descriptor, plan, extra_argv=extra_argv)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env={},
            pass_fds=(descriptor,),
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return SandboxExecution("UNKNOWN", reason=f"sandbox_launch_failed:{exc}")
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if completed.returncode != 0:
        return SandboxExecution(
            "UNKNOWN",
            completed.returncode,
            completed.stdout,
            completed.stderr,
            "analyzer_process_error",
        )
    return SandboxExecution("PASS", completed.returncode, completed.stdout, completed.stderr)


def _reserved_collision_paths(root: Path, prefixes: frozenset[str]) -> tuple[str, ...]:
    collisions: list[str] = []
    for prefix in sorted(prefixes):
        candidates = (root / f"{prefix}.py", root / f"{prefix}.pyi", root / prefix)
        if any(candidate.exists() or candidate.is_symlink() for candidate in candidates):
            collisions.append(prefix)
    return tuple(collisions)


def _signed_reserved_import_prefixes(environment_id: str) -> frozenset[str]:
    schema_path = Path(__file__).parents[1] / "resources/contracts/project-runtime-layer-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    catalog = schema["reserved_component_catalog"]
    if environment_id:
        environments = catalog["prefixes_by_environment"]
        selected = next(item for item in environments if item["environment_id"] == environment_id)
        values = selected["prefixes"]
    else:
        values = catalog["prefixes"]
    if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
        raise ValueError("reserved import catalog is invalid")
    return frozenset(values)


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def preflight_reserved_imports(context: SnapshotInvocationContext) -> PreflightResult:
    """Reject top-level module, stub, package, or namespace-package collisions."""

    try:
        prefixes = _signed_reserved_import_prefixes(context.environment_id) | frozenset(
            context.reserved_import_prefixes
        )
    except (KeyError, OSError, StopIteration, TypeError, ValueError, json.JSONDecodeError):
        return PreflightResult("UNKNOWN", "reserved_import_catalog_unavailable")
    roots = () if context.member == "targeted-pytest-plugin-preflight" else (context.snapshot_root,)
    if context.project_runtime_root is not None:
        roots = (*roots, context.project_runtime_root / "site-packages")
    collisions = tuple(f"{root}:{prefix}" for root in roots for prefix in _reserved_collision_paths(root, prefixes))
    if collisions:
        return PreflightResult("UNKNOWN", "reserved_import_collision", collisions)
    return PreflightResult("PASS")
