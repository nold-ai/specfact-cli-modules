"""Inventory ELF dependencies without executing ldd or customer extension code."""

from __future__ import annotations

import re
import shutil
import struct
from pathlib import Path
from typing import Any

from icontract import ensure

from specfact_code_review.run.runtime_models import ProjectRuntimeError, content_digest


SYSTEM_LIBRARY_ROOTS = (Path("/usr/lib/x86_64-linux-gnu"), Path("/lib/x86_64-linux-gnu"))


def _elf_sections(payload: bytes, name: str) -> list[tuple[int, ...]]:
    if len(payload) < 64 or payload[4:6] != b"\x02\x01":
        raise ProjectRuntimeError(f"project_native_elf_unsupported:{name}")
    machine = struct.unpack_from("<H", payload, 18)[0]
    if machine != 62:  # EM_X86_64
        raise ProjectRuntimeError(
            f"project_native_elf_architecture_unsupported:{name}:machine={machine}; require x86_64"
        )
    offset = struct.unpack_from("<Q", payload, 40)[0]
    size, count = struct.unpack_from("<HH", payload, 58)
    if size != 64 or offset + size * count > len(payload):
        raise ProjectRuntimeError(f"project_native_elf_invalid:{name}")
    return [struct.unpack_from("<IIQQQQIIQQ", payload, offset + index * size) for index in range(count)]


def _needed_names(payload: bytes, section: tuple[int, ...], sections: list[tuple[int, ...]]) -> list[str]:
    start, length, strings_index = section[4], section[5], section[6]
    if strings_index >= len(sections) or start + length > len(payload) or length % 16:
        raise ProjectRuntimeError("project_native_elf_invalid:dynamic section bounds")
    strings = sections[strings_index]
    table = payload[strings[4] : strings[4] + strings[5]]
    if len(table) != strings[5]:
        raise ProjectRuntimeError("project_native_elf_invalid:string table bounds")
    names = []
    for position in range(start, start + length, 16):
        tag, value = struct.unpack_from("<QQ", payload, position)
        if tag != 1:
            continue
        end = table.find(b"\0", value)
        if end < 0:
            raise ProjectRuntimeError("project_native_elf_invalid:unterminated dependency")
        names.append(table[value:end].decode("ascii"))
    return names


@ensure(lambda result: result == tuple(sorted(set(result))))
def elf_dependencies(path: Path) -> tuple[str, ...]:
    """Read ELF64 dynamic section DT_NEEDED names, with strict bounds checks."""
    payload = path.read_bytes()
    if not payload.startswith(b"\x7fELF"):
        return ()
    sections = _elf_sections(payload, path.name)
    names = []
    for section in sections:
        if section[1] == 6:  # SHT_DYNAMIC
            names.extend(_needed_names(payload, section, sections))
    return tuple(sorted(set(names)))


def _system_library(name: str, system_roots: tuple[Path, ...]) -> Path:
    candidates = [root / name for root in system_roots if (root / name).is_file()]
    if not candidates:
        raise ProjectRuntimeError(
            f"project_native_library_missing:{name}; install the declared system library on the builder"
        )
    source = candidates[0].resolve()
    if not any(source.is_relative_to(root.resolve()) for root in system_roots):
        raise ProjectRuntimeError(f"project_native_library_escape:{name}")
    if not source.read_bytes().startswith(b"\x7fELF"):
        raise ProjectRuntimeError(f"project_native_library_not_elf:{name}")
    return source


def _native_record(path: Path, artifact: Path, origin: str) -> dict[str, Any]:
    return {
        "path": path.relative_to(artifact).as_posix(),
        "sha256": content_digest(path.read_bytes()),
        "needed": elf_dependencies(path),
        "origin": origin,
    }


def _library_closure(
    artifact: Path, pending: set[str], available: set[str], system_roots: tuple[Path, ...]
) -> list[dict[str, Any]]:
    seen = set()
    records = []
    while pending:
        name = min(pending)
        pending.remove(name)
        if name in seen:
            continue
        seen.add(name)
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+\.so(?:\.[A-Za-z0-9_.+-]+)*", name):
            raise ProjectRuntimeError(f"project_native_library_invalid:{name}; declare ELF shared-library names")
        if name in available:
            continue
        source = _system_library(name, system_roots)
        pending.update(elf_dependencies(source))
        target = artifact / "native" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o755 if name == "ld-linux-x86-64.so.2" else 0o644)
        records.append({**_native_record(target, artifact, "system-library"), "source": str(source)})
    return records


def _native_extensions(artifact: Path) -> list[Path]:
    return sorted(
        {path for pattern in ("*.so*", "executables/*") for path in artifact.rglob(pattern) if path.is_file()}
    )


@ensure(lambda result: all(row["sha256"].startswith("sha256:") for row in result))
def inventory_native(
    artifact: Path,
    *,
    capsule_root: Path,
    declared: tuple[str, ...],
    system_roots: tuple[Path, ...] = SYSTEM_LIBRARY_ROOTS,
    target_loader: bool = False,
) -> list[dict[str, Any]]:
    """Copy required native closures into target storage; preserve the signed supervisor."""
    extensions = _native_extensions(artifact)
    capsule = {path.name for path in capsule_root.rglob("*.so*") if path.is_file()}
    bundled = {path.name for path in extensions}
    records = [_native_record(extension, artifact, "project") for extension in extensions]
    pending = set(declared)
    for record in records:
        pending.update(record["needed"])
    available = capsule | bundled
    if target_loader and pending:
        # Newer native libraries must use a matching loader/libc domain, never
        # replace libc underneath the running signed supervisor.
        pending.add("ld-linux-x86-64.so.2")
        available = bundled | {name for name in capsule if name.startswith("libpython")}
    return records + _library_closure(artifact, pending, available, system_roots)
