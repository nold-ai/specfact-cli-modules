"""Bounded diagnostic observations; missing snapshots never prove process state."""

from __future__ import annotations

import json
from typing import Any


STATE_FIELDS = ("wait_accepted", "wait_pending", "worker_reaped", "output_closed")


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
