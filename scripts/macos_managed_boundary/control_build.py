"""Exact source and SDK snapshots for signed native control experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, NamedTuple


class BuildTools(NamedTuple):
    """Trusted maintainer commands and proof checks, never worker-selected hooks."""

    command: Any
    clock: Any
    require: Any
    prepare: Any


def _sign(target: Path, tools: BuildTools) -> tuple[str, str]:
    tools.command(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)])
    tools.command(["/usr/bin/codesign", "--verify", "--strict", str(target)])
    details = tools.command(["/usr/bin/codesign", "--display", "--verbose=4", str(target)]).stderr
    tools.require(
        "flags=0x10002(adhoc,runtime)" in details and "Signature=adhoc" in details, "unexpected signature configuration"
    )
    entitlements = tools.command(["/usr/bin/codesign", "--display", "--entitlements", ":-", str(target)]).stdout
    tools.require(not entitlements.strip(), "fixture has unexpected entitlements")
    return details, entitlements


def _compile(code: Path, target: Path, tools: BuildTools, extra: list[str]) -> dict[str, Any]:
    snapshot = code.read_bytes()
    compiled_source = target.parent / f"source-{target.name.removeprefix('control-')}.c"
    compiled_source.write_bytes(snapshot)
    compiled_source.chmod(0o444)
    tools.command(
        [
            "/usr/bin/xcrun",
            "clang",
            "-arch",
            "arm64",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(compiled_source),
            "-o",
            str(target),
            *extra,
        ]
    )
    details, entitlements = _sign(target, tools)
    return {
        "name": target.name.removeprefix("control-"),
        "path": str(target),
        "source_sha256": hashlib.sha256(snapshot).hexdigest(),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "signing": details,
        "entitlements": entitlements,
    }


def _inputs(root: Path, source: Path, tools: BuildTools) -> tuple[list[str], list[dict[str, Any]]]:
    args, inputs = tools.prepare(root, tools.command)
    for name in ("control_mach.inc", "control_mach_policy.h", "control_mach_reply.h"):
        data = (source / name).read_bytes()
        captured = root / name
        captured.write_bytes(data)
        captured.chmod(0o444)
        inputs.append({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "path": str(captured)})
    return args, inputs


def build(root: Path, source: Path, tools: BuildTools) -> tuple[Path, Path, list[dict[str, Any]]]:
    """Compile captured source/SDK inputs and bind each exact signed payload."""
    root.chmod(0o700)
    (root / "clock-verification.json").write_text(json.dumps(tools.clock(), indent=2) + "\n")
    args, inputs = _inputs(root, source, tools)
    worker, observer, broker = (root / f"control-{name}" for name in ("worker", "observer", "broker"))
    worker_item = _compile(source / "control_worker.c", worker, tools, [])
    worker_hash = next(
        line.split("=", 1)[1] for line in worker_item["signing"].splitlines() if line.startswith("CDHash=")
    )
    tools.require(
        len(worker_hash) == 40 and all(value in "0123456789abcdef" for value in worker_hash), "bad worker CDHash"
    )
    observer_item = _compile(source / "startup_observe.c", observer, tools, [])
    args += [
        f'-DFIXED_WORKER="{worker}"',
        f'-DWORKER_REQUIREMENT="cdhash H\\"{worker_hash}\\""',
        "-framework",
        "Security",
        "-framework",
        "CoreFoundation",
    ]
    broker_item = _compile(source / "control_broker.c", broker, tools, args)
    broker_item.update(signal_transport="mach-exception-v1", build_inputs=inputs)
    positive = tools.command([str(worker), "0"])
    tools.require("control-positive-ok" in positive.stdout, "unsandboxed native positive probes missing")
    return broker, observer, [worker_item, observer_item, broker_item]
