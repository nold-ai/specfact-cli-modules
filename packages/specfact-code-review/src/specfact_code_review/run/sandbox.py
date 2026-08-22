"""Closed snapshot invocation and operating-system isolation boundary."""

from __future__ import annotations

import hashlib
import json
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


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def validate_bubblewrap(identity: BubblewrapIdentity) -> IsolationValidation:
    """Require the canonical static Linux x86_64 Bubblewrap descriptor."""

    expected = {
        "path": "/opt/specfact/bin/bwrap-static",
        "format": "ELF",
        "architecture": "x86_64",
        "linkage": "static",
    }
    actual = {
        "path": identity.path,
        "format": identity.format,
        "architecture": identity.architecture,
        "linkage": identity.linkage,
    }
    digest_fields_valid = all(
        value.startswith("sha256:") and len(value) == 71 for value in (identity.sha256, identity.descriptor_digest)
    )
    if actual != expected or identity.interpreter or identity.needed or not digest_fields_valid:
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
        SandboxMount("snapshot", "snapshot", context.snapshot_root, "/opt/specfact/snapshot", True),
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

    cwd = "/opt/specfact/control" if context.member == "radon" else "/opt/specfact/snapshot"
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


def _reserved_collision_paths(root: Path, prefixes: frozenset[str]) -> tuple[str, ...]:
    collisions: list[str] = []
    for prefix in sorted(prefixes):
        candidates = (root / f"{prefix}.py", root / f"{prefix}.pyi", root / prefix)
        if any(candidate.exists() or candidate.is_symlink() for candidate in candidates):
            collisions.append(prefix)
    return tuple(collisions)


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def preflight_reserved_imports(context: SnapshotInvocationContext) -> PreflightResult:
    """Reject top-level module, stub, package, or namespace-package collisions."""

    prefixes = frozenset(context.reserved_import_prefixes)
    roots = (context.snapshot_root,) + (() if context.project_runtime_root is None else (context.project_runtime_root,))
    collisions = tuple(f"{root}:{prefix}" for root in roots for prefix in _reserved_collision_paths(root, prefixes))
    if collisions:
        return PreflightResult("UNKNOWN", "reserved_import_collision", collisions)
    return PreflightResult("PASS")
