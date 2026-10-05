#!/usr/bin/env python3
"""Build a deterministic candidate capsule from a verified Darwin ARM64 root."""

# ruff: noqa: I001

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import plistlib
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
CODE_REVIEW_SOURCE = REPOSITORY_ROOT / "packages/specfact-code-review/src"
if str(CODE_REVIEW_SOURCE) not in sys.path:
    sys.path.insert(0, str(CODE_REVIEW_SOURCE))

from specfact_code_review.run import runtime_native  # noqa: E402
from scripts import build_macos_managed_git as managed_git_builder  # noqa: E402
from specfact_code_review.run.native_capsule import (  # noqa: E402
    CHUNK,
    MAX_ARCHIVE_BYTES,
    MAX_FILE_BYTES,
    MAX_FILES as CONSUMER_MAX_FILES,
    MAX_MANIFEST as CONSUMER_MAX_MANIFEST,
    MAX_PATH_BYTES,
    MAX_PATH_DEPTH,
    MAX_UNPACKED_BYTES,
    inspect_native_signature,
)


MAX_FILES = CONSUMER_MAX_FILES
MAX_MANIFEST = CONSUMER_MAX_MANIFEST
SUPPORTED_ENVIRONMENTS = {f"darwin-arm64-cp{minor}" for minor in (311, 312, 313)}
IDENTITY = re.compile(r"[a-z0-9][a-z0-9.-]{0,127}")
PATH_PART = re.compile(r"[A-Za-z0-9_.+-]+")
MACHO_MAGICS = {
    b"\xcf\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}
SIGNING_FIELDS = {"format", "mode", "identifier", "cdhash", "hardened_runtime"}
ANALYZER_IDS = {
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
ANALYZER_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,127}")
GIT_INPUT_FILES = {
    "bin/git": "bin/git",
    "git.requirement": "provenance/git.requirement",
    "licenses/Git-COPYING": "licenses/Git-COPYING",
    "licenses/sha1dc-LICENSE.txt": "licenses/sha1dc-LICENSE.txt",
    "licenses/reftable-LICENSE": "licenses/reftable-LICENSE",
    "source/git-2.54.0.tar.xz": "provenance/git-2.54.0.tar.xz",
}
GIT_RECEIPT = "provenance/input.json"
GIT_RUNTIME_FILES = {
    name: (
        "tools/git"
        if name == "bin/git"
        else f"licenses/managed-git/{name.removeprefix('licenses/')}"
        if name.startswith("licenses/")
        else f"provenance/managed-git/{name.removeprefix('provenance/')}"
    )
    for name in {*GIT_INPUT_FILES.values(), GIT_RECEIPT}
}


class SchemaLimitError(ValueError):
    """The complete runtime cannot fit the current consumer schema."""


@dataclass(frozen=True)
class BuildResult:
    archive: Path
    manifest: Path
    signature: Path | None
    summary: Path


FileRecord = dict[str, int | str]


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata is not canonical JSON") from exc


def _safe_name(value: str, *, label: str) -> None:
    parts = value.split("/")
    try:
        encoded = value.encode("ascii", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"unsafe {label} path or identity: {value!r}") from exc
    if (
        not value
        or len(encoded) > MAX_PATH_BYTES
        or len(parts) > MAX_PATH_DEPTH
        or any(part in {".", ".."} or PATH_PART.fullmatch(part) is None for part in parts)
    ):
        raise ValueError(f"unsafe {label} path or identity: {value!r}")


def _walk_runtime(root: Path) -> dict[str, Path]:
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("runtime root must be an absolute ordinary directory")
    files: dict[str, Path] = {}
    for directory, names, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(directory)
        for name in [*names, *filenames]:
            path = current / name
            relative = path.relative_to(root).as_posix()
            _safe_name(relative, label="payload")
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError(f"symlink payload member forbidden: {relative}")
            if name in names:
                if not stat.S_ISDIR(metadata.st_mode):
                    raise ValueError(f"non-directory payload parent forbidden: {relative}")
            elif stat.S_ISREG(metadata.st_mode):
                files[relative] = path
            else:
                raise ValueError(f"non-regular payload member forbidden: {relative}")
    folded = [name.casefold() for name in files]
    if len(folded) != len(set(folded)):
        raise ValueError("case-insensitive payload path collision")
    return files


def _validate_closure(closure: Mapping[str, Sequence[str]], files: Mapping[str, Path]) -> dict[str, list[str]]:
    if not closure:
        raise ValueError("closure must be non-empty")
    normalized: dict[str, list[str]] = {}
    members: list[str] = []
    for component, paths in sorted(closure.items()):
        _safe_name(component, label="closure component")
        if IDENTITY.fullmatch(component) is None:
            raise ValueError(f"unsafe closure component identity: {component!r}")
        if isinstance(paths, (str, bytes)) or not paths:
            raise ValueError(f"closure component must be non-empty: {component}")
        selected = sorted(paths)
        for name in selected:
            _safe_name(name, label="closure member")
        normalized[component] = selected
        members.extend(selected)
    if len(members) != len(set(members)):
        raise ValueError("closure members must be unique")
    missing = set(members) - set(files)
    undeclared = set(files) - set(members)
    if missing:
        raise ValueError(f"closure references missing files: {','.join(sorted(missing))}")
    if undeclared:
        raise ValueError(f"undeclared runtime files: {','.join(sorted(undeclared))}")
    if not any(name.startswith("provenance") for name in normalized):
        raise ValueError("closure requires a provenance component")
    if not any(name.startswith("licenses") for name in normalized):
        raise ValueError("closure requires a licenses component")
    return normalized


def _native_images(root: Path, files: Mapping[str, Path]) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    prefixes = {}
    for name, path in files.items():
        with path.open("rb") as source:
            prefixes[name] = source.read(4)
    images = {name: files[name] for name, prefix in prefixes.items() if prefix in MACHO_MAGICS}
    elf = {name for name, prefix in prefixes.items() if prefix == b"\x7fELF"}
    if images and elf:
        raise ValueError("project_native_architecture_mixed:ELF and Mach-O images")
    if elf:
        raise ValueError("executable_not_macho:Darwin capsule contains ELF")
    for name, path in files.items():
        if path.stat().st_mode & 0o111 and name not in images:
            raise ValueError(f"executable_not_macho:{name}")
    records = runtime_native.inventory_native(root, capsule_root=root, declared=(), system_roots=())
    inventoried = {record["path"] for record in records}
    if inventoried != set(images):
        unvalidated = set(images) - inventoried
        raise ValueError(f"native image outside inventory layout: {','.join(sorted(unvalidated))}")
    return images, records


def inspect_entitlements(path: Path) -> object:
    """Return the exact plist value reported by codesign for one native image."""
    result = subprocess.run(
        ["/usr/bin/codesign", "--display", "--entitlements", ":-", "--xml", str(path)],
        capture_output=True,
        check=False,
        env={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        timeout=10,
    )
    if result.returncode != 0:
        raise ValueError("native entitlement metadata unavailable")
    candidates = [payload for payload in (result.stdout, result.stderr) if b"<?xml" in payload or b"<plist" in payload]
    if not candidates:
        return {}
    try:
        payload = candidates[0]
        starts = [position for marker in (b"<?xml", b"<plist") if (position := payload.find(marker)) >= 0]
        return plistlib.loads(payload[min(starts) :])
    except (plistlib.InvalidFileException, ValueError) as exc:
        raise ValueError("native entitlement metadata malformed") from exc


def _signing_metadata(
    images: Mapping[str, Path],
    signature_inspector: Callable[[Path], dict[str, object]],
    entitlements_inspector: Callable[[Path], object],
) -> tuple[dict[str, dict[str, object]], bytes]:
    signatures: dict[str, dict[str, object]] = {}
    detail: dict[str, dict[str, object]] = {}
    for name, path in sorted(images.items()):
        observed = signature_inspector(path)
        if set(observed) != SIGNING_FIELDS or (
            observed.get("format") != "mach-o"
            or observed.get("mode") != "adhoc"
            or observed.get("hardened_runtime") is not True
            or not isinstance(observed.get("identifier"), str)
            or re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}", str(observed.get("identifier"))) is None
            or not isinstance(observed.get("cdhash"), str)
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(observed.get("cdhash"))) is None
        ):
            raise ValueError(f"native image lacks required ad-hoc hardened-runtime signature: {name}")
        signatures[name] = dict(observed)
        detail[name] = {"signature": observed, "entitlements": entitlements_inspector(path)}
    return signatures, _canonical({"schema": "specfact-native-signing-v1", "images": detail}) + b"\n"


