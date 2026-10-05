"""Inventory ELF and Mach-O dependencies without executing customer code."""

from __future__ import annotations

import re
import shutil
import struct
from pathlib import Path
from typing import Any

from icontract import ensure

from specfact_code_review.run.runtime_models import ProjectRuntimeError, content_digest


SYSTEM_LIBRARY_ROOTS = (Path("/usr/lib/x86_64-linux-gnu"), Path("/lib/x86_64-linux-gnu"))

_CPU_ARM64 = 0x0100000C
_CPU_X86_64 = 0x01000007
_MACHO_ARCHITECTURES = {_CPU_ARM64: "arm64", _CPU_X86_64: "x86_64"}
_MACHO_LOAD_COMMANDS = {
    0xC,  # LC_LOAD_DYLIB
    0x80000018,  # LC_LOAD_WEAK_DYLIB
    0x8000001F,  # LC_REEXPORT_DYLIB
    0x20,  # LC_LAZY_LOAD_DYLIB
    0x80000023,  # LC_LOAD_UPWARD_DYLIB
}
_MACHO_RPATH = 0x8000001C
_MACHO_ID_DYLIB = 0xD
_MACHO_LOAD_DYLINKER = 0xE
_MACHO_PASSIVE_REQUIRED = {
    0x80000022,  # LC_DYLD_INFO_ONLY
    0x80000028,  # LC_MAIN
    0x80000033,  # LC_DYLD_EXPORTS_TRIE
    0x80000034,  # LC_DYLD_CHAINED_FIXUPS
}
_MACHO_SYSTEM_ROOTS = (Path("/usr/lib"), Path("/System/Library"))
_MACHO_MAX_SLICES = 64
_MACHO_MAX_COMMANDS = 4096


def _macho_error(name: str, detail: str) -> ProjectRuntimeError:
    return ProjectRuntimeError(f"project_native_macho_invalid:{name}:{detail}")


def _macho_architecture(cpu: int, subtype: int) -> str:
    base_subtype = subtype & 0x00FFFFFF
    if cpu == _CPU_ARM64:
        if base_subtype == 0:
            return "arm64"
        if base_subtype == 2:
            return "arm64e"
        return f"arm64-subtype-{base_subtype}"
    return _MACHO_ARCHITECTURES.get(cpu, f"cpu-{cpu:#x}")


def _thin_macho_cpu(payload: bytes, name: str) -> tuple[str, int, int]:
    magic = payload[:4]
    if magic == b"\xcf\xfa\xed\xfe":
        byte_order = "<"
    elif magic == b"\xfe\xed\xfa\xcf":
        byte_order = ">"
    else:
        raise _macho_error(name, "unsupported thin magic")
    if len(payload) < 32:
        raise _macho_error(name, "truncated header")
    cpu, subtype = struct.unpack_from(byte_order + "II", payload, 4)
    return byte_order, cpu, subtype


def _fat_slices(payload: bytes, name: str) -> tuple[tuple[str, ...], bytes]:
    magic = payload[:4]
    formats = {
        b"\xca\xfe\xba\xbe": (">", False),
        b"\xbe\xba\xfe\xca": ("<", False),
        b"\xca\xfe\xba\xbf": (">", True),
        b"\xbf\xba\xfe\xca": ("<", True),
    }
    if magic not in formats or len(payload) < 8:
        raise _macho_error(name, "unsupported fat magic")
    byte_order, wide = formats[magic]
    count = struct.unpack_from(byte_order + "I", payload, 4)[0]
    entry_size = 32 if wide else 20
    table_end = 8 + count * entry_size
    if not 1 <= count <= _MACHO_MAX_SLICES or table_end > len(payload):
        raise _macho_error(name, "fat slice table bounds")
    slices: dict[tuple[int, int], bytes] = {}
    ranges: list[tuple[int, int]] = []
    for index in range(count):
        position = 8 + index * entry_size
        if wide:
            cpu, subtype, offset, size, alignment, _reserved = struct.unpack_from(
                byte_order + "IIQQII", payload, position
            )
        else:
            cpu, subtype, offset, size, alignment = struct.unpack_from(byte_order + "IIIII", payload, position)
        end = offset + size
        architecture = (cpu, subtype)
        if (
            architecture in slices
            or alignment > 30
            or offset % (1 << alignment)
            or offset < table_end
            or end > len(payload)
        ):
            raise _macho_error(name, "invalid fat slice")
        if any(offset < prior_end and prior_start < end for prior_start, prior_end in ranges):
            raise _macho_error(name, "overlapping fat slices")
        image = payload[offset:end]
        _slice_order, actual_cpu, actual_subtype = _thin_macho_cpu(image, name)
        if (actual_cpu, actual_subtype) != architecture:
            raise _macho_error(name, "fat slice architecture mismatch")
        slices[architecture] = image
        ranges.append((offset, end))
    architectures = tuple(sorted(_macho_architecture(cpu, subtype) for cpu, subtype in slices))
    arm64 = [image for (cpu, subtype), image in slices.items() if cpu == _CPU_ARM64 and subtype & 0x00FFFFFF == 0]
    if len(arm64) != 1:
        raise ProjectRuntimeError(
            f"project_native_macho_architecture_unsupported:{name}:"
            f"architectures={','.join(architectures)}; require arm64"
        )
    return architectures, arm64[0]


