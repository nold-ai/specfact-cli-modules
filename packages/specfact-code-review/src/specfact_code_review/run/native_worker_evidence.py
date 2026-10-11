"""Bounded native worker paths and pytest artifacts retain exact admission order."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any


__all__ = ["WorkerContractError", "_capture_pytest_observation", "_read_pytest_artifact", "_root"]


class WorkerContractError(ValueError):
    """The fixed worker invocation, request, or result violated its contract."""


def _root(raw: str, *, writable: bool, private_tree: bool = False) -> Path:
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink():
        raise WorkerContractError("worker roots must be absolute non-symlink directories")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or resolved != path:
        raise WorkerContractError("worker root identity changed during resolution")
    _root_permissions(resolved, writable=writable, private_tree=private_tree)
    return resolved


def _read_pytest_artifact(path: Path, temporary: Path) -> bytes | None:
    """Read one bounded ordinary artifact from the confined private state."""
    if not path.is_relative_to(temporary):
        raise WorkerContractError("native pytest artifact path is invalid")
    try:
        # Resolve existing links even when an ordinary evidence directory is gone.
        # Dangling/substituted parents still change the canonical path and reject.
        if path.parent.resolve(strict=False) != path.parent:
            raise WorkerContractError("native pytest artifact path is invalid")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16 << 20:
                raise WorkerContractError("native pytest artifact type or size is invalid")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                payload = stream.read((16 << 20) + 1)
            if len(payload) > 16 << 20:
                raise WorkerContractError("native pytest artifact size is invalid")
            return payload
        finally:
            os.close(descriptor)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise WorkerContractError("native pytest artifact is unavailable") from exc


def _capture_pytest_observation(result: Any, transport: Any) -> dict[str, object] | None:
    completed, coverage_path, observer_path, junit_path = result
    # Validate every path before the evaluator can read any artifact, including
    # when an earlier file is missing. Substituted/special/oversized files fail hard.
    coverage_bytes = _read_pytest_artifact(coverage_path, transport.temporary)
    observer_bytes = _read_pytest_artifact(observer_path, transport.temporary)
    junit_bytes = _read_pytest_artifact(junit_path, transport.temporary)
    if observer_bytes is None:
        return None
    records = _observer_records(observer_bytes)
    if records is None or coverage_bytes is None or junit_bytes is None:
        return None
    coverage = _coverage_object(coverage_bytes)
    if coverage is None:
        return None
    collected = sorted(
        {record["nodeid"] for record in records if record.get("phase") in {"collection", "setup", "call", "teardown"}}
    )
    return {
        "collected": collected,
        "records": records,
        "coverage": coverage,
        "process_exit": completed.returncode,
        "result_provenance": "project-origin-v1",
    }


def _root_permissions(path: Path, *, writable: bool, private_tree: bool) -> None:
    mode = path.stat().st_mode
    if private_tree and (not mode & stat.S_IWUSR or mode & (stat.S_IRWXG | stat.S_IRWXO)):
        raise WorkerContractError("private worker root is not owner-only")
    if writable and not private_tree and not mode & stat.S_IWUSR:
        raise WorkerContractError("writable worker root is not owner-writable")
    if not writable and not private_tree and mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise WorkerContractError("immutable worker root is writable")


def _observer_records(payload: bytes) -> list[dict[str, Any]] | None:
    try:
        records = json.loads(payload)
    except (ValueError, RecursionError):
        return None
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        return None
    if not all(isinstance(record.get("nodeid"), str) for record in records):
        raise WorkerContractError("native pytest observer node identity is invalid")
    return records


def _coverage_object(payload: bytes) -> dict[str, Any] | None:
    try:
        coverage = json.loads(payload)
    except (ValueError, RecursionError):
        return None
    if not isinstance(coverage, dict) or not isinstance(coverage.get("files"), dict):
        return None
    return coverage
