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


def _capture(root: Path, source: Path, name: str) -> dict[str, Any]:
    data = (source / name).read_bytes()
    captured = root / name
    captured.write_bytes(data)
    captured.chmod(0o444)
    return {"name": name, "sha256": hashlib.sha256(data).hexdigest(), "path": str(captured)}


def _inputs(root: Path, source: Path, tools: BuildTools) -> tuple[list[str], list[dict[str, Any]]]:
    args, inputs = tools.prepare(root, tools.command)
    for name in ("control_mach.inc", "control_mach_policy.h", "control_mach_reply.h", "control_exec_policy.h"):
        inputs.append(_capture(root, source, name))
    return args, inputs


def _cdhash(item: dict[str, Any], tools: BuildTools) -> str:
    hashes = [line.split("=", 1)[1] for line in item["signing"].splitlines() if line.startswith("CDHash=")]
    tools.require(
        len(hashes) == 1 and len(hashes[0]) == 40 and all(value in "0123456789abcdef" for value in hashes[0]),
        f"bad {item['name']} CDHash",
    )
    return hashes[0]


def _positive(target: Path, tools: BuildTools) -> None:
    name = target.name.removeprefix("control-")
    result = tools.command([str(target), "0"])
    marker = "target-positive-ok" if name == "target" else "control-positive-ok"
    tools.require(result.returncode == 0 and marker in result.stdout.splitlines(), f"{name} positive probes missing")


def build(root: Path, source: Path, tools: BuildTools) -> tuple[Path, Path, list[dict[str, Any]]]:
    """Compile captured source/SDK inputs and bind each exact signed payload."""
    root.chmod(0o700)
    (root / "clock-verification.json").write_text(json.dumps(tools.clock(), indent=2) + "\n")
    args, inputs = _inputs(root, source, tools)
    probes = _capture(root, source, "control_probes.h")
    target, worker, observer, broker = (root / f"control-{name}" for name in ("target", "worker", "observer", "broker"))
    target_item = _compile(source / "control_target.c", target, tools, [f"-I{root}"])
    target_item["build_inputs"] = [probes.copy()]
    target_hash = _cdhash(target_item, tools)
    target_macro = "-DFIXED_TARGET=" + json.dumps(str(target))
    worker_item = _compile(source / "control_worker.c", worker, tools, [f"-I{root}", target_macro])
    worker_item["build_inputs"] = [probes.copy()]
    worker_hash = _cdhash(worker_item, tools)
    observer_item = _compile(source / "startup_observe.c", observer, tools, [])
    args += [
        "-DFIXED_WORKER=" + json.dumps(str(worker)),
        "-DWORKER_REQUIREMENT=" + json.dumps(f'cdhash H"{worker_hash}"'),
        target_macro,
        "-DTARGET_REQUIREMENT=" + json.dumps(f'cdhash H"{target_hash}"'),
        "-framework",
        "Security",
        "-framework",
        "CoreFoundation",
    ]
    broker_item = _compile(source / "control_broker.c", broker, tools, args)
    broker_item.update(signal_transport="mach-exception-v1", build_inputs=inputs)
    _positive(target, tools)
    _positive(worker, tools)
    return broker, observer, [target_item, worker_item, observer_item, broker_item]
