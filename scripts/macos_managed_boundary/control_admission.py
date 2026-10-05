"""Real post-verification identity races; never admit alternate customer images."""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, NamedTuple


LIFECYCLE_CASES = ("exec-identity-swap",)
PROTOCOL_CASES = ("bootstrap-identity", "exec-exception-task", "exec-exception-thread")


class AdmissionTools(NamedTuple):
    """Controller-owned proof operations unavailable to confined workers."""

    invocation: Any
    require: Any
    observe_absence: Any
    cleanup_deadline: Any
    command: Any
    build: Any


def bootstrap_identity_trial(broker: Path, observer: Path, root: Path, *, tools: AdmissionTools) -> dict[str, Any]:
    """Retain proof that the exact fixed bootstrap was verified before resume."""
    with tools.invocation(broker, observer, root) as invocation:
        invocation.case = "bootstrap-identity"
        client = invocation.connect()
        launched = client.launch(1)
        status = client.request(2, handle=launched["handle"])
        tools.require(status["pid"] == launched["pid"] and status["exit"] == 37, "bootstrap control failed")
        return {
            "case": invocation.case,
            "passed": True,
            "bootstrap_identity": launched["bootstrap_identity"],
            "status": status,
        }


def _foreign_target(root: Path, tools: AdmissionTools) -> tuple[Path, dict[str, Any]]:
    """Sign a different image with the same real constructor and deny probes."""
    target = root / "foreign-target"
    record = root / "foreign-target-build.json"
    if target.exists():
        inventory = json.loads(record.read_text())
        tools.require(
            hashlib.sha256(target.read_bytes()).hexdigest() == inventory["sha256"], "foreign proof payload changed"
        )
        return target, inventory
    source = root / "foreign-target.c"
    source.write_bytes(
        (root / "source-target.c").read_bytes() + b"\nvolatile const unsigned int foreign_identity = 1;\n"
    )
    source.chmod(0o444)
    operations = tools.build.BuildTools(tools.command, None, tools.require, None)
    inventory = tools.build._compile(source, target, operations, [f"-I{root}"])
    positive = tools.command([str(target), "0"])
    tools.require(
        positive.returncode == 0 and "target-positive-ok" in positive.stdout.splitlines(), "foreign control failed"
    )
    tools.require(
        sum(line.startswith("target-initializer-ns=") for line in positive.stdout.splitlines()) == 1,
        "foreign initializer positive control missing",
    )
    inventory["positive_output"] = positive.stdout
    record.write_text(json.dumps(inventory))
    record.chmod(0o400)
    return target, inventory


def identity_swap_trial(broker: Path, observer: Path, root: Path, *, tools: AdmissionTools) -> dict[str, Any]:
    """Replace the verified path while its direct traced bootstrap is held."""
    foreign, foreign_inventory = _foreign_target(root, tools)
    target = root / "control-target"
    saved = root / "control-target-retained"
    replacement = root / "identity-swap-payload"
    replacement.write_bytes(foreign.read_bytes())
    replacement.chmod(0o755)
    with tools.invocation(broker, observer, root) as invocation:
        invocation.case = "exec-identity-swap"
        client = invocation.connect()
        launched = client.launch(13)
        identity = invocation.capture_worker(launched, 13)
        deadline = tools.cleanup_deadline(launched)
        os.replace(target, saved)
        try:
            os.replace(replacement, target)
            started = time.monotonic()
            # This fixed bootstrap ignores TERM; the broker still preserves signal
            # delivery while releasing its initial stop. No new RPC grants exist.
            with suppress(EOFError, OSError):
                client.request(3, handle=launched["handle"], argument=15)
            # Only independently measured rejection below can accept.
            rejection = invocation.wait_event("exec_identity_failure", launched["pid"])
            tools.require(rejection.get("stage") == "foreign", "dynamic identity rejection missing")
            result = tools.observe_absence(invocation, identity, started, job=True, native_deadline_ns=deadline)
            tools.require(rejection.get("output_complete") is True, "rejected image output was not observed")
            tools.require(rejection.get("initializer_seen") is False, "rejected image initialized")
            return {
                "case": "exec-identity-swap",
                **result,
                "bootstrap_identity": launched["bootstrap_identity"],
                "image_rejection": rejection,
                "foreign_payload": foreign_inventory,
            }
        finally:
            os.replace(saved, target)


def exception_port_trial(
    broker: Path, observer: Path, root: Path, kind: str, *, tools: AdmissionTools
) -> dict[str, Any]:
    """Try the real Mach API and independently inspect installed exception rights."""
    if kind not in ("task", "thread"):
        raise ValueError("unknown exception-port fixture")
    positive = tools.command([str(root / "control-target"), "7"])
    tools.require(positive.returncode == 0, "unconfined exception-port control failed")
    tools.require(
        f"exception-port-{kind}-status=0-installed=1" in positive.stdout.splitlines(),
        "unconfined endpoint replacement was not observed",
    )
    with tools.invocation(broker, observer, root) as invocation:
        invocation.case = f"exec-exception-{kind}"
        client = invocation.connect()
        launched = client.launch(14 if kind == "task" else 15)
        status = client.request(2, handle=launched["handle"])
        marker = f"exception-port-{kind}-status="
        observations = [line for line in status["output"].splitlines() if line.startswith(marker)]
        tools.require(len(observations) == 1, "exception-port observation missing")
        installed = observations[0].endswith("-installed=1")
        tools.require(observations[0].endswith("-installed=0") or installed, "invalid port observation")
        tools.require(status["exit"] == 37 and not installed, "confined worker replaced exception endpoint")
        tools.require(f"exception-swap-{kind}-installed=0" in status["output"].splitlines(), "exception swap escaped")
        tools.require(f"exception-clear-{kind}-preserved=1" in status["output"].splitlines(), "exception clear escaped")
        return {"case": invocation.case, "passed": True, "status": status, "installed": installed}