def _arm64_macho(payload: bytes, name: str) -> tuple[tuple[str, ...], bytes, str]:
    if payload[:4] in {b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"}:
        architectures, image = _fat_slices(payload, name)
        byte_order, cpu, subtype = _thin_macho_cpu(image, name)
    else:
        byte_order, cpu, subtype = _thin_macho_cpu(payload, name)
        architectures = (_macho_architecture(cpu, subtype),)
        image = payload
    if cpu != _CPU_ARM64 or subtype & 0x00FFFFFF != 0:
        raise ProjectRuntimeError(
            f"project_native_macho_architecture_unsupported:{name}:"
            f"architectures={','.join(architectures)}; require arm64"
        )
    return architectures, image, byte_order


def _macho_command_string(image: bytes, position: int, size: int, byte_order: str, *, minimum: int) -> str:
    if size < minimum:
        raise _macho_error("load-command", "command too small")
    offset = struct.unpack_from(byte_order + "I", image, position + 8)[0]
    if offset < minimum or offset >= size:
        raise _macho_error("load-command", "string offset")
    start = position + offset
    end = image.find(b"\0", start, position + size)
    if end < 0:
        raise _macho_error("load-command", "unterminated string")
    try:
        value = image[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _macho_error("load-command", "non-UTF-8 string") from exc
    if not value or any(ord(character) < 32 for character in value):
        raise _macho_error("load-command", "unsafe string")
    return value


def _macho_metadata(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    architectures, image, byte_order = _arm64_macho(payload, path.name)
    if len(image) < 32:
        raise _macho_error(path.name, "truncated header")
    _magic, _cpu, _subtype, filetype, count, command_bytes, _flags, _reserved = struct.unpack_from(
        byte_order + "8I", image
    )
    if filetype not in {2, 6, 8}:  # MH_EXECUTE, MH_DYLIB, MH_BUNDLE
        raise ProjectRuntimeError(f"project_native_macho_filetype_unsupported:{path.name}:filetype={filetype}")
    command_end = 32 + command_bytes
    if count > _MACHO_MAX_COMMANDS or command_end > len(image):
        raise _macho_error(path.name, "load command bounds")
    dependencies: list[str] = []
    rpaths: list[str] = []
    position = 32
    for _index in range(count):
        if position + 8 > command_end:
            raise _macho_error(path.name, "truncated load command")
        command, size = struct.unpack_from(byte_order + "II", image, position)
        if size < 8 or size % 8 or position + size > command_end:
            raise _macho_error(path.name, "load command size")
        if command in _MACHO_LOAD_COMMANDS:
            dependencies.append(_macho_command_string(image, position, size, byte_order, minimum=24))
        elif command == _MACHO_RPATH:
            rpaths.append(_macho_command_string(image, position, size, byte_order, minimum=12))
        elif command == _MACHO_ID_DYLIB:
            _macho_command_string(image, position, size, byte_order, minimum=24)
        elif command == _MACHO_LOAD_DYLINKER:
            linker = _macho_command_string(image, position, size, byte_order, minimum=12)
            if linker != "/usr/lib/dyld":
                raise ProjectRuntimeError(f"project_native_macho_dynamic_linker_unsafe:{linker}")
        elif command & 0x80000000 and command not in _MACHO_PASSIVE_REQUIRED:
            raise _macho_error(path.name, f"unsupported required command {command:#x}")
        position += size
    if position != command_end:
        raise _macho_error(path.name, "load command byte count")
    return {
        "architectures": architectures,
        "filetype": filetype,
        "needed": tuple(sorted(set(dependencies))),
        "rpaths": tuple(sorted(set(rpaths))),
    }


def _is_macho(payload: bytes) -> bool:
    return payload[:4] in {
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }


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
    if offset == 0 and count == 0 and size in (0, 64):
        return []
    if size != 64 or offset + size * count > len(payload):
        raise ProjectRuntimeError(f"project_native_elf_invalid:{name}")
    return [struct.unpack_from("<IIQQQQIIQQ", payload, offset + index * size) for index in range(count)]


def _dependency_name(table: bytes, offset: int) -> str:
    end = table.find(b"\0", offset)
    if end < 0:
        raise ProjectRuntimeError("project_native_elf_invalid:unterminated dependency")
    try:
        return table[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ProjectRuntimeError("project_native_elf_invalid:non-ASCII dependency") from exc


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
        names.append(_dependency_name(table, value))
    return names


def _validate_segment_bounds(segment: tuple[int, ...], payload_size: int) -> None:
    if segment[0] not in (1, 2):  # PT_LOAD, PT_DYNAMIC
        return
    start, address, length, memory = segment[2], segment[3], segment[5], segment[6]
    if start + length > payload_size or length > memory or address + memory > 2**64:
        raise ProjectRuntimeError("project_native_elf_invalid:program segment bounds")


def _elf_segments(payload: bytes) -> list[tuple[int, ...]]:
    offset = struct.unpack_from("<Q", payload, 32)[0]
    size, count = struct.unpack_from("<HH", payload, 54)
    if count == 0:
        return []
    if size != 56 or offset < 64 or offset + size * count > len(payload):
        raise ProjectRuntimeError("project_native_elf_invalid:program header bounds")
    segments = [struct.unpack_from("<IIQQQQQQ", payload, offset + index * size) for index in range(count)]
    for segment in segments:
        _validate_segment_bounds(segment, len(payload))
    return segments


def _dynamic_entries(payload: bytes, segment: tuple[int, ...]) -> list[tuple[int, int]]:
    start, length = segment[2], segment[5]
    if length % 16:
        raise ProjectRuntimeError("project_native_elf_invalid:dynamic segment size")
    entries = []
    for position in range(start, start + length, 16):
        tag, value = struct.unpack_from("<QQ", payload, position)
        if tag == 0:  # DT_NULL
            return entries
        entries.append((tag, value))
    raise ProjectRuntimeError("project_native_elf_invalid:unterminated dynamic segment")


def _dynamic_value(entries: list[tuple[int, int]], requested: int) -> int:
    values = [value for tag, value in entries if tag == requested]
    if len(values) != 1:
        raise ProjectRuntimeError("project_native_elf_invalid:dynamic string table metadata")
    return values[0]


def _segment_string_table(payload: bytes, segments: list[tuple[int, ...]], entries: list[tuple[int, int]]) -> bytes:
    address = _dynamic_value(entries, 5)  # DT_STRTAB
    length = _dynamic_value(entries, 10)  # DT_STRSZ
    offsets = {
        segment[2] + address - segment[3]
        for segment in segments
        if segment[0] == 1 and segment[3] <= address and address + length <= segment[3] + segment[5]
    }
    if len(offsets) != 1:
        raise ProjectRuntimeError("project_native_elf_invalid:dynamic string table mapping")
    start = offsets.pop()
    return payload[start : start + length]


def _segment_needed_names(payload: bytes) -> list[str]:
    segments = _elf_segments(payload)
    dynamic = [segment for segment in segments if segment[0] == 2]
    if not dynamic:
        return []
    if len(dynamic) != 1:
        raise ProjectRuntimeError("project_native_elf_invalid:multiple dynamic segments")
    entries = _dynamic_entries(payload, dynamic[0])
    needed = [value for tag, value in entries if tag == 1]
    if not needed:
        return []
    table = _segment_string_table(payload, segments, entries)
    return [_dependency_name(table, offset) for offset in needed]


@ensure(lambda result: result == tuple(sorted(set(result))))
def elf_dependencies(path: Path) -> tuple[str, ...]:
    """Read ELF64 DT_NEEDED names from sections or sectionless program segments."""
    payload = path.read_bytes()
    if not payload.startswith(b"\x7fELF"):
        return ()
    sections = _elf_sections(payload, path.name)
    names = [] if sections else _segment_needed_names(payload)
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


def _macho_system_path(path: Path) -> bool:
    return (
        path.is_absolute() and ".." not in path.parts and any(path.is_relative_to(root) for root in _MACHO_SYSTEM_ROOTS)
    )


def _macho_contained(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ProjectRuntimeError(f"project_native_macho_load_path_escape:{path}")
    return resolved


def _expand_macho_path(value: str, *, loader: Path, executable: Path | None, root: Path) -> Path:
    contexts = {"@loader_path": loader.parent, "@executable_path": executable.parent if executable else None}
    for token, context in contexts.items():
        if value == token or value.startswith(token + "/"):
            if context is None:
                raise ProjectRuntimeError(f"project_native_macho_executable_context_missing:{value}")
            suffix = value[len(token) :].lstrip("/")
            return _macho_contained(context / suffix, root)
    candidate = Path(value)
    if not candidate.is_absolute():
        raise ProjectRuntimeError(f"project_native_macho_unresolved_load_path:{value}")
    if _macho_system_path(candidate):
        return candidate
    raise ProjectRuntimeError(f"project_native_macho_absolute_load_path:{value}")


def _resolve_macho_load(
    name: str,
    *,
    loader: Path,
    executable: Path | None,
    rpaths: tuple[Path, ...],
    root: Path,
    images: dict[Path, dict[str, Any]],
) -> Path:
    if name.startswith("@rpath/"):
        suffix = name[len("@rpath/") :]
        if not suffix or suffix.startswith("/") or ".." in Path(suffix).parts:
            raise ProjectRuntimeError(f"project_native_macho_load_path_escape:{name}")
        candidates = [
            path / suffix if _macho_system_path(path) else _macho_contained(path / suffix, root) for path in rpaths
        ]
    elif name == "@rpath" or (name.startswith("@") and not name.startswith(("@loader_path", "@executable_path"))):
        raise ProjectRuntimeError(f"project_native_macho_unresolved_load_path:{name}")
    else:
        candidates = [_expand_macho_path(name, loader=loader, executable=executable, root=root)]
    for candidate in candidates:
        if _macho_system_path(candidate):
            return candidate
        resolved = candidate.resolve(strict=False)
        if resolved.exists():
            image = images.get(resolved)
            if image is None or image["filetype"] != 6:
                raise ProjectRuntimeError(f"project_native_macho_dependency_not_dylib:{name}:{resolved}")
            return resolved
    raise ProjectRuntimeError(f"project_native_macho_dependency_missing:{name}:{loader.relative_to(root)}")


def _macho_resolutions(images: dict[Path, dict[str, Any]], root: Path) -> dict[Path, tuple[str, ...]]:
    resolved: dict[Path, set[str]] = {path: set() for path in images}
    reached: set[Path] = set()

    def visit(loader: Path, executable: Path | None, inherited: tuple[Path, ...], chain: tuple[Path, ...]) -> None:
        if loader in chain:
            return
        reached.add(loader)
        image = images[loader]
        local_rpaths = tuple(
            _expand_macho_path(value, loader=loader, executable=executable, root=root) for value in image["rpaths"]
        )
        rpaths = (*local_rpaths, *inherited)
        for dependency in image["needed"]:
            target = _resolve_macho_load(
                dependency,
                loader=loader,
                executable=executable,
                rpaths=rpaths,
                root=root,
                images=images,
            )
            relative = str(target) if _macho_system_path(target) else target.relative_to(root).as_posix()
            resolved[loader].add(relative)
            if not _macho_system_path(target):
                visit(target, executable, rpaths, (*chain, loader))

    for path, image in sorted(images.items()):
        if image["filetype"] == 2:
            visit(path, path, (), ())
    for path in sorted(images):
        if path not in reached:
            visit(path, None, (), ())
    return {
        path: tuple(sorted(values, key=lambda value: (value.startswith("/"), value)))
        for path, values in resolved.items()
    }


def _macho_candidates(artifact: Path) -> list[Path]:
    regular_files = {path for path in artifact.rglob("*") if path.is_file()}
    executable_files = {path for path in regular_files if path.stat().st_mode & 0o111}
    header_images = set()
    for path in regular_files:
        with path.open("rb") as stream:
            prefix = stream.read(7)
        if _is_macho(prefix) or prefix.startswith(b"\x7fELF"):
            header_images.add(path)
    return sorted(
        executable_files
        | header_images
        | {
            path
            for pattern in ("*.dylib", "*.so*", "executables/*")
            for path in artifact.rglob(pattern)
            if path.is_file()
        }
    )


def _macho_inventory(artifact: Path, candidates: list[Path]) -> list[dict[str, Any]] | None:
    formats = {path: path.read_bytes()[:7] for path in candidates}
    macho = [path for path, prefix in formats.items() if _is_macho(prefix)]
    if not macho:
        return None
    if any(prefix.startswith(b"\x7fELF") for prefix in formats.values()):
        raise ProjectRuntimeError("project_native_architecture_mixed:ELF and Mach-O images")
    root = artifact.resolve()
    images: dict[Path, dict[str, Any]] = {}
    for path in macho:
        resolved = _macho_contained(path, root)
        images[resolved] = _macho_metadata(path)
    resolutions = _macho_resolutions(images, root)
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": content_digest(path.read_bytes()),
            "needed": image["needed"],
            "rpaths": image["rpaths"],
            "architectures": image["architectures"],
            "resolved": resolutions[path],
            "origin": "project",
        }
        for path, image in sorted(images.items())
    ]


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
    """Inventory native closures; copy only the established Linux ELF closure."""
    macho = _macho_inventory(artifact, _macho_candidates(artifact))
    if macho is not None:
        if declared:
            raise ProjectRuntimeError(
                "project_native_macho_declared_unsupported:dependencies must be encoded in Mach-O load commands"
            )
        if target_loader:
            raise ProjectRuntimeError("project_native_macho_loader_unsupported:dyld is supplied by macOS")
        return macho
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
