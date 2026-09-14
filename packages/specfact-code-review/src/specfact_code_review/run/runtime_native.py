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


@ensure(lambda result: all(row["sha256"].startswith("sha256:") for row in result))
def inventory_native(
    artifact: Path,
    *,
    capsule_root: Path,
    declared: tuple[str, ...],
    system_roots: tuple[Path, ...] = SYSTEM_LIBRARY_ROOTS,
) -> list[dict[str, Any]]:
    """Copy only required shared-library closures; preserve signed capsule libraries."""
    extensions = sorted(path for path in artifact.rglob("*.so*") if path.is_file())
    capsule = {path.name: path for path in capsule_root.rglob("*.so*") if path.is_file()}
    bundled = {path.name: path for path in extensions}
    pending = set(declared)
    records = [_native_record(extension, artifact, "project") for extension in extensions]
    for record in records:
        pending.update(record["needed"])
    seen = set()
    while pending:
        name = min(pending)
        pending.remove(name)
        if name in seen:
            continue
        seen.add(name)
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+\.so(?:\.[A-Za-z0-9_.+-]+)*", name):
            raise ProjectRuntimeError(f"project_native_library_invalid:{name}; declare ELF shared-library names")
        if name in capsule or name in bundled:
            continue
        source = _system_library(name, system_roots)
        needed = elf_dependencies(source)
        pending.update(needed)
        target = artifact / "native" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o644)
        records.append({**_native_record(target, artifact, "system-library"), "source": str(source)})
    return records
