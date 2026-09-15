"""Seal and validate private local runtime artifacts without executing payloads."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.runtime_models import (
    PreparedRuntime,
    ProjectPlan,
    ProjectRuntimeError,
    content_digest,
    document_digest,
)


_DESCRIPTOR = "project-runtime.json"


def _reject_hardlink(metadata: os.stat_result, name: str) -> None:
    """Require independent regular files before reading untrusted payload bytes."""
    if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1:
        raise ProjectRuntimeError(f"project_runtime_hardlink_invalid:{name}; independent file required")


def _validate_build_directory(directory: Path, root: Path) -> list[Path]:
    """Check immediate nodes without reading payloads, returning directories to visit."""
    children = []
    with os.scandir(directory) as entries:
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            _reject_hardlink(metadata, Path(entry.path).relative_to(root).as_posix())
            mode = metadata.st_mode
            if stat.S_ISDIR(mode):
                children.append(Path(entry.path))
                continue
            if not stat.S_ISREG(mode):
                name = Path(entry.path).relative_to(root).as_posix()
                raise ProjectRuntimeError(f"project_runtime_build_artifact_invalid:{name}; regular nodes required")
    return children


@beartype
@require(lambda root: bool(root.name))
def validate_build_artifact(root: Path) -> None:
    """Reject indirection and special nodes before reading untrusted build output."""
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ProjectRuntimeError("project_runtime_build_artifact_invalid: root must be a regular directory")
    pending = [root]
    while pending:
        pending.extend(_validate_build_directory(pending.pop(), root))


def _payload_manifest(root: Path) -> dict[str, dict[str, object]]:
    entries = {}
    if root.is_symlink() or not root.is_dir():
        raise ProjectRuntimeError("project_runtime_payload_invalid: root must be a regular directory")
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        if name in {_DESCRIPTOR, "." + _DESCRIPTOR + ".tmp"}:
            continue
        metadata = path.lstat()
        _reject_hardlink(metadata, name)
        mode = metadata.st_mode
        if stat.S_ISLNK(mode):
            raise ProjectRuntimeError(f"project_runtime_payload_symlink:{name}")
        if stat.S_ISDIR(mode):
            entries[name] = {"kind": "directory", "mode": stat.S_IMODE(mode)}
        elif stat.S_ISREG(mode):
            entries[name] = {"kind": "file", "mode": stat.S_IMODE(mode), "digest": content_digest(path.read_bytes())}
        else:
            raise ProjectRuntimeError(f"project_runtime_payload_special_file:{name}")
    return entries


@ensure(lambda result: result.descriptor_path.is_file())
def seal_runtime(
    root: Path,
    *,
    plan: ProjectPlan,
    environment_id: str,
    worker_identity: str,
    inventory: dict[str, Any] | None = None,
) -> PreparedRuntime:
    """Publish a descriptor only after the complete local payload is available."""
    root = root.absolute()
    descriptor: dict[str, Any] = {
        "schema": "project-runtime-layer-v2",
        "environment_id": environment_id,
        "project_identity": plan.identity,
        "project": plan.document(),
        "worker_identity": worker_identity,
        "provenance": {"authority": "local_build", "protected_pr_eligible": False},
        "inventory": inventory or {},
        "payload": _payload_manifest(root),
    }
    descriptor["identity"] = document_digest(descriptor)
    target = root / _DESCRIPTOR
    temporary = root / ("." + _DESCRIPTOR + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(descriptor, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    return PreparedRuntime(root, target, descriptor["identity"], descriptor)


def _validate_inventory(inventory: object) -> None:
    if not isinstance(inventory, dict):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: expected an object")
    arguments = inventory.get("pytest_arguments", [])
    if not isinstance(arguments, list) or not all(isinstance(value, str) for value in arguments):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: pytest_arguments must be an array of strings")
    conflicts = inventory.get("analyzer_conflicts", {})
    if not isinstance(conflicts, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in conflicts.items()
    ):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: analyzer_conflicts must map strings")
    graphs = inventory.get("member_graphs", {})
    if not isinstance(graphs, dict):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: member_graphs must be an object")
    for graph in graphs.values():
        _validate_member_graph(graph)


def _validate_member_distribution(row: object) -> None:
    if (
        not isinstance(row, dict)
        or not isinstance(row.get("name"), str)
        or not isinstance(row.get("origin"), str)
        or row["origin"] not in {"project", "analyzer"}
    ):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: malformed member distribution")


def _validate_member_graph(graph: object) -> None:
    if (
        not isinstance(graph, dict)
        or not isinstance(graph.get("sealed_imports"), list)
        or not isinstance(graph.get("installed"), list)
    ):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: malformed member graph")
    if not all(isinstance(name, str) and name.isidentifier() for name in graph["sealed_imports"]):
        raise ProjectRuntimeError("project_runtime_inventory_invalid: malformed member imports")
    for row in graph["installed"]:
        _validate_member_distribution(row)


def _read_descriptor(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.name != _DESCRIPTOR:
        raise ProjectRuntimeError("project_runtime_descriptor_invalid: expected project-runtime.json")
    _reject_hardlink(path.lstat(), path.name)
    try:
        descriptor = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectRuntimeError(f"project_runtime_descriptor_invalid:{exc}") from exc
    if not isinstance(descriptor, dict) or descriptor.get("schema") != "project-runtime-layer-v2":
        raise ProjectRuntimeError("project_runtime_descriptor_schema_unsupported")
    unsigned = {key: value for key, value in descriptor.items() if key != "identity"}
    if descriptor.get("identity") != document_digest(unsigned):
        raise ProjectRuntimeError("project_runtime_descriptor_identity_mismatch")
    _validate_inventory(descriptor.get("inventory"))
    return descriptor


def _verify_context(descriptor: dict[str, Any], plan: ProjectPlan, environment_id: str, worker_identity: str) -> None:
    if descriptor.get("provenance") != {"authority": "local_build", "protected_pr_eligible": False}:
        raise ProjectRuntimeError("project_runtime_descriptor_authority_invalid")
    if descriptor.get("project_identity") != plan.identity or descriptor.get("project") != json.loads(
        json.dumps(plan.document())
    ):
        raise ProjectRuntimeError("project_runtime_inputs_mismatch: run runtime prepare again")
    if descriptor.get("environment_id") != environment_id:
        raise ProjectRuntimeError("project_runtime_environment_mismatch: rebuild for the selected capsule ABI")
    if descriptor.get("worker_identity") != worker_identity:
        raise ProjectRuntimeError("project_runtime_worker_identity_mismatch: rebuild for the selected analyzer worker")


@ensure(lambda result, plan: result.descriptor["project_identity"] == plan.identity)
def load_runtime(path: Path, *, plan: ProjectPlan, environment_id: str, worker_identity: str) -> PreparedRuntime:
    """Verify all artifact bytes and current inputs before returning any mount root."""
    descriptor = _read_descriptor(path)
    _verify_context(descriptor, plan, environment_id, worker_identity)
    root = path.absolute().parent
    if descriptor.get("payload") != _payload_manifest(root):
        raise ProjectRuntimeError("project_runtime_payload_identity_mismatch: rebuild the corrupt artifact")
    return PreparedRuntime(root, path.absolute(), str(descriptor["identity"]), descriptor)
