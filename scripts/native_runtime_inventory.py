#!/usr/bin/env python3
"""Read-only Mach-O inventory for stable local payloads, never an admission receipt.

Only exact arm64 slices are evaluated. System paths are permitted shared-cache
references, not proof of their availability. Runtime dlopen, signing, minimum OS
compatibility and concurrently mutated payloads are outside this static inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import stat
import subprocess
import sys
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO, Any, NamedTuple


MAX_ENTRIES = 10000
MAX_IMAGES = 512
MAX_BYTES = 512 * 1024 * 1024
MAX_OUTPUT = 4 * 1024 * 1024
MAX_CONTEXTS = 8192
ARCHITECTURES = {"arm64", "arm64e", "arm64e.x1", "arm64_32", "x86_64", "x86_64h", "i386"}
TOOL_TIMEOUT = 10.0
MAGICS = {
    bytes.fromhex(value)
    for value in ("feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")
}
LOADS = {"LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB", "LC_LAZY_LOAD_DYLIB"}
PASSIVE = {
    "LC_SEGMENT_64",
    "LC_SYMTAB",
    "LC_DYSYMTAB",
    "LC_UUID",
    "LC_BUILD_VERSION",
    "LC_VERSION_MIN_MACOSX",
    "LC_SOURCE_VERSION",
    "LC_MAIN",
    "LC_UNIXTHREAD",
    "LC_FUNCTION_STARTS",
    "LC_DATA_IN_CODE",
    "LC_CODE_SIGNATURE",
    "LC_DYLD_INFO",
    "LC_DYLD_INFO_ONLY",
    "LC_DYLD_EXPORTS_TRIE",
    "LC_DYLD_CHAINED_FIXUPS",
    "LC_TWOLEVEL_HINTS",
    "LC_LINKER_OPTION",
    "LC_SEGMENT_SPLIT_INFO",
    "LC_DYLIB_CODE_SIGN_DRS",
    "LC_LINKER_OPTIMIZATION_HINT",
    "LC_ROUTINES_64",
}


class InventoryError(ValueError):
    """Incomplete or unsafe static inventory evidence."""


def _read_inspection_output(stream: IO[bytes], argv: list[str], deadline: float) -> bytearray:
    output = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(stream, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise InventoryError(f"Inspection timeout: {argv[0]} {argv[-1]}")
            chunk = os.read(stream.fileno(), 65536)
            if not chunk:
                return output
            output.extend(chunk)
            if len(output) > MAX_OUTPUT:
                raise InventoryError("Inspection output limit exceeded")


def _inspect_process(process: subprocess.Popen[bytes], argv: list[str]) -> str:
    """Collect bounded output and always kill/reap an unfinished inspector."""
    try:
        deadline = time.monotonic() + TOOL_TIMEOUT
        assert process.stdout is not None
        output = _read_inspection_output(process.stdout, argv, deadline)
        code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if code:
            raise InventoryError(f"Inspection failed ({code}): {argv[-1]}: {output[:1024].decode(errors='replace')}")
        return output.decode("utf-8", errors="strict")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1)


def inspect_tool(argv: list[str]) -> str:
    """Run only Apple inspectors with bounded time/output and a clean environment."""
    if argv[0] not in {"/usr/bin/lipo", "/usr/bin/otool"}:
        raise InventoryError("Only absolute Apple inspection tools are allowed")
    try:
        with subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            cwd="/",
        ) as process:
            return _inspect_process(process, argv)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise InventoryError(f"Inspection failed: {argv[0]}: {exc}") from exc


def contained(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise InventoryError(f"Payload path/symlink escape: {path}")
    return resolved


def _bounded_entries(entries: Iterable[os.DirEntry[str]], limit: int) -> Iterator[os.DirEntry[str]]:
    """Consume at most the remaining budget plus the first rejected entry."""
    for count, entry in enumerate(entries, start=1):
        if count > limit:
            raise InventoryError("Payload entry limit exceeded")
        yield entry


def _scan_entry(entry: os.DirEntry[str], root: Path, pending: list[Path], files: list[Path], total: int) -> int:
    path = Path(entry.path)
    info = contained(path, root).stat()
    if stat.S_ISDIR(info.st_mode):
        if not entry.is_symlink():
            pending.append(path)
        return total
    if not stat.S_ISREG(info.st_mode):
        raise InventoryError(f"Not a regular payload file: {path}")
    if entry.is_symlink():
        return total  # Target is scanned under its canonical payload path.
    total += info.st_size
    if total > MAX_BYTES:
        raise InventoryError("Payload byte limit exceeded")
    files.append(path)
    return total


def payload_files(root: Path) -> list[Path]:
    """Enforce entry bounds during enumeration, before allocating directory lists."""
    files: list[Path] = []
    pending = [root]
    count = 0
    total = 0
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in _bounded_entries(entries, MAX_ENTRIES - count):
                count += 1
                total = _scan_entry(entry, root, pending, files, total)
    return sorted(files)


def command_value(block: str, field: str, size: int, minimum_offset: int = 24) -> str:
    matches = re.findall(rf"^\s*{field} (.+) \(offset (\d{{1,10}})\)\s*$", block, re.MULTILINE)
    if len(matches) != 1:
        raise InventoryError(f"Malformed {field} in load command")
    value, offset = matches[0]
    if not value or any(ord(char) < 32 for char in value) or not minimum_offset <= int(offset) < size:
        raise InventoryError(f"Invalid {field} in load command")
    if int(offset) + len(value.encode()) + 1 > size:
        raise InventoryError(f"Truncated {field} in load command")
    return value


def _command_header(output: str) -> tuple[str, int, int]:
    if re.search(r"^\s*(?:error:|warning:|truncated\s|unknown\s)", output, re.IGNORECASE | re.MULTILINE):
        raise InventoryError("Malformed inspection output: diagnostic present")
    headers = re.findall(
        r"^MH_MAGIC_64\s+ARM64\s+\S+\s+\S+\s+(EXECUTE|DYLIB|BUNDLE)\s+(\d{1,10})\s+(\d{1,10})[^\n]*$",
        output,
        re.MULTILINE,
    )
    if len(headers) != 1:
        raise InventoryError("Malformed or unsupported ARM64 Mach-O header")
    kind, count, command_bytes = headers[0]
    return kind, int(count), int(command_bytes)


def _command_frame(number: str, block: str, index: int) -> tuple[str, int]:
    cmds = re.findall(r"^\s*cmd (\S+)\s*$", block, re.MULTILINE)
    sizes = re.findall(r"^\s*cmdsize (\d{1,10})\s*$", block, re.MULTILINE)
    if int(number) != index or len(cmds) != 1 or len(sizes) != 1:
        raise InventoryError("Malformed load command framing")
    cmd, size = cmds[0], int(sizes[0])
    if size < 8 or size % 8:
        raise InventoryError("Malformed load command size")
    return cmd, size


def _record_command(result: dict[str, Any], cmd: str, block: str, size: int) -> None:
    if cmd in LOADS:
        result["dependencies"].append({"command": cmd, "name": command_value(block, "name", size)})
        return
    if cmd == "LC_RPATH":
        result["rpaths"].append(command_value(block, "path", size, 12))
        return
    if cmd == "LC_ID_DYLIB":
        if result["filetype"] != "DYLIB" or result["id"] is not None:
            raise InventoryError("Unexpected or duplicate library ID")
        result["id"] = command_value(block, "name", size)
        return
    if cmd == "LC_LOAD_DYLINKER":
        if command_value(block, "name", size, 12) != "/usr/lib/dyld":
            raise InventoryError("Non-system dynamic linker")
        return
    if cmd not in PASSIVE:
        raise InventoryError(f"Unsupported load command: {cmd}")


def parse_commands(output: str) -> dict[str, Any]:
    kind, count, command_bytes = _command_header(output)
    blocks = re.split(r"^Load command (\d{1,10})\s*$", output, flags=re.MULTILINE)
    if len(blocks) != 1 + 2 * count:
        raise InventoryError("Malformed load command count")
    result: dict[str, Any] = {"filetype": kind, "dependencies": [], "rpaths": [], "id": None}
    total = 0
    for index in range(count):
        number, block = blocks[1 + 2 * index : 3 + 2 * index]
        cmd, size = _command_frame(number, block, index)
        total += size
        _record_command(result, cmd, block, size)
    if total != command_bytes:
        raise InventoryError("Malformed total load command size")
    return result


def is_system(path: Path) -> bool:
    if ".." in path.parts:
        return False
    roots = (Path("/usr/lib"), Path("/System/Library/Frameworks"), Path("/System/Library/PrivateFrameworks"))
    return any(path.is_relative_to(root) and path.resolve().is_relative_to(root) for root in roots)


def expand_path(value: str, loader: Path, executable: Path | None, root: Path) -> Path:
    for token, context in (("@loader_path", loader), ("@executable_path", executable)):
        if value == token or value.startswith(token + "/"):
            if context is None:
                raise InventoryError(f"Missing executable context for {value}")
            return contained(context.parent / value[len(token) :].lstrip("/"), root)
    path = Path(value)
    if not path.is_absolute():
        raise InventoryError(f"Unresolved or ambient load path: {value}")
    return path if is_system(path) else contained(path, root)


class _LoadContext(NamedTuple):
    """Paths needed to expand one loader's dependencies in an executable context."""

    loader: Path
    executable: Path | None
    rpaths: list[Path]
    root: Path


