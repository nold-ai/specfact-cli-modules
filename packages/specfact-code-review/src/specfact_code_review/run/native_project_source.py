"""Data-only acquisition and byte authentication for exact locked HTTPS Git inputs.

Only the sealed acquisition worker calls acquire(). Builds run separately in the
existing network-denied hook worker. No Git command or source code is executed.
"""

from __future__ import annotations

import hashlib
import json
import re
import ssl
import stat
import tarfile
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

from specfact_code_review.run.runtime_models import ProjectRuntimeError


SCHEMA = "native-locked-git-v1"
REQUEST_SCHEMA = "native-git-acquisition-v1"
BINDING_SCHEMA = "native-poetry-source-wheel-v1"
MAX_FILES = 20000
MAX_BYTES = 128 << 20
MAX_SOURCES = 64
_HEX = re.compile(r"[0-9a-f]{40}")


def _path(value: str, *, empty: bool = False) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or (not value and not empty)
        or len(value.encode()) > 512
        or value.startswith("/")
        or "\\" in value
        or "\0" in value
        or any(part in {"", ".", ".."} for part in value.split("/") if value)
    ):
        raise ProjectRuntimeError("project_native_source_request_invalid:path")
    return PurePosixPath(value)


def validate_declaration(value: Any) -> dict[str, str]:
    fields = {"schema", "name", "version", "url", "reference", "commit", "subdirectory"}
    if not isinstance(value, dict) or set(value) != fields or any(not isinstance(v, str) for v in value.values()):
        raise ProjectRuntimeError("project_native_source_request_invalid")
    parsed = urlsplit(value["url"])
    if (
        value["schema"] != SCHEMA
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value["name"])
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.query
        or parsed.fragment
        or len(value["url"]) > 2048
        or not _HEX.fullmatch(value["commit"])
        or not 0 < len(value["reference"]) <= 256
    ):
        raise ProjectRuntimeError("project_native_source_request_invalid")
    _path(parsed.path.removeprefix("/"))
    _path(value["subdirectory"], empty=True)
    try:
        Version(value["version"])
    except ValueError as exc:
        raise ProjectRuntimeError("project_native_source_request_invalid:version") from exc
    return {**value, "name": canonicalize_name(value["name"])}


def git_hash(kind: str, payload: bytes) -> str:
    return hashlib.sha1(f"{kind} {len(payload)}\0".encode() + payload, usedforsecurity=False).hexdigest()


def _file(path: Path) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
        raise ProjectRuntimeError("project_native_source_tree_invalid:file")
    return path.read_bytes()


def verify_tree(root: Path, tree: str, entries: list[dict[str, Any]], *, check_modes: bool = True) -> dict[str, Any]:
    """Reconstruct every Git blob/tree identity, including executable modes."""
    if not _HEX.fullmatch(tree) or not isinstance(entries, list) or len(entries) > MAX_FILES:
        raise ProjectRuntimeError("project_native_source_tree_invalid")
    records = {}
    folded = set()
    for entry in entries:
        path = _path(entry["path"]).as_posix()
        if path.casefold() in folded or not _HEX.fullmatch(entry.get("sha", "")):
            raise ProjectRuntimeError("project_native_source_tree_invalid")
        folded.add(path.casefold())
        if (entry.get("mode"), entry.get("type")) not in {("100644", "blob"), ("100755", "blob"), ("040000", "tree")}:
            raise ProjectRuntimeError("project_native_source_tree_invalid:links and submodules unsupported")
        records[path] = entry
    actual = set()
    inventory = {}
    total = 0
    for file in root.rglob("*"):
        relative = file.relative_to(root).as_posix()
        metadata = file.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            if records.get(relative, {}).get("type") != "tree":
                raise ProjectRuntimeError("project_native_source_tree_mismatch:unexpected directory")
            continue
        payload = _file(file)
        total += len(payload)
        if total > MAX_BYTES or len(actual) >= MAX_FILES:
            raise ProjectRuntimeError("project_native_source_tree_invalid:bounds")
        if payload.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            raise ProjectRuntimeError("project_native_source_lfs_unsupported")
        entry = records.get(relative)
        mode = "100755" if metadata.st_mode & 0o111 else "100644"
        if (
            not entry
            or entry["type"] != "blob"
            or (check_modes and entry["mode"] != mode)
            or git_hash("blob", payload) != entry["sha"]
        ):
            raise ProjectRuntimeError("project_native_source_tree_mismatch:blob")
        actual.add(relative)
        inventory[relative] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
            "mode": entry["mode"],
        }
    if actual != {name for name, entry in records.items() if entry["type"] == "blob"}:
        raise ProjectRuntimeError("project_native_source_tree_mismatch:missing files")
    trees = {"": tree, **{name: entry["sha"] for name, entry in records.items() if entry["type"] == "tree"}}
    children: dict[str, list[tuple[bytes, bytes]]] = {name: [] for name in trees}
    for name, entry in records.items():
        path = PurePosixPath(name)
        parent = "" if path.parent == PurePosixPath(".") else path.parent.as_posix()
        if parent not in children:
            raise ProjectRuntimeError("project_native_source_tree_invalid:missing parent")
        directory = entry["type"] == "tree"
        mode = "40000" if directory else entry["mode"]
        leaf = path.name.encode()
        children[parent].append(
            (leaf + (b"/" if directory else b""), mode.encode() + b" " + leaf + b"\0" + bytes.fromhex(entry["sha"]))
        )
    for name, expected in trees.items():
        content = b"".join(value for _, value in sorted(children[name]))
        if git_hash("tree", content) != expected:
            raise ProjectRuntimeError("project_native_source_tree_mismatch:tree")
    return inventory


