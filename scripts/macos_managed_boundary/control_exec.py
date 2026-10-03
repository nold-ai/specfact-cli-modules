"""Fixed-image handoff proofs; never admit customer-selected executables."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple


LIFECYCLE_CASES = (
    "exec-cancel",
    "exec-eof",
    "exec-broker-kill",
    "exec-cancel-held",
    "exec-eof-held",
    "exec-broker-kill-held",
)
PROTOCOL_CASES = (
    "exec-status",
    "exec-runtime-trap",
    "exec-bootstrap-trap",
    "exec-failed",
    "exec-second-image",
    "exec-modified-target",
)


class ExecTools(NamedTuple):
    """Trusted fixture orchestration, bound by the controller rather than workers."""

    invocation: Any
    require: Any
    event: Any


def verify_status(status: dict[str, Any], marker: dict[str, Any], mode: int, require: Any) -> None:
    """Bind initializer ordering to the verified image stop and genuine signal result."""
    output = status["output"]
    initializers = [
        line.removeprefix("target-initializer-ns=")
        for line in output.splitlines()
        if line.startswith("target-initializer-ns=")
    ]
    require(len(initializers) == 1 and initializers[0].isdigit(), "missing or repeated target initializer")
    verified = marker.get("verified_ns")
    require(
        isinstance(verified, int) and not isinstance(verified, bool) and int(initializers[0]) >= verified,
        "target initialized before image verification",
    )
    require(marker.get("held") is False and status["traced"] is True, "replacement admission evidence missing")
    require(output.count("target-entry") == 1 and "target-denials-ok" in output, "replacement evidence missing")
    require("target-trap-was-suppressed" not in output, "genuine target trap suppressed")
    expected = (37, 0) if mode == 6 else (-1, 5)
    require((status["exit"], status["signal"]) == expected, "replacement exit/signal mismatch")
    if mode == 12:
        require("target-second-exec" in output, "second replacement not attempted")


def trials(broker: Path, observer: Path, root: Path, tools: ExecTools) -> list[dict[str, Any]]:
    """Exercise real replacement traps, confinement and substituted payload rejection."""
    cases = (
        (6, "exec-status"),
        (7, "exec-runtime-trap"),
        (8, "exec-bootstrap-trap"),
        (9, "exec-failed"),
        (12, "exec-second-image"),
    )
    results = [_trial(broker, observer, root, tools, fixture) for fixture in cases]
    results.append(_modified_target_trial(broker, observer, root, tools))
    return results


def _trial(broker: Path, observer: Path, root: Path, tools: ExecTools, fixture: tuple[int, str]) -> dict[str, Any]:
    """Measure one image/signal transition in its private invocation."""
    mode, case = fixture
    require = tools.require
    with tools.invocation(broker, observer, root) as invocation:
        invocation.case = case
        client = invocation.connect()
        launched = client.launch(mode)
        status = client.request(2, handle=launched["handle"])
        marker = tools.event(invocation.directory / "events", "exec", launched["pid"])
        if mode in (6, 7, 12):
            require(marker is not None, "replacement identity not verified")
            verify_status(status, marker, mode, require)
        else:
            require(marker is None, "failed or unrequested exec admitted")
            require("target-initializer-ns=" not in status["output"], "unexpected target initialization")
            expected = (-1, 5) if mode == 8 else (38, 0)
            require((status["exit"], status["signal"]) == expected, "bootstrap trap/failed exec mismatch")
            if mode == 8:
                require("runtime-trap-was-suppressed" not in status["output"], "bootstrap trap suppressed")
            else:
                require("exec-failed" in status["output"], "failed exec did not return")
        return {"case": case, "passed": True, "status": status, "image_stop": marker}


def _modified_target_trial(broker: Path, observer: Path, root: Path, tools: ExecTools) -> dict[str, Any]:
    """A damaged build-owned payload must be refused before any worker is launched."""
    require = tools.require
    target = root / "control-target"
    original = target.read_bytes()
    try:
        damaged = original[:64] + bytes([original[64] ^ 1]) + original[65:]
        for substituted in (damaged, (root / "control-worker").read_bytes()):
            target.write_bytes(substituted)
            with tools.invocation(broker, observer, root) as invocation:
                invocation.case = "exec-modified-target"
                client = invocation.connect()
                rejected = client.request(1, argument=6, timeout_ms=1000)
                require(
                    rejected.get("error") == "signature" and rejected.get("ok") is False, "modified target accepted"
                )
                require(
                    tools.event(invocation.directory / "events", "trace", None) is None, "substituted target spawned"
                )
        return {"case": "exec-modified-target", "passed": True, "response": rejected, "substitutions_checked": 2}
    finally:
        target.write_bytes(original)  # Restore this private negative fixture, never an installed cache.
