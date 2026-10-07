"""Bounded diagnostic observations; missing snapshots never prove process state."""

from __future__ import annotations

import json
from typing import Any


STATE_FIELDS = ("wait_accepted", "wait_pending", "worker_reaped", "output_closed")
OUTPUT_CLASSES = frozenset(
    ("profile_initialization", "python_initialization", "python_path_configuration", "loader", "unclassified")
)
RESULT_FIELDS = ("worker_exited", "worker_signalled", "entry_marker_present")
RESULT_STAGES = frozenset(
    ("entered", "queued", "output_encoding", "response_size", "queue_capacity", "session_deadline")
)


def _is_integer(value: Any, minimum: int) -> bool:
    """JSON integers exclude booleans even though bool inherits from int."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _wait_worker_pid(history: list[dict[str, Any]]) -> int | None:
    """Resolve the final wait only through this client's recorded launches."""
    request = history[-1]
    fields = request.get("fields", {})
    if request.get("opcode") != 2 or not isinstance(fields, dict):
        return None
    handle = fields.get("handle")
    if not _is_integer(handle, 1):
        return None
    pid = None
    for item in history:
        response = item.get("response", {})
        if item.get("opcode") == 1 and isinstance(response, dict) and response.get("handle") == handle:
            pid = response.get("pid")
    return pid if _is_integer(pid, 2) else None


def _worker_snapshot(line: str, pid: int) -> dict[str, bool]:
    """Reject malformed/foreign records and project only actual boolean fields."""
    try:
        item = json.loads(line)
    except ValueError:
        return {}
    if not isinstance(item, dict) or not _is_integer(item.get("control_state"), 2) or item["control_state"] != pid:
        return {}
    if not all(isinstance(item.get(field), bool) for field in STATE_FIELDS):
        return {}
    return {field: item[field] for field in STATE_FIELDS}


def last_worker_state(events: str, history: list[dict[str, Any]], phase: str) -> dict[str, bool]:
    """Select only the last valid snapshot of the failing wait's launched worker."""
    if phase != "request-wait" or not history or len(history) > 64 or len(events.encode()) > 8192:
        return {}
    pid = _wait_worker_pid(history)
    if pid is None:
        return {}
    result: dict[str, bool] = {}
    for line in events.splitlines():
        state = _worker_snapshot(line, pid)
        if state:
            result = state
    return result


def project_worker_result(item: object) -> dict[str, object]:
    """Keep only fixed rejection stages and actual status-class booleans."""
    if not isinstance(item, dict):
        return {}
    stage = item.get("stage")
    if not isinstance(stage, str) or stage not in RESULT_STAGES:
        return {}
    if not all(isinstance(item.get(field), bool) for field in RESULT_FIELDS):
        return {}
    result = {"stage": stage, **{field: item[field] for field in RESULT_FIELDS}}
    if "output_class" in item:
        kind = item["output_class"]
        if not isinstance(kind, str) or kind not in OUTPUT_CLASSES:
            return {}
        result["output_class"] = kind
    return result


def last_worker_result(events: str, history: list[dict[str, Any]], phase: str) -> dict[str, object]:
    """Bind the last finite result observation to this client's failing WAIT."""
    if phase != "request-wait" or not history or len(history) > 64 or len(events.encode()) > 8192:
        return {}
    pid = _wait_worker_pid(history)
    if pid is None:
        return {}
    result: dict[str, object] = {}
    for line in events.splitlines():
        try:
            item = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if isinstance(item, dict) and _is_integer(item.get("control_result"), 2) and item["control_result"] == pid:
            result = project_worker_result(item) or result
    return result


def wait_observations(events: str, history: list[dict[str, Any]], phase: str) -> dict[str, object]:
    """Omit absent observations without manufacturing a successful state."""
    readers = {"last_worker_state": last_worker_state, "last_worker_result": last_worker_result}
    return {field: value for field, reader in readers.items() if (value := reader(events, history, phase))}