def extract_archive(archive: Path, destination: Path) -> None:
    """Extract a bounded commit archive, never trusting links or member paths."""
    destination.mkdir(mode=0o700)
    seen = set()
    total = 0
    prefix = None
    try:
        with tarfile.open(archive, "r:gz") as stream:
            for index, member in enumerate(stream):
                path = _path(member.name.rstrip("/"))
                if index >= MAX_FILES or not (member.isfile() or member.isdir()):
                    raise ProjectRuntimeError("project_native_source_archive_invalid")
                if prefix is None:
                    prefix = path.parts[0]
                if path.parts[0] != prefix:
                    raise ProjectRuntimeError("project_native_source_archive_invalid")
                if len(path.parts) == 1:
                    if not member.isdir():
                        raise ProjectRuntimeError("project_native_source_archive_invalid")
                    continue
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                if relative.casefold() in seen:
                    raise ProjectRuntimeError("project_native_source_archive_invalid")
                seen.add(relative.casefold())
                target = destination / relative
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                    continue
                total += member.size
                if member.size < 0 or total > MAX_BYTES:
                    raise ProjectRuntimeError("project_native_source_archive_invalid:bounds")
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                data = stream.extractfile(member)
                if data is None:
                    raise ProjectRuntimeError("project_native_source_archive_invalid")
                payload = data.read(member.size + 1)
                if len(payload) != member.size:
                    raise ProjectRuntimeError("project_native_source_archive_invalid")
                with target.open("xb") as output:
                    output.write(payload)
                target.chmod(0o700 if member.mode & 0o111 else 0o600)
    except (ValueError, OSError, tarfile.TarError) as exc:
        raise ProjectRuntimeError("project_native_source_archive_invalid") from exc


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _fetch(url: str, limit: int) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "SpecFact-locked-source-v1", "Accept": "application/vnd.github+json"}
    )
    import certifi

    context = ssl.create_default_context(cafile=certifi.where())
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(), urllib.request.HTTPSHandler(context=context)
    )
    with opener.open(request, timeout=60) as response:
        payload = response.read(limit + 1)
        if response.status != 200 or len(payload) > limit or response.geturl() != url:
            raise ProjectRuntimeError("project_native_source_fetch_invalid:bounds or redirect")
        return payload


