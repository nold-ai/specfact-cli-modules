"""Authenticated Darwin capsule acquisition; this module never executes a payload.

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
import subprocess
import sys
import tarfile
import uuid
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from types import MappingProxyType
from typing import Any, BinaryIO

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa


MAX_ARCHIVE_BYTES = 4 * 1024**3
MAX_UNPACKED_BYTES = 4 * 1024**3
MAX_FILE_BYTES = 2 * 1024**3
MAX_FILES = 200_000
MAX_DIRECTORIES = 400_000
MAX_MANIFEST = 64 * 1024**2
MAX_PATH_BYTES = 240
MAX_PATH_DEPTH = 32
DISK_RESERVE_BYTES = 64 * 1024**2
CHUNK = 64 * 1024
PROGRESS_INTERVAL_BYTES = 8 * 1024**2
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_SUPPORTED_ENVIRONMENTS = {f"darwin-arm64-cp{minor}" for minor in (311, 312, 313)}
_SIGNING_FIELDS = {"format", "mode", "identifier", "cdhash", "hardened_runtime"}
_ANALYZER_IDS = {
    "ai-bloat-ast",
    "ast-clean-code",
    "basedpyright",
    "contracts",
    "pylint",
    "radon",
    "ruff",
    "semgrep-bugs",
    "semgrep-clean",
    "targeted-pytest-coverage",
}
_ANALYZER_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,127}")
_NATIVE_SEMGREP_VERSION = "1.175.0"


class NativeCapsuleIncompleteError(ValueError):
    """Capability failure that cannot become successful execution evidence."""

    def __init__(self, reason: str, *, environment_id: str):
        super().__init__(reason)
        self.evidence = {
            "status": "INCOMPLETE",
            "capability": "native-capsule-cache-v1",
            "environment_id": environment_id,
            "reason": reason,
            "production_eligible": False,
            "artifact_publication_production": False,
        }


class NativeCapsuleLease:
    """Own verified file/directory descriptors until explicitly closed.

    Descriptor consumers survive path replacement. In-place inode mutation and
    native loader handoff still require independent immutable image admission.
    """

    def __init__(
        self,
        path: Path,
        identity: str,
        fds: dict[str, int],
        directories: list[int],
        analyzer_versions: dict[str, str],
    ):
        self.path, self.identity, self.fds = path, identity, fds
        self.analyzer_versions = MappingProxyType(dict(analyzer_versions))
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

    def __enter__(self) -> NativeCapsuleLease:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _sha(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _json(data: bytes) -> dict[str, Any]:
    value = json.loads(
        data.decode("utf-8", "strict"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    return value


def _tar_text_field(field: bytes) -> str:
    value, _separator, padding_bytes = field.partition(b"\0")
    if any(padding_bytes):
        raise ValueError("nonzero TAR text field padding")
    return value.decode("utf-8", "strict")


def _raw_header_path(header: bytes) -> str:
    name = _tar_text_field(header[:100])
    prefix = _tar_text_field(header[345:500])
    return f"{prefix}/{name}" if prefix else name


def _ordinary_header(header: bytes) -> tarfile.TarInfo:
    if header[257:265] != b"ustar\0" + b"00" or any(header[500:512]):
        raise ValueError("unsupported TAR magic/version or header padding")
    for start, end in ((157, 257), (265, 297), (297, 329)):
        _tar_text_field(header[start:end])
    for start, end in ((100, 108), (108, 116), (116, 124), (124, 136), (136, 148), (148, 156)):
        if re.fullmatch(rb" *[0-7]+[\0 ]*", header[start:end]) is None:
            raise ValueError("invalid TAR numeric field")
    for start, end in ((329, 337), (337, 345)):
        if re.fullmatch(rb" *[0-7]*[\0 ]*", header[start:end]) is None:
            raise ValueError("invalid TAR numeric field")
    member = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
    if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or not 0 <= member.size <= MAX_FILE_BYTES:
        raise ValueError("only bounded regular TAR members are supported")
    if _raw_header_path(header) != member.name:
        raise ValueError("TAR path normalization is forbidden")
    return member


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
    # Conservative ASCII profile; the manifest rejects case-insensitive aliases
    # separately while preserving real Python package and metadata filenames.
    try:
        encoded = value.encode("ascii", "strict") if isinstance(value, str) else b""
    except UnicodeEncodeError as exc:
        raise ValueError("noncanonical or alias-prone payload path") from exc
    if (
        not isinstance(value, str)
        or not value
        or len(encoded) > MAX_PATH_BYTES
        or len(value.split("/")) > MAX_PATH_DEPTH
        or any(part in {".", ".."} or re.fullmatch(r"[A-Za-z0-9_.+-]+", part) is None for part in value.split("/"))
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


def _manifest(document: dict[str, Any], environment_id: str, backend: str, policy: str) -> None:
    _fields(
        document,
        {
            "schema",
            "os",
            "architecture",
            "environment_id",
            "abi",
            "backend",
            "policy",
            "archive",
            "files",
            "closure",
            "closure_sha256",
            "native_signatures",
            "analyzer_versions",
        },
    )
    expected_abi = environment_id.rsplit("-", 1)[-1]
    if (
        document["schema"] != "specfact-native-capsule-v1"
        or document["os"] != "darwin"
        or document["architecture"] != "arm64"
        or environment_id not in _SUPPORTED_ENVIRONMENTS
        or document["environment_id"] != environment_id
        or document["abi"] != expected_abi
    ):
        raise ValueError("unsupported platform/schema/ABI binding")
    if not backend or not policy or document["backend"] != backend or document["policy"] != policy:
        raise NativeCapsuleIncompleteError(
            "backend/policy incompatible; install a matching native consumer and approved manifest",
            environment_id=environment_id,
        )
    analyzer_versions = document["analyzer_versions"]
    if not isinstance(analyzer_versions, dict) or set(analyzer_versions) != _ANALYZER_IDS:
        raise ValueError("native analyzer version map is incomplete")
    if any(
        not isinstance(version, str) or _ANALYZER_VERSION.fullmatch(version) is None
        for version in analyzer_versions.values()
    ):
        raise ValueError("native analyzer version is malformed")
    if {
        analyzer_versions["semgrep-clean"],
        analyzer_versions["semgrep-bugs"],
    } != {_NATIVE_SEMGREP_VERSION}:
        raise ValueError("native Semgrep version policy mismatch")
    archive = document["archive"]
    _fields(archive, {"size", "sha256"})
    _number(archive["size"], MAX_ARCHIVE_BYTES)
    _digest(archive["sha256"])
    files = document["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("invalid file count")
    total = 0
    parents = set()
    for name, record in files.items():
        _name(name)
        _fields(record, {"size", "sha256", "mode"})
        _number(record["size"], MAX_FILE_BYTES)
        _digest(record["sha256"])
        if type(record["mode"]) is not int or record["mode"] not in {0o400, 0o500}:
            raise ValueError("payload modes must be owner-read-only or owner-executable")
        total += record["size"]
        parents.update(str(parent) for parent in Path(name).parents if str(parent) != ".")
    folded_names = [name.casefold() for name in files]
    if len(folded_names) != len(set(folded_names)):
        raise ValueError("case-insensitive payload path collision")
    expected_archive_size = sum(512 + ((record["size"] + 511) // 512) * 512 for record in files.values()) + 1024
    if total > MAX_UNPACKED_BYTES:
        raise ValueError("aggregate unpacked payload limit")
    if len(parents) > MAX_DIRECTORIES:
        raise ValueError("payload directory limit")
    if set(files) & parents:
        raise ValueError("payload parent/file collision")
    if expected_archive_size != archive["size"]:
        raise ValueError("archive size does not encode exact USTAR end blocks")
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
    signatures = document["native_signatures"]
    executables = {name for name, record in files.items() if record["mode"] == 0o500}
    if not isinstance(signatures, dict) or set(signatures) != executables or not executables:
        raise ValueError("native signatures must cover every executable and only executables")
    for name, record in signatures.items():
        _name(name)
        _fields(record, _SIGNING_FIELDS)
        if (
            record["format"] != "mach-o"
            or record["mode"] != "adhoc"
            or record["hardened_runtime"] is not True
            or not isinstance(record["identifier"], str)
            or re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}", record["identifier"]) is None
            or not isinstance(record["cdhash"], str)
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", record["cdhash"]) is None
        ):
            raise ValueError("invalid native signing metadata")


def _private(fd: int) -> None:
    metadata = os.fstat(fd)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ValueError("cache directory must be owner-owned mode 0700")


def _root(path: Path) -> int:
    """Anchor each absolute component; never resolve/follow a symlink."""
    path = path.absolute()
    fd = os.open("/", DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:]:
            if part in {".", ".."}:
                raise ValueError("noncanonical cache root")
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


class _ArchiveReader:
    """Consume one authenticated archive with fixed-size reads and hashing."""

    def __init__(self, stream: BinaryIO, descriptor: dict[str, Any], progress: Callable[[str, int], None]):
        self.stream = stream
        self.size = descriptor["size"]
        self.expected_digest = descriptor["sha256"]
        self.progress = progress
        self.consumed = 0
        self._reported = 0
        self.digest = hashlib.sha256()

    def read_exact(self, size: int) -> bytes:
        if size < 0 or self.consumed + size > self.size:
            raise ValueError("archive exceeds signed size")
        output = bytearray()
        while len(output) < size:
            budget = min(CHUNK, size - len(output))
            chunk = self.stream.read(budget)
            if not isinstance(chunk, bytes) or not chunk or len(chunk) > budget:
                raise ValueError("short or oversized reader output")
            output.extend(chunk)
            self.digest.update(chunk)
            self.consumed += len(chunk)
            if self.consumed == self.size or self.consumed - self._reported >= PROGRESS_INTERVAL_BYTES:
                self.progress("downloading", self.consumed)
                self._reported = self.consumed
        return bytes(output)

    def finish(self) -> None:
        if self.consumed != self.size:
            raise ValueError("invalid TAR end blocks or trailing signed bytes")
        if self.stream.read(1) != b"":
            raise ValueError("trailing archive bytes")
        if self.digest.hexdigest() != self.expected_digest:
            raise ValueError("archive digest mismatch")


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(fd, payload[offset:])
        if written <= 0:
            raise OSError("short staging write")
        offset += written


def _member_parent(stage: int, name: str) -> tuple[int, str]:
    parent = os.dup(stage)
    try:
        parts = name.split("/")
        for part in parts[:-1]:
            with suppress(FileExistsError):
                os.mkdir(part, 0o700, dir_fd=parent)
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=parent)
            os.close(parent)
            parent = child
            _private(parent)
        return parent, parts[-1]
    except BaseException:
        os.close(parent)
        raise


def _stream_extract(
    reader: Callable[[], BinaryIO],
    document: dict[str, Any],
    stage: int,
    progress: Callable[[str, int], None],
) -> None:
    """Verify and extract one exact USTAR stream without buffering payloads."""
    stream = reader()
    archive = _ArchiveReader(stream, document["archive"], progress)
    progress("downloading", 0)
    try:
        for name, record in document["files"].items():
            header = archive.read_exact(512)
            if not any(header):
                raise ValueError("missing signed payload files before TAR end blocks")
            member = _ordinary_header(header)
            _name(member.name)
            if member.linkname or member.devmajor or member.devminor:
                raise ValueError("unused TAR link/device descriptor")
            if member.name != name or member.size != record["size"] or member.mode != record["mode"]:
                raise ValueError("payload order/name/size/mode mismatch")
            parent, leaf = _member_parent(stage, name)
            try:
                fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                try:
                    digest = hashlib.sha256()
                    remaining = record["size"]
                    while remaining:
                        chunk = archive.read_exact(min(CHUNK, remaining))
                        digest.update(chunk)
                        _write_all(fd, chunk)
                        remaining -= len(chunk)
                    padding_size = (-record["size"]) % 512
                    if padding_size and any(archive.read_exact(padding_size)):
                        raise ValueError("nonzero TAR member padding")
                    if digest.hexdigest() != record["sha256"]:
                        raise ValueError("payload digest mismatch")
                    os.fchmod(fd, record["mode"])
                    os.fsync(fd)
                finally:
                    os.close(fd)
            finally:
                os.close(parent)
        if any(archive.read_exact(512)) or any(archive.read_exact(512)):
            raise ValueError("invalid TAR end blocks")
        archive.finish()
    finally:
        stream.close()


def _available_disk_bytes(fd: int) -> int:
    usage = os.fstatvfs(fd)
    return usage.f_bavail * usage.f_frsize


def _disk_preflight(root: int, document: dict[str, Any]) -> None:
    unpacked = sum(record["size"] for record in document["files"].values())
    required = unpacked + DISK_RESERVE_BYTES
    if _available_disk_bytes(root) < required:
        raise ValueError(f"insufficient cache disk space: required={required}")


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


def _verify(root: int, name: str, path: Path, document: dict[str, Any]) -> NativeCapsuleLease:
    fds: dict[str, int] = {}
    directories: list[int] = []
    expected_dirs = {str(p) for n in document["files"] for p in Path(n).parents if str(p) != "."}
    observed_dirs = set()
    observed_files = set()
    retained = set(document["native_signatures"])

    def walk(directory: int, prefix: str) -> None:
        _private(directory)
        count = 0
        with os.scandir(directory) as entries:
            for item in entries:
                count += 1
                if count > MAX_FILES + MAX_DIRECTORIES:
                    raise ValueError("cache member limit")
                entry = item.name
                relative = prefix + entry
                if relative in expected_dirs:
                    child = os.open(entry, DIRECTORY_FLAGS, dir_fd=directory)
                    try:
                        observed_dirs.add(relative)
                        walk(child, relative + "/")
                    finally:
                        os.close(child)
                elif relative in document["files"]:
                    fd = os.open(entry, FILE_FLAGS, dir_fd=directory)
                    keep = relative in retained
                    retained_fd = False
                    try:
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
                        if (
                            os.read(fd, 1)
                            or digest.hexdigest() != record["sha256"]
                            or _stable(before) != _stable(after)
                        ):
                            raise ValueError("cached digest changed during verification")
                        observed_files.add(relative)
                        if keep:
                            os.lseek(fd, 0, os.SEEK_SET)
                            fds[relative] = fd
                            retained_fd = True
                    finally:
                        if not retained_fd:
                            os.close(fd)
                else:
                    raise ValueError("unsigned cache entry")
        os.fsync(directory)

    try:
        directory = os.open(name, DIRECTORY_FLAGS, dir_fd=root)
        directories.append(directory)
        walk(directory, "")
        if set(fds) != retained or observed_files != set(document["files"]) or observed_dirs != expected_dirs:
            raise ValueError("incomplete cache tree")
        lease = NativeCapsuleLease(path, name, fds, directories, document["analyzer_versions"])
        lease.evidence.update(
            {
                field: document[field]
                for field in (
                    "os",
                    "architecture",
                    "environment_id",
                    "abi",
                    "backend",
                    "policy",
                    "closure_sha256",
                )
            }
        )
        lease.evidence["archive_sha256"] = document["archive"]["sha256"]
        lease.evidence["analyzer_versions"] = dict(lease.analyzer_versions)
        return lease
    except BaseException:
        for fd in [*fds.values(), *directories]:
            os.close(fd)
        raise


def inspect_native_signature(path: Path) -> dict[str, object]:
    """Read an ad-hoc hardened-runtime signature using the macOS system tool."""
    if sys.platform != "darwin":
        raise ValueError("native signing inspection requires Darwin")
    environment = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
    verified = subprocess.run(
        ["/usr/bin/codesign", "--verify", "--strict", "--verbose=4", str(path)],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )
    if verified.returncode != 0:
        raise ValueError("native code signature verification failed")
    described = subprocess.run(
        ["/usr/bin/codesign", "--display", "--verbose=4", str(path)],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )
    if described.returncode != 0:
        raise ValueError("native code signature metadata unavailable")
    fields: dict[str, str] = {}
    for line in described.stderr.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    code_directory = next((line for line in described.stderr.splitlines() if line.startswith("CodeDirectory ")), "")
    signature_mode = fields.get("Signature", "")
    if signature_mode != "adhoc":
        raise ValueError("native executable is not ad-hoc signed")
    return {
        "format": "mach-o",
        "mode": "adhoc",
        "identifier": fields.get("Identifier", ""),
        "cdhash": fields.get("CDHash", "").lower(),
        "hardened_runtime": "runtime" in code_directory,
    }


def _verify_native_signatures(
    lease: NativeCapsuleLease,
    document: dict[str, Any],
    inspector: Callable[[Path], dict[str, object]],
) -> None:
    for name, expected in document["native_signatures"].items():
        fd = lease.fds[name]
        path = lease.path / name
        before = os.fstat(fd)
        pathname_before = path.lstat()
        if path.is_symlink() or (before.st_dev, before.st_ino) != (pathname_before.st_dev, pathname_before.st_ino):
            raise ValueError("native signature path no longer identifies the verified file")
        observed = inspector(path)
        after = os.fstat(fd)
        pathname_after = path.lstat()
        if (
            observed != expected
            or _stable(before) != _stable(after)
            or (after.st_dev, after.st_ino) != (pathname_after.st_dev, pathname_after.st_ino)
        ):
            raise ValueError("native signature metadata mismatch")
    lease.evidence["native_signing_mode"] = "adhoc"
    lease.evidence["native_signing_verified"] = True


def _remove(directory: int) -> None:
    """Clean only our private staging tree, anchored to its opened directory."""
    with os.scandir(directory) as entries:
        for item in entries:
            name = item.name
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


def acquire_native_capsule(
    cache_root: Path,
    manifest: bytes,
    signature: str,
    public_key: bytes,
    *,
    environment_id: str,
    backend: str,
    policy: str,
    reader: Callable[[], BinaryIO] | None = None,
    offline: bool = False,
    progress: Callable[[str, int], None] | None = None,
    signature_inspector: Callable[[Path], dict[str, object]] = inspect_native_signature,
) -> NativeCapsuleLease:
    """Authenticate, install atomically once, or reverify an offline cache.

    No download occurs until manifest authentication, compatibility and disk-space checks pass.
    The supplied reader owns connect/read deadlines and cancellation behavior.
    Cooperating callers serialize on a private identity lock. Missing/invalid final
    caches never fall back to host execution, an older identity or orphan staging.
    """
    document = _authenticate(manifest, signature, public_key)
    _manifest(document, environment_id, backend, policy)
    identity = _sha(manifest)
    report = progress or _report
    cache_root = cache_root.absolute()
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
                raise NativeCapsuleIncompleteError(
                    "offline cache missing; retry online with an authenticated native artifact reader",
                    environment_id=environment_id,
                ) from None
            _disk_preflight(root, document)
            os.mkdir(staging, 0o700, dir_fd=root)
            stage = os.open(staging, DIRECTORY_FLAGS, dir_fd=root)
            try:
                _stream_extract(reader, document, stage, report)
            except tarfile.TarError as exc:
                raise ValueError("invalid TAR record framing") from exc
            report("verifying", document["archive"]["size"])
            with _verify(root, staging, cache_root / staging, document) as staged_lease:
                _verify_native_signatures(staged_lease, document, signature_inspector)
            os.rename(staging, identity, src_dir_fd=root, dst_dir_fd=root)
            os.fsync(root)
        report("verifying", document["archive"]["size"])
        lease = _verify(root, identity, cache_root / identity, document)
        try:
            _verify_native_signatures(lease, document, signature_inspector)
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
