"""Experimental authenticated Darwin cache acquisition; never executes a payload.

The caller pins public trust and exact backend/policy selections independently.
Reader factories return closeable binary streams with bounded read(n) semantics.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tarfile
import uuid
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, BinaryIO

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from macos_capsule_candidate import _json, _physical_members


MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 256
MAX_MANIFEST = 256 * 1024
CHUNK = 64 * 1024
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class IncompleteError(ValueError):
    """Capability failure that cannot become successful execution evidence."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.evidence = {
            "status": "INCOMPLETE",
            "capability": "native-cache-v1",
            "reason": reason,
            "production_eligible": False,
            "artifact_publication_production": False,
        }


class Lease:
    """Own verified file/directory descriptors until explicitly closed.

    Descriptor consumers survive path replacement. In-place inode mutation and
    native loader handoff still require independent immutable image admission.
    """

    def __init__(self, path: Path, identity: str, fds: dict[str, int], directories: list[int]):
        self.path, self.identity, self.fds = path, identity, fds
        self._directories = directories
        self.code_identities = {name: (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for name, fd in fds.items()}
        self.evidence = {
            "status": "VERIFIED_CACHE_CANDIDATE",
            "identity": identity,
            "production_eligible": False,
            "artifact_publication_production": False,
            "execution_race_closed": False,
            "native_execution_performed": False,
        }

    def close(self) -> None:
        """Release handles; repeated close is harmless."""
        for fd in [*self.fds.values(), *self._directories]:
            os.close(fd)
        self.fds.clear()
        self._directories.clear()

    def __enter__(self) -> Lease:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _sha(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _fields(value: Any, fields: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("unexpected or missing manifest fields/descriptors")


def _number(value: Any, maximum: int) -> None:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("invalid bounded integer")


def _digest(value: Any) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("invalid SHA-256 digest")


def _name(value: Any) -> None:
    # Conservative ASCII profile avoids Unicode and case-insensitive aliases.
    if (
        not isinstance(value, str)
        or len(value) > 240
        or len(value.split("/")) > 16
        or any(re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", part) is None for part in value.split("/"))
    ):
        raise ValueError("noncanonical or alias-prone payload path")


def _authenticate(payload: bytes, signature: str, public_key: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_MANIFEST or len(signature) > 16384 or len(public_key) > 16384:
        raise ValueError("manifest/signature/public key byte limit")
    try:
        key = serialization.load_pem_public_key(public_key)
        raw = base64.b64decode(signature, validate=True)
        if isinstance(key, ed25519.Ed25519PublicKey):
            key.verify(raw, payload)
        elif isinstance(key, rsa.RSAPublicKey):
            key.verify(raw, payload, padding.PKCS1v15(), hashes.SHA256())
        else:
            raise ValueError("unsupported signature key (RSA or Ed25519 required)")
    except InvalidSignature as exc:
        raise ValueError("SpecFact signature validation failed") from exc
    return _json(payload)


def _manifest(document: dict[str, Any], abi: str, backend: str, policy: str) -> None:
    _fields(
        document,
        {"schema", "os", "architecture", "abi", "backend", "policy", "archive", "files", "closure", "closure_sha256"},
    )
    if (
        document["schema"] != "specfact-native-cache-v1"
        or document["os"] != "darwin"
        or document["architecture"] != "arm64"
        or abi not in {"3.11", "3.12", "3.13"}
        or document["abi"] != abi
    ):
        raise ValueError("unsupported platform/schema/ABI binding")
    if not backend or not policy or document["backend"] != backend or document["policy"] != policy:
        raise IncompleteError("backend/policy incompatible; install a matching native consumer and approved manifest")
    archive = document["archive"]
    _fields(archive, {"size", "sha256"})
    _number(archive["size"], MAX_BYTES)
    _digest(archive["sha256"])
    files = document["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("invalid file count")
    total = 0
    parents = set()
    for name, record in files.items():
        _name(name)
        _fields(record, {"size", "sha256", "mode"})
        _number(record["size"], MAX_BYTES)
        _digest(record["sha256"])
        if type(record["mode"]) is not int or record["mode"] not in {0o400, 0o500}:
            raise ValueError("payload modes must be owner-read-only or owner-executable")
        total += record["size"]
        parents.update(str(parent) for parent in Path(name).parents if str(parent) != ".")
    if total > MAX_BYTES or len(parents) > MAX_FILES or set(files) & parents:
        raise ValueError("payload size or parent/file collision")
    closure = document["closure"]
    if not isinstance(closure, dict) or not 1 <= len(closure) <= MAX_FILES:
        raise ValueError("invalid component closure")
    members = []
    for component, paths in closure.items():
        _name(component)
        if not isinstance(paths, list) or not paths or len(paths) > MAX_FILES:
            raise ValueError("invalid component file closure")
        for name in paths:
            _name(name)
        members.extend(paths)
    if len(members) != len(set(members)) or set(members) != set(files):
        raise ValueError("component closure must partition all signed files")
    _digest(document["closure_sha256"])
    if _sha(_canonical(closure)) != document["closure_sha256"]:
        raise ValueError("closure digest mismatch")


def _private(fd: int) -> None:
    metadata = os.fstat(fd)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ValueError("cache directory must be owner-owned mode 0700")


def _root(path: Path) -> int:
    """Anchor each absolute component; never resolve/follow a symlink."""
    path = path.absolute()
    fd = os.open("/", DIRECTORY_FLAGS)
    try:
        for index, part in enumerate(path.parts[1:]):
            if part in {".", ".."}:
                raise ValueError("noncanonical cache root")
            if index == len(path.parts[1:]) - 1:
                with suppress(FileExistsError):
                    os.mkdir(part, 0o700, dir_fd=fd)
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        _private(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _download(reader: Callable[[], BinaryIO], descriptor: dict[str, Any], progress: Callable) -> bytes:
    """Consume exactly the signed byte budget, including an EOF probe."""
    content = bytearray()
    stream = reader()
    try:
        progress("downloading", 0)
        while len(content) < descriptor["size"]:
            budget = min(CHUNK, descriptor["size"] - len(content))
            chunk = stream.read(budget)
            if not isinstance(chunk, bytes) or not chunk or len(chunk) > budget:
                raise ValueError("short or oversized reader output")
            content.extend(chunk)
            progress("downloading", len(content))
        if stream.read(1) != b"":
            raise ValueError("extra archive bytes")
    finally:
        stream.close()
    if _sha(content) != descriptor["sha256"]:
        raise ValueError("archive digest mismatch")
    return bytes(content)


def _extract(raw: bytes, document: dict[str, Any], stage: int) -> None:
    """Write only authenticated ordinary records into a new private fd tree."""
    seen = set()
    for member, content in _physical_members(raw):
        name = member.name
        _name(name)
        if member.linkname or member.devmajor or member.devminor:
            raise ValueError("unused TAR link/device descriptor")
        if not member.isfile() or name in seen or name not in document["files"]:
            raise ValueError("extra/duplicate/nonregular archive member")
        seen.add(name)
        record = document["files"][name]
        if len(content) != record["size"] or _sha(content) != record["sha256"] or member.mode != record["mode"]:
            raise ValueError("payload digest/size/mode mismatch")
        parent = os.dup(stage)
        try:
            for part in name.split("/")[:-1]:
                with suppress(FileExistsError):
                    os.mkdir(part, 0o700, dir_fd=parent)
                child = os.open(part, DIRECTORY_FLAGS, dir_fd=parent)
                os.close(parent)
                parent = child
                _private(parent)
            fd = os.open(
                name.split("/")[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent
            )
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fchmod(output.fileno(), record["mode"])
                os.fsync(output.fileno())
        finally:
            os.close(parent)
    if seen != set(document["files"]):
        raise ValueError("missing signed payload files")


def _stable(info: os.stat_result) -> tuple[int, ...]:
    """Ignore access-time updates caused by our own digest read."""
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_uid,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _verify(root: int, name: str, path: Path, document: dict[str, Any]) -> Lease:
    fds: dict[str, int] = {}
    directories: list[int] = []
    expected_dirs = {str(p) for n in document["files"] for p in Path(n).parents if str(p) != "."}
    observed_dirs = set()

    def walk(directory: int, prefix: str) -> None:
        _private(directory)
        names = os.listdir(directory)
        if len(names) > MAX_FILES + len(expected_dirs):
            raise ValueError("cache member limit")
        for entry in names:
            relative = prefix + entry
            if relative in expected_dirs:
                child = os.open(entry, DIRECTORY_FLAGS, dir_fd=directory)
                directories.append(child)
                observed_dirs.add(relative)
                walk(child, relative + "/")
            elif relative in document["files"]:
                fd = os.open(entry, FILE_FLAGS, dir_fd=directory)
                fds[relative] = fd
                before = os.fstat(fd)
                record = document["files"][relative]
                if (
                    not stat.S_ISREG(before.st_mode)
                    or before.st_nlink != 1
                    or before.st_uid != os.getuid()
                    or stat.S_IMODE(before.st_mode) != record["mode"]
                    or before.st_size != record["size"]
                ):
                    raise ValueError("invalid cached file type/link/mode/size")
                digest = hashlib.sha256()
                remaining = record["size"]
                while remaining:
                    chunk = os.read(fd, min(CHUNK, remaining))
                    if not chunk:
                        raise ValueError("truncated cached file")
                    digest.update(chunk)
                    remaining -= len(chunk)
                after = os.fstat(fd)
                if os.read(fd, 1) or digest.hexdigest() != record["sha256"] or _stable(before) != _stable(after):
                    raise ValueError("cached digest changed during verification")
                os.lseek(fd, 0, os.SEEK_SET)
            else:
                raise ValueError("unsigned cache entry")
        os.fsync(directory)

    try:
        directory = os.open(name, DIRECTORY_FLAGS, dir_fd=root)
        directories.append(directory)
        walk(directory, "")
        if set(fds) != set(document["files"]) or observed_dirs != expected_dirs:
            raise ValueError("incomplete cache tree")
        lease = Lease(path, name, fds, directories)
        lease.evidence.update(
            {field: document[field] for field in ("os", "architecture", "abi", "backend", "policy", "closure_sha256")}
        )
        lease.evidence["archive_sha256"] = document["archive"]["sha256"]
        return lease
    except BaseException:
        for fd in [*fds.values(), *directories]:
            os.close(fd)
        raise


def _remove(directory: int) -> None:
    """Clean only our private staging tree, anchored to its opened directory."""
    for name in os.listdir(directory):
        mode = os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode
        if stat.S_ISDIR(mode):
            child = os.open(name, DIRECTORY_FLAGS, dir_fd=directory)
            try:
                _remove(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=directory)
        else:
            os.unlink(name, dir_fd=directory)


def _lock(root: int, identity: str) -> int:
    """Separate exclusive creation from opening an existing cooperative lock."""
    name = "." + identity + ".lock"
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        return os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=root)
    except FileExistsError:
        return os.open(name, flags, dir_fd=root)


def _report(phase: str, count: int) -> None:
    """Emit allowlisted first-use progress without paths or registry secrets."""
    sys.stderr.write(json.dumps({"native_cache": phase, "bytes": count}) + "\n")


def acquire(
    cache_root: Path,
    manifest: bytes,
    signature: str,
    public_key: bytes,
    *,
    abi: str,
    backend: str,
    policy: str,
    reader: Callable[[], BinaryIO] | None = None,
    offline: bool = False,
    progress: Callable[[str, int], None] | None = None,
) -> Lease:
    """Authenticate, install atomically once, or reverify an offline cache.

    No download occurs until manifest authentication and compatibility checks pass.
    Cooperating callers serialize on a private identity lock. Missing/invalid final
    caches never fall back to host execution, an older identity or orphan staging.
    """
    document = _authenticate(manifest, signature, public_key)
    _manifest(document, abi, backend, policy)
    identity = _sha(manifest)
    report = progress or _report
    root = _root(cache_root)
    lock = None
    stage = None
    staging = "." + identity + "." + uuid.uuid4().hex + ".partial"
    try:
        lock = _lock(root, identity)
        info = os.fstat(lock)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise ValueError("invalid cache lock")
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            os.stat(identity, dir_fd=root, follow_symlinks=False)
        except FileNotFoundError:
            if offline or reader is None:
                raise IncompleteError(
                    "offline cache missing; retry online with an authenticated native artifact reader"
                ) from None
            raw = _download(reader, document["archive"], report)
            report("verifying", len(raw))
            os.mkdir(staging, 0o700, dir_fd=root)
            stage = os.open(staging, DIRECTORY_FLAGS, dir_fd=root)
            try:
                _extract(raw, document, stage)
            except tarfile.TarError as exc:
                raise ValueError("invalid TAR record framing") from exc
            with _verify(root, staging, cache_root / staging, document):
                pass
            os.rename(staging, identity, src_dir_fd=root, dst_dir_fd=root)
            os.fsync(root)
        report("verifying", document["archive"]["size"])
        lease = _verify(root, identity, cache_root / identity, document)
        try:
            report("ready", sum(record["size"] for record in document["files"].values()))
        except BaseException:
            lease.close()
            raise
        return lease
    finally:
        try:
            if stage is not None:
                try:
                    try:
                        # Published names are absent: never remove a final cache.
                        os.stat(staging, dir_fd=root, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        _remove(stage)
                        os.rmdir(staging, dir_fd=root)
                finally:
                    os.close(stage)
        finally:
            try:
                if lock is not None:
                    os.close(lock)
            finally:
                os.close(root)