def acquire(declaration: dict[str, str], output: Path) -> dict[str, Any]:
    """Run only in the sealed data-only acquisition domain."""
    declaration = validate_declaration(declaration)
    parsed = urlsplit(declaration["url"])
    parts = parsed.path.strip("/").removesuffix(".git").split("/")
    if (
        parsed.hostname != "github.com"
        or len(parts) != 2
        or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts)
    ):
        raise ProjectRuntimeError("project_native_source_transport_unsupported:require admitted GitHub HTTPS transport")
    repo = "/".join(parts)
    commit = declaration["commit"]
    metadata = json.loads(_fetch(f"https://api.github.com/repos/{repo}/git/commits/{commit}", 1 << 20))
    if metadata.get("sha") != commit or not _HEX.fullmatch(metadata.get("tree", {}).get("sha", "")):
        raise ProjectRuntimeError("project_native_source_commit_mismatch")
    tree = metadata["tree"]["sha"]
    result = json.loads(_fetch(f"https://api.github.com/repos/{repo}/git/trees/{tree}?recursive=1", 16 << 20))
    if result.get("sha") != tree or result.get("truncated") is not False:
        raise ProjectRuntimeError("project_native_source_tree_invalid:truncated or mismatched API tree")
    output.mkdir(mode=0o700, exist_ok=True)
    archive = output / "source.tar.gz"
    archive.write_bytes(_fetch(f"https://codeload.github.com/{repo}/tar.gz/{commit}", MAX_BYTES))
    extract_archive(archive, output / "source")
    inventory = verify_tree(output / "source", tree, result["tree"])
    receipt = {
        "schema": REQUEST_SCHEMA,
        "declaration": declaration,
        "tree": tree,
        "entries": result["tree"],
        "archive_sha256": hashlib.sha256(_file(archive)).hexdigest(),
        "inventory": inventory,
    }
    (output / "source-receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    return receipt


def verify_acquired(root: Path, declaration: dict[str, str]) -> dict[str, Any]:
    """Fresh controller verification before any source is admitted to a build."""
    path = root / "source-receipt.json"
    if len(_file(path)) > 16 << 20:
        raise ProjectRuntimeError("project_native_source_receipt_invalid")
    receipt = json.loads(path.read_text())
    if (
        set(receipt) != {"schema", "declaration", "tree", "entries", "archive_sha256", "inventory"}
        or receipt["schema"] != REQUEST_SCHEMA
        or receipt["declaration"] != validate_declaration(declaration)
        or receipt["archive_sha256"] != hashlib.sha256(_file(root / "source.tar.gz")).hexdigest()
        or receipt["inventory"] != verify_tree(root / "source", receipt["tree"], receipt["entries"], check_modes=False)
    ):
        raise ProjectRuntimeError("project_native_source_receipt_invalid")
    return receipt


def bind_wheel(wheel: Path, declaration: dict[str, str], receipt: dict[str, Any]) -> dict[str, Any]:
    """Inspect after hook exit; only pure Python, compatible wheels are admitted."""
    name, version, _, tags = parse_wheel_filename(wheel.name)
    declaration = validate_declaration(declaration)
    if (
        name != declaration["name"]
        or version != Version(declaration["version"])
        or any(tag.abi != "none" or tag.platform != "any" for tag in tags)
    ):
        raise ProjectRuntimeError("project_native_source_wheel_invalid:name/version or nonpure wheel")
    payload = _file(wheel)
    with zipfile.ZipFile(wheel) as archive:
        metadata_files = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        wheel_files = [name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")]
        if (
            len(metadata_files) != 1
            or len(wheel_files) != 1
            or any(archive.getinfo(name).file_size > 1 << 20 for name in [*metadata_files, *wheel_files])
        ):
            raise ProjectRuntimeError("project_native_source_wheel_invalid:metadata")
        metadata = BytesParser().parsebytes(archive.read(metadata_files[0]))
        layout = BytesParser().parsebytes(archive.read(wheel_files[0]))
        if (
            canonicalize_name(metadata.get("Name", "")) != declaration["name"]
            or metadata.get("Version") != declaration["version"]
            or layout.get("Root-Is-Purelib", "").lower() != "true"
        ):
            raise ProjectRuntimeError("project_native_source_wheel_invalid:metadata identity")
        total = 0
        for member in archive.infolist():
            _path(member.filename.rstrip("/"))
            total += member.file_size
            if total > MAX_BYTES or len(archive.infolist()) > MAX_FILES or stat.S_ISLNK(member.external_attr >> 16):
                raise ProjectRuntimeError("project_native_source_wheel_invalid:bounds or link")
            if not member.is_dir():
                head = archive.read(member)[:4]
                if (
                    member.filename.endswith((".so", ".dylib", ".dll", ".exe"))
                    or head in {b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"}
                    or head[:2] == b"MZ"
                ):
                    raise ProjectRuntimeError("project_native_source_wheel_invalid:native member")
    return {
        "schema": BINDING_SCHEMA,
        "declaration": declaration,
        "tree": receipt["tree"],
        "inventory_sha256": hashlib.sha256(json.dumps(receipt["inventory"], sort_keys=True).encode()).hexdigest(),
        "wheel": wheel.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def bound_wheel(wheelhouse: Path, package: Any, bindings: list[dict[str, Any]]) -> Path:
    """Match the original Poetry Git Package; do not alter its source fields."""
    declaration = package_declaration(package)
    matches = [
        value for value in bindings if value.get("schema") == BINDING_SCHEMA and value.get("declaration") == declaration
    ]
    if len(matches) != 1:
        raise ProjectRuntimeError("project_native_source_wheel_binding_missing")
    binding = matches[0]
    if set(binding) != {"schema", "declaration", "tree", "inventory_sha256", "wheel", "sha256"} or not _HEX.fullmatch(
        binding["tree"]
    ):
        raise ProjectRuntimeError("project_native_source_wheel_binding_invalid")
    filename = binding["wheel"]
    if not isinstance(filename, str) or Path(filename).name != filename or wheelhouse.resolve() != wheelhouse:
        raise ProjectRuntimeError("project_native_source_wheel_binding_invalid")
    path = wheelhouse / filename
    name, version, _, _ = parse_wheel_filename(filename)
    if (
        name != declaration["name"]
        or version != Version(declaration["version"])
        or hashlib.sha256(_file(path)).hexdigest() != binding["sha256"]
    ):
        raise ProjectRuntimeError("project_native_source_wheel_binding_invalid:wheel bytes")
    return path


def package_declaration(package: Any) -> dict[str, str]:
    if package.source_type != "git" or getattr(package, "develop", False):
        raise ProjectRuntimeError("project_native_dependency_source_unsupported:require noneditable locked HTTPS Git")
    return validate_declaration(
        {
            "schema": SCHEMA,
            "name": package.name,
            "version": str(package.version),
            "url": package.source_url,
            "reference": package.source_reference,
            "commit": package.source_resolved_reference,
            "subdirectory": package.source_subdirectory or "",
        }
    )