def _hash_path(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(CHUNK):
            if len(chunk) > CHUNK:
                raise ValueError("oversized local payload read")
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def _git_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 1 << 20:
        raise ValueError("Git provenance must be a bounded ordinary file")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Git provenance must be an object")
    return value


def _git_pin(provenance: Mapping[str, Any]) -> None:
    expected = {
        "version": managed_git_builder.VERSION,
        "commit": managed_git_builder.UPSTREAM_COMMIT,
        "archive_url": managed_git_builder.ARCHIVE_URL,
        "archive_sha256": managed_git_builder.ARCHIVE_SHA256,
        "checksum_url": managed_git_builder.CHECKSUM_URL,
    }
    if provenance.get("upstream") != expected:
        raise ValueError("Git source provenance differs from the reviewed official pin")


def _git_files(root: Path, expected: set[str]) -> dict[str, dict[str, Any]]:
    if not root.is_absolute() or root.resolve(strict=True) != root or root.is_symlink():
        raise ValueError("Git input root must be canonical")
    files = _walk_runtime(root)
    return _git_file_records(files, expected, executable="bin/git")


def _git_file_records(files: Mapping[str, Path], expected: set[str], *, executable: str) -> dict[str, dict[str, Any]]:
    if set(files) != expected:
        raise ValueError("Git input inventory contains missing or undeclared files")
    records = {}
    for name, path in files.items():
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o222 or (bool(mode & 0o111) != (name == executable)):
            raise ValueError("Git input must be immutable with one executable image")
        if path.stat().st_size > managed_git_builder.MAX_SOURCE_BYTES:
            raise ValueError("Git input file exceeds maintainer bound")
        size, digest = _hash_path(path)
        records[name] = {"size": size, "sha256": digest}
    return records


def _git_identity(
    root: Path,
    provenance: Mapping[str, Any],
    requirement_name: str,
    signature_inspector: Callable[[Path], Mapping[str, object]],
    *,
    image_name: str = "bin/git",
) -> str:
    image = root / image_name
    observed = signature_inspector(image)
    signing = provenance.get("signing")
    codehash = observed.get("cdhash")
    if (
        observed.get("format") != "mach-o"
        or observed.get("mode") != "adhoc"
        or observed.get("identifier") != managed_git_builder.SIGNING_IDENTIFIER
        or observed.get("hardened_runtime") is not True
        or not isinstance(codehash, str)
        or re.fullmatch(r"[0-9a-f]{40}", codehash) is None
        or not isinstance(signing, dict)
    ):
        raise ValueError("Git image lacks the exact hardened ad-hoc identity")
    requirement = f'cdhash H"{codehash}"'
    expected = {
        "mode": "adhoc",
        "identifier": managed_git_builder.SIGNING_IDENTIFIER,
        "cdhash": codehash,
        "requirement": requirement,
    }
    requirement_file = root / requirement_name
    if (
        requirement_file.stat().st_size > 128
        or requirement_file.read_text() != requirement + "\n"
        or signing != expected
    ):
        raise ValueError("Git signed requirement does not match the observed image")
    metadata = runtime_native._macho_metadata(image)
    dependencies = provenance.get("dependencies")
    if (
        metadata["architectures"] != ("arm64",)
        or metadata["rpaths"]
        or not metadata["needed"]
        or not isinstance(dependencies, list)
        or sorted(metadata["needed"]) != sorted(dependencies)
        or any(not name.startswith(("/usr/lib/", "/System/Library/")) for name in dependencies)
    ):
        raise ValueError("Git native closure must be ARM64 and Apple-only")
    return requirement


def verify_managed_git_artifact(
    root: Path, *, signature_inspector: Callable[[Path], Mapping[str, object]] = inspect_native_signature
) -> dict[str, Any]:
    """Check an explicit maintainer artifact; never infer publisher authority."""
    records = _git_files(root, {*GIT_INPUT_FILES, "build.log", "provenance.json", "SHA256SUMS"})
    provenance = _git_json(root / "provenance.json")
    if provenance.get("schema") != "specfact-managed-git-build-v1" or provenance.get("maintainer_only") is not True:
        raise ValueError("Git artifact is not a maintainer build")
    _git_pin(provenance)
    inventory = provenance.get("inventory")
    expected = {
        name: record["sha256"] for name, record in records.items() if name not in {"provenance.json", "SHA256SUMS"}
    }
    if inventory != expected or records["source/git-2.54.0.tar.xz"]["sha256"] != managed_git_builder.ARCHIVE_SHA256:
        raise ValueError("Git artifact differs from its complete pinned inventory")
    sums = root / "SHA256SUMS"
    if sums.stat().st_size > 16384:
        raise ValueError("Git checksum inventory exceeds bound")
    expected_sums = "".join(f"{records[name]['sha256']}  {name}\n" for name in sorted(records) if name != "SHA256SUMS")
    if sums.read_text() != expected_sums:
        raise ValueError("Git checksum inventory differs from artifact bytes")
    _git_identity(root, provenance, "git.requirement", signature_inspector)
    return provenance


def verify_managed_git_input(
    root: Path, *, signature_inspector: Callable[[Path], Mapping[str, object]] = inspect_native_signature
) -> dict[str, Any]:
    """Recheck the compact candidate input, including its sanitized receipt."""
    records = _git_files(root, {*GIT_INPUT_FILES.values(), GIT_RECEIPT})
    return _verify_git_receipt(root, records, signature_inspector)


def _verify_git_receipt(
    root: Path,
    records: Mapping[str, dict[str, Any]],
    signature_inspector: Callable[[Path], Mapping[str, object]],
    *,
    runtime_layout: bool = False,
) -> dict[str, Any]:
    mapping = GIT_RUNTIME_FILES if runtime_layout else {name: name for name in records}
    receipt = _git_json(root / mapping[GIT_RECEIPT])
    _git_pin(receipt)
    if receipt.get("schema") != "specfact-managed-git-input-v1" or receipt.get("production_eligible") is not False:
        raise ValueError("Git installation receipt is not candidate-only")
    expected = {name: record for name, record in records.items() if name != GIT_RECEIPT}
    if (
        receipt.get("files") != expected
        or records["provenance/git-2.54.0.tar.xz"]["sha256"] != managed_git_builder.ARCHIVE_SHA256
    ):
        raise ValueError("Git installed payload differs from its pinned receipt")
    _git_identity(
        root, receipt, mapping["provenance/git.requirement"], signature_inspector, image_name=mapping["bin/git"]
    )
    return receipt


def verify_managed_git_binding(
    broker: Path,
    requirement: str,
    broker_requirement: object,
    *,
    signature_inspector: Callable[[Path], Mapping[str, object]] = inspect_native_signature,
) -> None:
    """Bind the verified Git identity to the observed, compiled native broker."""
    observed = signature_inspector(broker)
    codehash = observed.get("cdhash")
    if (
        observed.get("format") != "mach-o"
        or observed.get("mode") != "adhoc"
        or observed.get("hardened_runtime") is not True
        or not isinstance(codehash, str)
        or re.fullmatch(r"[0-9a-f]{40}", codehash) is None
        or broker_requirement != f'cdhash H"{codehash}"'
    ):
        raise ValueError("Git broker identity differs from component provenance")
    needle = requirement.encode("ascii") + b"\0"
    descriptor = os.open(broker, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FILE_BYTES:
            raise ValueError("Git broker input must be a bounded ordinary image")
        overlap = b""
        remaining = metadata.st_size
        while remaining:
            chunk = source.read(min(CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            if needle in overlap + chunk:
                return
            overlap = (overlap + chunk)[-len(needle) :]
    raise ValueError("Git broker lacks the exact compiled tool requirement")


def verify_managed_git_runtime(
    root: Path, *, signature_inspector: Callable[[Path], Mapping[str, object]] = inspect_native_signature
) -> dict[str, Any]:
    """Recheck the assembled Git files and native-component binding before packing."""
    files = {
        name: path
        for name, path in _walk_runtime(root).items()
        if name == "tools/git" or name.startswith(("licenses/managed-git/", "provenance/managed-git/"))
    }
    actual = _git_file_records(files, set(GIT_RUNTIME_FILES.values()), executable="tools/git")
    records = {name: actual[target] for name, target in GIT_RUNTIME_FILES.items()}
    receipt = _verify_git_receipt(root, records, signature_inspector, runtime_layout=True)
    component = _git_json(root / "provenance/native-component.json")
    requirement = receipt["signing"]["requirement"]
    if component.get("managed_tool_requirements") != {"tools/git": requirement}:
        raise ValueError("Git broker requirement provenance differs from installed input")
    verify_managed_git_binding(
        root / "bin/specfact-native-broker",
        requirement,
        component.get("broker_designated_requirement"),
        signature_inspector=signature_inspector,
    )
    return receipt


def _copy_git_input(source: Path, target: Path, expected_digest: str) -> dict[str, Any]:
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as payload, target.open("xb") as output:
        metadata = os.fstat(payload.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_mode & 0o222
            or metadata.st_size > managed_git_builder.MAX_SOURCE_BYTES
        ):
            raise ValueError("Git installation source changed type, mode or bounded size")
        remaining = metadata.st_size
        digest = hashlib.sha256()
        while remaining:
            chunk = payload.read(min(CHUNK, remaining))
            if not chunk:
                raise ValueError("Git source shortened while installing")
            remaining -= len(chunk)
            digest.update(chunk)
            output.write(chunk)
        if payload.read(1) or digest.hexdigest() != expected_digest:
            raise ValueError("Git artifact changed while installing")
    return {"size": metadata.st_size, "sha256": digest.hexdigest()}


def install_managed_git_input(
    git_artifact_root: Path,
    payload_root: Path,
    *,
    signature_inspector: Callable[[Path], Mapping[str, object]] = inspect_native_signature,
) -> dict[str, Any]:
    """Copy a verified image/source/license input without signing or raw logs."""
    provenance = verify_managed_git_artifact(git_artifact_root, signature_inspector=signature_inspector)
    if payload_root.resolve(strict=True) != payload_root or not payload_root.is_dir():
        raise ValueError("Git candidate payload must be a canonical existing directory")
    destination = payload_root / "git"
    if destination.exists() or destination.is_symlink():
        raise ValueError("Git candidate input already exists")
    if payload_root == git_artifact_root or payload_root.is_relative_to(git_artifact_root):
        raise ValueError("Git payload must be disjoint from artifact input")
    with tempfile.TemporaryDirectory(prefix=".managed-git-", dir=payload_root) as temporary:
        work = Path(temporary) / "git"
        work.mkdir(mode=0o700)
        records = {}
        for name, target in GIT_INPUT_FILES.items():
            output = work / target
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            records[target] = _copy_git_input(git_artifact_root / name, output, provenance["inventory"][name])
            output.chmod(0o555 if target == "bin/git" else 0o444)
        toolchain = provenance.get("toolchain", {})
        receipt = {
            "schema": "specfact-managed-git-input-v1",
            "upstream": provenance["upstream"],
            "signing": provenance["signing"],
            "dependencies": sorted(provenance["dependencies"]),
            "toolchain": {
                name: str(toolchain[name]).splitlines()[0]
                for name in ("compiler_version", "sdk_version", "make_version")
                if name in toolchain
            },
            "artifact_provenance_sha256": _hash_path(git_artifact_root / "provenance.json")[1],
            "files": records,
            "production_eligible": False,
        }
        (work / GIT_RECEIPT).write_bytes(_canonical(receipt) + b"\n")
        (work / GIT_RECEIPT).chmod(0o444)
        verify_managed_git_input(work, signature_inspector=signature_inspector)
        work.rename(destination)
    return receipt


def prepare_managed_git_input(
    *,
    payload_root: Path,
    git_artifact_root: Path | None = None,
    source_archive: Path | None = None,
    git_build_output: Path | None = None,
    jobs: int = 2,
    signature_inspector: Callable[[Path], Mapping[str, object]] = inspect_native_signature,
) -> dict[str, Any]:
    """Key-free maintainer route; compilation occurs only for explicit source."""
    if (git_artifact_root is None) == (source_archive is None) or (source_archive is not None) != (
        git_build_output is not None
    ):
        raise ValueError("select one explicit Git artifact or source/build output pair")
    if source_archive is not None:
        assert git_build_output is not None
        managed_git_builder.build(source_archive, git_build_output, jobs=jobs)
        git_artifact_root = git_build_output
    assert git_artifact_root is not None
    return install_managed_git_input(git_artifact_root, payload_root, signature_inspector=signature_inspector)


def _tar_header(name: str, size: int, mode: int) -> bytes:
    member = tarfile.TarInfo(name)
    member.size = size
    member.mode = mode
    member.mtime = 0
    member.uid = 0
    member.gid = 0
    member.uname = ""
    member.gname = ""
    member.type = tarfile.REGTYPE
    return member.tobuf(format=tarfile.USTAR_FORMAT, encoding="utf-8", errors="strict")


def _stream_archive(
    output: BinaryIO,
    sources: Mapping[str, Path | bytes],
    records: Mapping[str, FileRecord],
) -> tuple[int, str]:
    archive_digest = hashlib.sha256()
    archive_size = 0

    def emit(output: Any, payload: bytes) -> None:
        nonlocal archive_size
        output.write(payload)
        archive_digest.update(payload)
        archive_size += len(payload)
        if archive_size > MAX_ARCHIVE_BYTES:
            raise SchemaLimitError(
                f"native_capsule_schema_limit:archive_bytes:observed={archive_size}:maximum={MAX_ARCHIVE_BYTES}"
            )

    for name, record in records.items():
        size = int(record["size"])
        emit(output, _tar_header(name, size, int(record["mode"])))
        source = sources[name]
        member_digest = hashlib.sha256()
        observed = 0
        if isinstance(source, Path):
            with source.open("rb") as payload:
                while chunk := payload.read(CHUNK):
                    if len(chunk) > CHUNK:
                        raise ValueError("oversized local payload read")
                    emit(output, chunk)
                    member_digest.update(chunk)
                    observed += len(chunk)
        else:
            for offset in range(0, len(source), CHUNK):
                chunk = source[offset : offset + CHUNK]
                emit(output, chunk)
                member_digest.update(chunk)
                observed += len(chunk)
        if observed != size or member_digest.hexdigest() != record["sha256"]:
            raise ValueError(f"payload changed while building archive: {name}")
        padding_size = (-size) % 512
        if padding_size:
            emit(output, b"\0" * padding_size)
    emit(output, b"\0" * 1024)
    output.flush()
    os.fsync(output.fileno())
    return archive_size, archive_digest.hexdigest()


@contextmanager
def _exclusive_outputs(destination: Path, names: tuple[str, ...]) -> Iterator[dict[str, BinaryIO]]:
    with suppress(FileExistsError):
        destination.mkdir(parents=True)
    try:
        directory_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ValueError("output path must be an ordinary output directory") from exc

    created: list[str] = []
    try:
        with ExitStack() as resources:
            streams: dict[str, BinaryIO] = {}
            for name in names:
                descriptor = os.open(
                    name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd
                )
                created.append(name)
                streams[name] = resources.enter_context(os.fdopen(descriptor, "wb"))
                os.fchmod(descriptor, 0o600)
            yield streams
    except BaseException:
        for name in reversed(created):
            with suppress(FileNotFoundError):
                os.unlink(name, dir_fd=directory_fd)
        raise
    finally:
        os.close(directory_fd)


def _write_output(output: BinaryIO, payload: bytes) -> None:
    output.write(payload)
    output.flush()
    os.fsync(output.fileno())


def _sign(payload: bytes, private_key: object) -> str:
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        raw = private_key.sign(payload)
    elif isinstance(private_key, rsa.RSAPrivateKey):
        raw = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
    else:
        raise ValueError("private key must be Ed25519 or RSA")
    return base64.b64encode(raw).decode("ascii")


def _limit(condition: bool, reason: str, observed: int, maximum: int) -> None:
    if condition:
        raise SchemaLimitError(f"native_capsule_schema_limit:{reason}:observed={observed}:maximum={maximum}")


def build_native_capsule(
    *,
    runtime_root: Path,
    output_dir: Path,
    closure: Mapping[str, Sequence[str]],
    environment_id: str,
    backend: str,
    policy: str,
    analyzer_versions: Mapping[str, str],
    private_key: object | None,
    signature_inspector: Callable[[Path], dict[str, object]] = inspect_native_signature,
    entitlements_inspector: Callable[[Path], object] = inspect_entitlements,
) -> BuildResult:
    """Build immutable candidate files; never mutate or complete the runtime root."""
    if runtime_root.is_symlink():
        raise ValueError("runtime root symlink forbidden")
    root = runtime_root.resolve(strict=True)
    destination = output_dir.absolute()
    if destination == root or destination.is_relative_to(root):
        raise ValueError("output directory must be outside runtime root")
    if environment_id not in SUPPORTED_ENVIRONMENTS:
        raise ValueError("unsupported Darwin ARM64 environment")
    if IDENTITY.fullmatch(backend) is None or IDENTITY.fullmatch(policy) is None:
        raise ValueError("backend and policy must be bounded identities")
    if set(analyzer_versions) != ANALYZER_IDS or any(
        not isinstance(version, str) or ANALYZER_VERSION.fullmatch(version) is None
        for version in analyzer_versions.values()
    ):
        raise ValueError("native analyzer version map is invalid")

    files = _walk_runtime(root)
    normalized_closure = _validate_closure(closure, files)
    if "native-signing-v1" in normalized_closure:
        raise ValueError("generated signing component collides with runtime input")
    _limit(len(files) + 1 > MAX_FILES, "file_count", len(files) + 1, MAX_FILES)
    input_bytes = sum(path.stat().st_size for path in files.values())
    _limit(input_bytes > MAX_UNPACKED_BYTES, "payload_bytes", input_bytes, MAX_UNPACKED_BYTES)
    for path in files.values():
        _limit(path.stat().st_size > MAX_FILE_BYTES, "file_bytes", path.stat().st_size, MAX_FILE_BYTES)
    images, _inventory = _native_images(root, files)
    if not images:
        raise ValueError("native capsule requires at least one Mach-O image")
    signatures, signing_detail = _signing_metadata(images, signature_inspector, entitlements_inspector)
    if any(
        name == "tools/git" or name.startswith(("licenses/managed-git/", "provenance/managed-git/")) for name in files
    ):
        verify_managed_git_runtime(root, signature_inspector=signature_inspector)

    metadata_name = "metadata/native-signing.json"
    if metadata_name in files:
        raise ValueError("generated signing metadata path collides with runtime input")
    normalized_closure["native-signing-v1"] = [metadata_name]
    sources: dict[str, Path | bytes] = {**files, metadata_name: signing_detail}
    modes = {name: 0o500 if name in images else 0o400 for name in sources}
    _limit(len(sources) > MAX_FILES, "file_count", len(sources), MAX_FILES)
    file_records: dict[str, FileRecord] = {}
    for name in sorted(sources):
        source = sources[name]
        size, digest = _hash_path(source) if isinstance(source, Path) else (len(source), sha256(source))
        _limit(size > MAX_FILE_BYTES, "file_bytes", size, MAX_FILE_BYTES)
        file_records[name] = {"size": size, "sha256": digest, "mode": modes[name]}
    total = sum(int(record["size"]) for record in file_records.values())
    _limit(total > MAX_UNPACKED_BYTES, "payload_bytes", total, MAX_UNPACKED_BYTES)
    expected_archive_size = (
        sum(512 + ((int(record["size"]) + 511) // 512) * 512 for record in file_records.values()) + 1024
    )
    _limit(expected_archive_size > MAX_ARCHIVE_BYTES, "archive_bytes", expected_archive_size, MAX_ARCHIVE_BYTES)

    outputs = BuildResult(
        archive=destination / "capsule.tar",
        manifest=destination / "manifest.json",
        signature=destination / "manifest.sig" if private_key is not None else None,
        summary=destination / "summary.json",
    )
    output_names = ("capsule.tar", "manifest.json", "summary.json")
    if private_key is not None:
        output_names += ("manifest.sig",)
    elif (destination / "manifest.sig").exists() or (destination / "manifest.sig").is_symlink():
        raise ValueError("unsigned output contains a stale signature sidecar")
    with _exclusive_outputs(destination, output_names) as streams:
        archive_size, archive_digest = _stream_archive(streams["capsule.tar"], sources, file_records)
        if archive_size != expected_archive_size:
            raise ValueError("deterministic USTAR size mismatch")
        ordered_closure = {name: normalized_closure[name] for name in sorted(normalized_closure)}
        document = {
            "schema": "specfact-native-capsule-v1",
            "os": "darwin",
            "architecture": "arm64",
            "environment_id": environment_id,
            "abi": environment_id.rsplit("-", 1)[-1],
            "backend": backend,
            "policy": policy,
            "analyzer_versions": {name: analyzer_versions[name] for name in sorted(analyzer_versions)},
            "archive": {"size": archive_size, "sha256": archive_digest},
            "files": file_records,
            "closure": ordered_closure,
            "closure_sha256": sha256(_canonical(ordered_closure)),
            "native_signatures": signatures,
        }
        manifest_bytes = _canonical(document)
        _limit(len(manifest_bytes) > MAX_MANIFEST, "manifest_bytes", len(manifest_bytes), MAX_MANIFEST)
        signature = _sign(manifest_bytes, private_key) if private_key is not None else None
        summary = {
            "archive_sha256": document["archive"]["sha256"],
            "archive_size": archive_size,
            "environment_id": environment_id,
            "file_count": len(sources),
            "manifest_sha256": sha256(manifest_bytes),
            "native_image_count": len(images),
            "production_eligible": False,
            "publication": "candidate-only",
            "signing_mode": "adhoc",
        }

        _write_output(streams["manifest.json"], manifest_bytes)
        if signature is not None:
            _write_output(streams["manifest.sig"], signature.encode("ascii"))
        else:
            summary["manifest_authenticated"] = False
        _write_output(streams["summary.json"], _canonical(summary) + b"\n")
    return outputs


def _load_private_key(path: Path) -> object:
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def main() -> int:
    if sys.argv[1:2] == ["prepare-managed-git"]:
        parser = argparse.ArgumentParser(description="Install explicit managed Git maintainer input; no signing key.")
        parser.add_argument("--payload-root", type=Path, required=True)
        selected = parser.add_mutually_exclusive_group(required=True)
        selected.add_argument("--git-artifact-root", type=Path)
        selected.add_argument("--source-archive", type=Path)
        parser.add_argument("--git-build-output", type=Path)
        parser.add_argument("--jobs", type=int, choices=range(1, 5), default=2)
        args = parser.parse_args(sys.argv[2:])
        receipt = prepare_managed_git_input(
            payload_root=args.payload_root,
            git_artifact_root=args.git_artifact_root,
            source_archive=args.source_archive,
            git_build_output=args.git_build_output,
            jobs=args.jobs,
        )
        print(_canonical(receipt).decode("ascii"))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--environment-id", choices=sorted(SUPPORTED_ENVIRONMENTS), required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--analyzer-version-policy", type=Path, required=True)
    signing = parser.add_mutually_exclusive_group(required=True)
    signing.add_argument("--private-key", type=Path, help="Protected CI/CD publisher key only")
    signing.add_argument("--unsigned", action="store_true", help="Build final bytes without signing authority")
    args = parser.parse_args()
    closure = json.loads(args.closure.read_text(encoding="utf-8"))
    if not isinstance(closure, dict):
        parser.error("closure must be a JSON object")
    version_policy = json.loads(args.analyzer_version_policy.read_text(encoding="utf-8"))
    if (
        not isinstance(version_policy, dict)
        or version_policy.get("schema") != "specfact-native-candidate-policy-v1"
        or not isinstance(version_policy.get("analyzer_versions"), dict)
    ):
        parser.error("analyzer version policy must be a native candidate policy")
    result = build_native_capsule(
        runtime_root=args.runtime_root,
        output_dir=args.output_dir,
        closure=closure,
        environment_id=args.environment_id,
        backend=args.backend,
        policy=args.policy,
        analyzer_versions=version_policy["analyzer_versions"],
        private_key=None if args.unsigned else _load_private_key(args.private_key),
    )
    print(result.summary.read_text(encoding="ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
