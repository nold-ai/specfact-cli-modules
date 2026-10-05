"""Package pinned native Node/BasedPyright inputs offline; never execute or admit them."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import shutil
import struct
import sys
import tarfile
import unicodedata
from pathlib import Path
from typing import Any


NODE_VERSION = "24.16.0"
NODE_PREFIX = f"node-v{NODE_VERSION}-darwin-arm64"
NODE_SHA256 = "39189dab4eeb15706c424af0ac08a3044c9e48f7db12a7d77f6b7aafc7dd5df6"
NPM_VERSION = "1.39.10"
NPM_INTEGRITY = "sha512-9NTfbegeSey8Trhaf+Tr8++Uo/UFCtsUMzpvXA/seDfSTN3kOwfmPJ4lf/tjxPjVlr/fsHo34W9/qW+ZF+b6kg=="
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 12000


def pinned_bytes(path: Path, algorithm: str, expected: str) -> bytes:
    """Read a bounded archive and authenticate its exact bytes before parsing."""
    with path.open("rb") as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("archive size limit exceeded")
    digest = hashlib.new(algorithm, data)
    actual = digest.hexdigest() if algorithm == "sha256" else "sha512-" + base64.b64encode(digest.digest()).decode()
    if actual != expected:
        raise ValueError(f"{path.name}: input digest mismatch")
    return data


def canonical_path(name: str) -> str:
    """Reject path spellings unsafe for ordinary case-insensitive macOS storage."""
    name = name.removesuffix("/")
    if (
        not name
        or "\\" in name
        or any(ord(character) < 32 for character in name)
        or any(part in ("", ".", "..") for part in name.split("/"))
        or unicodedata.normalize("NFC", name) != name
    ):
        raise ValueError("unsafe archive path")
    return name


def selected_name(name: str, node: bool) -> str | None:
    """Select only the runtime executable/license or the pinned npm package."""
    if node:
        return {f"{NODE_PREFIX}/bin/node": "bin/node", f"{NODE_PREFIX}/LICENSE": "licenses/node.txt"}.get(name)
    if not name.startswith("package/"):
        raise ValueError("unexpected npm archive root")
    return "basedpyright/" + name.removeprefix("package/")


def _account_member(member: tarfile.TarInfo, seen: set[str], total: int) -> tuple[str, int]:
    """Validate every archive path and charge its size before payload selection."""
    name = canonical_path(member.name)
    key = name.casefold()
    if key in seen or len(seen) >= MAX_MEMBERS:
        raise ValueError("duplicate/case-colliding path or member count limit")
    seen.add(key)
    total += member.size
    if member.size < 0 or total > MAX_EXPANDED_BYTES:
        raise ValueError("expanded archive size limit exceeded")
    return name, total


def _read_regular_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    """Read selected regular bytes only after checking kind and permission bits."""
    if not member.isfile() or member.issparse() or member.mode & 0o7000:
        raise ValueError("selected payload contains links, special files or unsafe modes")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("missing member data")
    content = stream.read(member.size + 1)
    if len(content) != member.size:
        raise ValueError("truncated member data")
    return content


def payload_files(data: bytes, *, node: bool) -> dict[str, tuple[bytes, int]]:
    """Copy regular-file bytes only; never invoke TAR extraction or input scripts."""
    files: dict[str, tuple[bytes, int]] = {}
    seen: set[str] = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            name, total = _account_member(member, seen, total)
            if member.isdir():
                continue
            target = selected_name(name, node)
            if target is None:
                continue
            content = _read_regular_member(archive, member)
            files[target] = (content, 0o755 if target == "bin/node" else 0o644)
    return files


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Avoid ambiguous npm metadata from duplicate JSON keys."""
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate metadata key")
        value[key] = item
    return value