def resolve_load(name: str, context: _LoadContext, images: dict[Path, dict[str, Any]]) -> Path:
    loader, executable, rpaths, root = context
    if name.startswith("@rpath/"):
        suffix = name[len("@rpath/") :]
        if not suffix or suffix.startswith("/") or ".." in Path(suffix).parts:
            raise InventoryError(f"Unsafe rpath load: {name}")
        candidates = [expand_path(str(path / suffix), loader, executable, root) for path in rpaths]
    else:
        candidates = [expand_path(name, loader, executable, root)]
    for candidate in candidates:
        if is_system(candidate):
            return candidate
        if candidate.exists():
            if candidate not in images or images[candidate]["filetype"] != "DYLIB":
                raise InventoryError(f"Dependency is not an inventoried Mach-O dylib: {candidate}")
            return candidate
    raise InventoryError(f"Unresolved dependency {name} loaded by {loader}")


def resolve_closure(images: dict[Path, dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    resolutions = []
    reached: set[Path] = set()
    visits = 0

    def visit(loader: Path, executable: Path | None, inherited: list[Path], chain: tuple[Path, ...]) -> None:
        nonlocal visits
        visits += 1
        if visits > MAX_CONTEXTS or len(chain) >= 128:
            raise InventoryError("Dependency context/depth limit exceeded")
        if loader in chain:
            return
        reached.add(loader)
        image = images[loader]
        rpaths = [expand_path(value, loader, executable, root) for value in image["rpaths"]] + inherited
        context = _LoadContext(loader, executable, rpaths, root)
        for dependency in image["dependencies"]:
            if len(resolutions) >= MAX_CONTEXTS:
                raise InventoryError("Dependency edge limit exceeded")
            target = resolve_load(dependency["name"], context, images)
            system = is_system(target)
            resolutions.append(
                {
                    "loader": str(loader.relative_to(root)),
                    "executable": str(executable.relative_to(root)) if executable else None,
                    **dependency,
                    "resolved": str(target) if system else str(target.relative_to(root)),
                    "system": system,
                }
            )
            if not system:
                visit(target, executable, rpaths, (*chain, loader))

    for path, image in images.items():
        if image["filetype"] == "EXECUTE":
            visit(path, path, [], ())
    for path in images:
        if path not in reached:
            visit(path, None, [], ())
    return resolutions


def _image_digest(path: Path, size: int, image_count: int) -> str | None:
    with path.open("rb") as stream:
        if stream.read(4) not in MAGICS:
            return None
        if image_count >= MAX_IMAGES:
            raise InventoryError("Mach-O image limit exceeded")
        stream.seek(0)
        digest = hashlib.sha256()
        read_bytes = 0
        while chunk := stream.read(65536):
            read_bytes += len(chunk)
            if read_bytes > min(size, MAX_BYTES):
                raise InventoryError(f"Payload grew beyond byte limit: {path}")
            digest.update(chunk)
    return digest.hexdigest()


def _image_architectures(path: Path) -> list[str]:
    architectures = inspect_tool(["/usr/bin/lipo", "-archs", str(path)]).split()
    if (
        not architectures
        or len(set(architectures)) != len(architectures)
        or any(arch not in ARCHITECTURES for arch in architectures)
    ):
        raise InventoryError(f"Malformed architecture output: {path}")
    if "arm64" not in architectures:
        raise InventoryError(f"Missing exact arm64 architecture slice: {path}: {architectures}")
    return architectures


def _inspect_image(path: Path, root: Path, image_count: int) -> dict[str, Any] | None:
    before = path.stat()
    digest = _image_digest(path, before.st_size, image_count)
    if digest is None:
        return None
    architectures = _image_architectures(path)
    image = parse_commands(inspect_tool(["/usr/bin/otool", "-arch", "arm64", "-hv", "-l", str(path)]))
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise InventoryError(f"Payload changed during inspection: {path}")
    return {
        "path": str(path.relative_to(root)),
        "sha256": digest,
        "architectures": architectures,
        **image,
    }


def inventory(payload: Path) -> dict[str, Any]:
    """Inspect a directory without loading or executing its images."""
    try:
        root = payload.resolve(strict=True)
        if not root.is_dir():
            raise InventoryError("Payload must be a directory")
        images = {}
        for path in payload_files(root):
            image = _inspect_image(path, root, len(images))
            if image is not None:
                images[path] = image
        if not images:
            raise InventoryError("No Mach-O images found")
        return {
            "ok": True,
            "kind": "static-macho-inventory",
            "production_eligible": False,
            "sandbox_verified": False,
            "images": list(images.values()),
            "resolutions": resolve_closure(images, root),
        }
    except (OSError, RuntimeError) as exc:
        raise InventoryError(f"Cannot inspect payload: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path, help="Stable local payload directory to inspect; never executed")
    args = parser.parse_args(argv)
    try:
        result = inventory(args.payload)
    except InventoryError as exc:
        result = {"ok": False, "production_eligible": False, "sandbox_verified": False, "errors": [str(exc)]}
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