def _validate_node_binary(node: bytes) -> None:
    """Check the thin ARM64 executable header and load-command bounds."""
    if len(node) < 32:
        raise ValueError("Node is not a thin ARM64 Mach-O executable")
    magic, cpu, _, kind, commands, command_bytes, _, _ = struct.unpack("<8I", node[:32])
    if (
        magic != 0xFEEDFACF
        or cpu != 0x100000C
        or kind != 2
        or command_bytes > len(node) - 32
        or commands > command_bytes // 8
    ):
        raise ValueError("Node is not a valid ARM64 Mach-O executable")


def _validate_npm_metadata(content: bytes) -> None:
    """Require the pinned package identity, entrypoint and dependency closure."""
    meta = json.loads(content, object_pairs_hook=unique_object)
    if not isinstance(meta, dict):
        raise ValueError("unsupported BasedPyright metadata")
    if meta.get("name") != "basedpyright" or meta.get("version") != NPM_VERSION or meta.get("license") != "MIT":
        raise ValueError("unsupported BasedPyright metadata")
    entrypoints = meta.get("bin")
    if not isinstance(entrypoints, dict) or entrypoints.get("basedpyright") != "index.js":
        raise ValueError("unsupported BasedPyright metadata")
    if meta.get("dependencies") or meta.get("optionalDependencies") != {"fsevents": "~2.3.3"}:
        raise ValueError("unsupported BasedPyright metadata")


def _validate_payload_paths(files: dict[str, tuple[bytes, int]]) -> None:
    """Ensure no selected file must also serve as a payload directory."""
    for name in files:
        parents = (str(path) for path in Path(name).parents if str(path) != ".")
        if any(parent in files for parent in parents):
            raise ValueError("file/directory path conflict")


def validate_payload(files: dict[str, tuple[bytes, int]]) -> None:
    """Verify native identity and the supported one-shot npm dependency contract."""
    required = {
        "bin/node",
        "licenses/node.txt",
        "basedpyright/package.json",
        "basedpyright/index.js",
        "basedpyright/LICENSE.txt",
    }
    if not required.issubset(files):
        raise ValueError("missing required payload file")
    _validate_node_binary(files["bin/node"][0])
    _validate_npm_metadata(files["basedpyright/package.json"][0])
    _validate_payload_paths(files)


def package(node_archive: Path, npm_archive: Path, output: Path) -> dict[str, Any]:
    """Materialize verified inputs into a new private directory, cleaning failures."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    node = pinned_bytes(node_archive, "sha256", NODE_SHA256)
    npm = pinned_bytes(npm_archive, "sha512", NPM_INTEGRITY)
    files = payload_files(node, node=True) | payload_files(npm, node=False)
    validate_payload(files)
    manifest: dict[str, Any] = {
        "schema": "specfact-native-node-input-v1",
        "experimental": True,
        "dependency_admitted": False,
        "production_eligible": False,
        "platform": "darwin-arm64",
        "inputs": {
            "node_version": NODE_VERSION,
            "node_sha256": NODE_SHA256,
            "basedpyright_version": NPM_VERSION,
            "basedpyright_integrity": NPM_INTEGRITY,
        },
        "tools": {"basedpyright": ["bin/node", "basedpyright/index.js"]},
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "mode": mode}
            for name, (data, mode) in sorted(files.items())
        },
    }
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        for name, (content, mode) in sorted(files.items()):
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(mode)
        (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(output)
        raise
    return manifest


def basedpyright_argv(root: Path) -> tuple[str, str]:
    """Locate explicit packaged tools; this does not verify or launch a cache."""
    root = root.resolve(strict=True)
    return str(root / "bin/node"), str(root / "basedpyright/index.js")


def main() -> int:
    """Prepare local maintainer inputs; no network, installer or tool execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-archive", required=True, type=Path)
    parser.add_argument("--basedpyright-archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = package(args.node_archive, args.basedpyright_archive, args.output)
    except (ValueError, OSError, tarfile.TarError) as exc:
        parser.exit(2, f"Native input packaging failed: {exc}\n")
    sys.stdout.write(
        json.dumps(
            {"output": str(args.output.resolve()), "files": len(manifest["files"]), "production_eligible": False}
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
