"""Sealed offline wheel preparation for the native macOS capsule.

The trusted controller authenticates an acquisition descriptor through the
required verifier callback. This module then revalidates its exact manager lock
and wheelhouse closure before extracting compatible wheels into a private root.
It never resolves dependencies, imports project code, starts a process, or uses
the network.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform as platform_module
import re
import shutil
import stat
import sys
import tempfile
import zipfile
import zlib
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from packaging.tags import Tag, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename


DESCRIPTOR_SCHEMA = "specfact-macos-project-acquisition-v1"
LOCK_SCHEMA = "specfact-macos-offline-manager-lock-v1"
EVIDENCE_SCHEMA = "specfact-native-project-preparation-evidence-v1"
MANAGER_VERSIONS = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
SUPPORTED_ABIS = frozenset({"cp311", "cp312", "cp313"})
SUPPORTED_PLATFORM = "macos-arm64"
MAX_METADATA_BYTES = 64 * 1024**2
MAX_WHEELS = 4_096
MAX_WHEEL_BYTES = 512 * 1024**2
MAX_FILES = 30_000
MAX_UNPACKED_BYTES = 512 * 1024**2
MAX_FILE_BYTES = 128 * 1024**2
MAX_PATH_BYTES = 240
MAX_PATH_DEPTH = 32
CHUNK = 64 * 1024
EVIDENCE_NAME = ".specfact-preparation-evidence.json"
RESULT_NAME = "project-preparation.json"
RESULT_SCHEMA = "specfact-native-project-preparation-result-v1"
PUBLIC_KEY_NAME = "project-acquisition-public.pem"
BROKER_OUTPUTS = frozenset({"managed-stdout.bin", "managed-stderr.bin"})
MAX_PUBLIC_KEY_BYTES = 16 * 1024
MAX_SIGNATURE_TEXT_BYTES = 256
EXIT_COMPLETE = 0
EXIT_INCOMPLETE = 74
EXIT_INVALID_REQUEST = 76
EXIT_OUTPUT_COLLISION = 78

SignatureVerifier = Callable[[bytes, dict[str, str]], bool]
VerifiedWheel = tuple[dict[str, Any], str, int]


class NativeProjectPreparationError(ValueError):
    """Authenticated preparation input or output violated the closed contract."""


class UnsupportedWheelLayoutError(NativeProjectPreparationError):
    """An authenticated wheel needs an installation scheme we cannot provide."""

    def __init__(self, wheel_name: str) -> None:
        super().__init__(f"wheel .data installation scheme is unsupported: {wheel_name}")
        self.wheel_name = wheel_name


def _fail(reason: str) -> NativeProjectPreparationError:
    return NativeProjectPreparationError(f"native project preparation rejected: {reason}")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise _fail(f"invalid JSON constant: {value}")


def _read_canonical_json(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise _fail(f"{label} must be a regular file")
    metadata = path.stat()
    if metadata.st_size <= 0 or metadata.st_size > MAX_METADATA_BYTES:
        raise _fail(f"{label} exceeds the metadata byte limit")
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _fail(f"{label} is invalid JSON") from error
    if not isinstance(value, dict) or raw != _canonical(value):
        raise _fail(f"{label} is not canonical JSON")
    return raw, value


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while block := os.read(descriptor, CHUNK):
        digest.update(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return digest.hexdigest()


def _closed_manager(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"name", "version"}:
        raise _fail("manager identity is malformed")
    name, version = value.get("name"), value.get("version")
    if not isinstance(name, str) or name not in MANAGER_VERSIONS:
        raise _fail("manager is not admitted")
    if version != MANAGER_VERSIONS[name]:
        raise _fail("manager version is not admitted")
    return {"name": name, "version": str(version)}


def _authenticate_descriptor(path: Path, verifier: SignatureVerifier) -> dict[str, Any]:
    _raw, descriptor = _read_canonical_json(path, "descriptor")
    expected_fields = {
        "schema",
        "project",
        "corpus_identity",
        "abi",
        "platform",
        "manager",
        "source",
        "artifacts",
        "manager_lock",
        "acquisition_executed_project_code",
        "content_sha256",
        "signature",
    }
    if set(descriptor) != expected_fields or descriptor.get("schema") != DESCRIPTOR_SCHEMA:
        raise _fail("descriptor fields or schema are invalid")
    signature = descriptor.get("signature")
    if (
        not isinstance(signature, dict)
        or set(signature) != {"algorithm", "key_id", "value"}
        or any(not isinstance(item, str) or not item for item in signature.values())
    ):
        raise _fail("descriptor authentication envelope is invalid")
    signed = {key: value for key, value in descriptor.items() if key != "signature"}
    try:
        authenticated = verifier(_canonical(signed), dict(signature))
    except Exception as error:
        raise _fail("descriptor authentication failed") from error
    if authenticated is not True:
        raise _fail("descriptor authentication failed")
    unsigned = {key: value for key, value in signed.items() if key != "content_sha256"}
    if descriptor.get("content_sha256") != _digest_bytes(_canonical(unsigned)):
        raise _fail("descriptor content digest mismatch")
    if descriptor.get("acquisition_executed_project_code") is not False:
        raise _fail("descriptor does not prove code-free acquisition")
    _closed_manager(descriptor.get("manager"))
    if descriptor.get("platform") != SUPPORTED_PLATFORM:
        raise _fail("platform is not macOS ARM64")
    if descriptor.get("abi") not in SUPPORTED_ABIS:
        raise _fail("ABI is not admitted")
    return descriptor


def _validate_lock(path: Path, descriptor: Mapping[str, Any]) -> dict[str, Any]:
    raw, lock = _read_canonical_json(path, "manager lock")
    binding = descriptor.get("manager_lock")
    if (
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256"}
        or binding.get("sha256") != _digest_bytes(raw)
        or PurePosixPath(str(binding.get("path", ""))).name != path.name
    ):
        raise _fail("manager lock binding mismatch")
    if set(lock) != {"schema", "manager", "selection", "abi", "platform", "artifacts"}:
        raise _fail("manager lock fields are invalid")
    if lock.get("schema") != LOCK_SCHEMA:
        raise _fail("manager lock schema is invalid")
    if _closed_manager(lock.get("manager")) != _closed_manager(descriptor.get("manager")):
        raise _fail("manager lock manager mismatch")
    if lock.get("abi") != descriptor.get("abi"):
        raise _fail("manager lock ABI mismatch")
    if lock.get("platform") != descriptor.get("platform"):
        raise _fail("manager lock platform mismatch")
    selection = lock.get("selection")
    if (
        not isinstance(selection, dict)
        or set(selection) != {"groups", "environment"}
        or not isinstance(selection.get("groups"), list)
        or any(not isinstance(group, str) or not group for group in selection["groups"])
        or not isinstance(selection.get("environment"), str)
        or not selection["environment"]
    ):
        raise _fail("manager lock selection is invalid")
    return lock


def _validate_bundle_paths(
    descriptor_path: Path,
    manager_lock_path: Path,
    wheelhouse: Path,
    descriptor: Mapping[str, Any],
) -> None:
    root = descriptor_path.parent
    binding = descriptor["manager_lock"]
    manager = descriptor["manager"]
    expected_relative = f"locks/{manager['name']}.json"
    if (
        not descriptor_path.is_absolute()
        or descriptor_path.name != "descriptor.json"
        or root.is_symlink()
        or not root.is_dir()
        or root.resolve() != root.absolute()
        or binding.get("path") != expected_relative
        or manager_lock_path != root / expected_relative
        or wheelhouse != root / "wheelhouse"
    ):
        raise _fail("descriptor, manager lock, or wheelhouse path is not the exact cached bundle layout")


def _compatible_tag(tag: Tag, abi: str) -> bool:
    interpreter, wheel_abi, platform = tag.interpreter, tag.abi, tag.platform
    selected_minor = int(abi.removeprefix("cp3"))
    pure_interpreter = interpreter in {"py3", f"py3{selected_minor}"}
    interpreter_match = interpreter == abi or pure_interpreter
    if platform == "any":
        return interpreter_match and wheel_abi == "none"
    minimum = re.fullmatch(r"macosx_(\d+)_(\d+)_(?:arm64|universal2)", platform)
    if minimum is None:
        return False
    # Explicit inputs keep the selected capsule ABI independent of host Python.
    compatible = cpython_tags((3, selected_minor), abis=[abi], platforms=[platform])
    if not (pure_interpreter and wheel_abi == "none") and tag not in compatible:
        return False
    host = re.match(r"^(\d+)\.(\d+)(?:\.|$)", platform_module.mac_ver()[0])
    if host is None:
        return False
    return (int(minimum[1]), int(minimum[2])) <= (int(host[1]), int(host[2]))


def _artifact_closure(descriptor: Mapping[str, Any], lock: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts = descriptor.get("artifacts")
    lock_artifacts = lock.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts or len(artifacts) > MAX_WHEELS:
        raise _fail("artifact count is invalid")
    if not isinstance(lock_artifacts, list) or len(lock_artifacts) != len(artifacts):
        raise _fail("manager lock artifact closure mismatch")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected_record_fields = {
        "package",
        "version",
        "filename",
        "url",
        "sha256",
        "size",
        "kind",
        "tags",
        "build_hook_required",
        "mode",
    }
    lock_fields = {"package", "version", "filename", "sha256", "kind", "tags"}
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict) or set(record) != expected_record_fields:
            raise _fail("artifact descriptor is malformed")
        filename = record.get("filename")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename.casefold() in seen
        ):
            raise _fail("artifact filename is invalid or duplicated")
        seen.add(filename.casefold())
        locked = lock_artifacts[index]
        if not isinstance(locked, dict) or set(locked) != lock_fields:
            raise _fail("manager lock artifact is malformed")
        if locked != {key: record[key] for key in lock_fields}:
            raise _fail("manager lock artifact closure mismatch")
        if record.get("kind") != "wheel" or record.get("build_hook_required") is not False:
            normalized.append(dict(record))
            continue
        if (
            not isinstance(record.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None
            or type(record.get("size")) is not int
            or not 0 < record["size"] <= MAX_WHEEL_BYTES
            or record.get("mode") != 0o600
        ):
            raise _fail("wheel digest, size, or mode is invalid")
        try:
            parsed_name, parsed_version, _build, tags = parse_wheel_filename(filename)
        except ValueError as error:
            raise _fail("wheel filename is invalid") from error
        tag_names = sorted(str(tag) for tag in tags)
        if tag_names != record.get("tags"):
            raise _fail("wheel tag inventory mismatch")
        if not any(_compatible_tag(tag, str(descriptor["abi"])) for tag in tags):
            raise _fail("wheel tag is incompatible with macOS ARM64 or selected ABI")
        if canonicalize_name(str(record.get("package"))) != canonicalize_name(parsed_name):
            raise _fail("wheel package identity mismatch")
        if str(record.get("version")) != str(parsed_version):
            raise _fail("wheel version identity mismatch")
        normalized.append(dict(record))
    return normalized


def _validate_wheelhouse(
    root: Path,
    artifacts: list[dict[str, Any]],
    *,
    effective_mode: int = 0o600,
) -> list[VerifiedWheel]:
    if effective_mode not in {0o400, 0o600}:
        raise _fail("wheel effective mode is not admitted")
    if root.is_symlink() or not root.is_dir():
        raise _fail("wheelhouse must be a regular directory")
    expected = {str(record["filename"]) for record in artifacts}
    actual: set[str] = set()
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise _fail("wheelhouse contains a link or special file")
        actual.add(path.name)
    if actual != expected:
        raise _fail("wheelhouse closure contains missing or extra artifacts")
    verified: list[VerifiedWheel] = []
    try:
        for record in artifacts:
            name = str(record["filename"])
            try:
                descriptor = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except OSError as error:
                raise _fail(f"cannot open wheel safely: {name}") from error
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise _fail(f"wheel is not a regular file: {name}")
                if (
                    metadata.st_size != record.get("size")
                    or record.get("mode") != 0o600
                    or stat.S_IMODE(metadata.st_mode) != effective_mode
                ):
                    raise _fail(f"wheel size or mode mismatch: {name}")
                if _digest_descriptor(descriptor) != record.get("sha256"):
                    raise _fail(f"wheel digest mismatch: {name}")
                verified.append((record, name, descriptor))
            except Exception:
                os.close(descriptor)
                raise
        return verified
    except Exception:
        for _record, _name, descriptor in verified:
            os.close(descriptor)
        raise


def _wheel_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    try:
        encoded = value.encode("ascii", "strict")
    except UnicodeEncodeError as error:
        raise _fail("wheel path must use the admitted ASCII profile") from error
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or "\0" in value
        or len(encoded) > MAX_PATH_BYTES
        or len(path.parts) > MAX_PATH_DEPTH
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise _fail("wheel path is noncanonical or escapes the preparation root")
    return path


def _member_kind(info: zipfile.ZipInfo) -> str:
    mode = info.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if info.is_dir():
        if file_type not in {0, stat.S_IFDIR}:
            raise _fail("wheel contains a link or special file")
        return "directory"
    if file_type not in {0, stat.S_IFREG}:
        raise _fail("wheel contains a link or special file")
    if info.flag_bits & 0x1:
        raise _fail("encrypted wheel members are unsupported")
    return "file"


def _zip_from_descriptor(descriptor: int) -> tuple[Any, zipfile.ZipFile]:
    stream = os.fdopen(os.dup(descriptor), "rb")
    try:
        return stream, zipfile.ZipFile(stream)
    except Exception:
        stream.close()
        raise


def _preflight_wheels(wheels: list[VerifiedWheel]) -> tuple[int, int, int]:
    aliases: dict[str, str] = {}
    kinds: dict[str, str] = {}
    files = 0
    total = 0
    native_extensions = 0
    for _record, wheel_name, descriptor in wheels:
        try:
            stream, archive = _zip_from_descriptor(descriptor)
            with stream, archive:
                for info in archive.infolist():
                    relative = _wheel_path(info.filename.rstrip("/") if info.is_dir() else info.filename)
                    kind = _member_kind(info)
                    if relative.parts[0].endswith(".data") and (len(relative.parts) > 1 or kind == "directory"):
                        raise UnsupportedWheelLayoutError(wheel_name)
                    for offset in range(1, len(relative.parts) + 1):
                        name = PurePosixPath(*relative.parts[:offset]).as_posix()
                        inferred_kind = kind if offset == len(relative.parts) else "directory"
                        folded = name.casefold()
                        previous = aliases.get(folded)
                        if previous is not None and previous != name:
                            raise _fail(f"wheel case-insensitive path collision: {previous} and {name}")
                        if name in kinds and (kinds[name] != inferred_kind or inferred_kind == "file"):
                            raise _fail(f"wheel output collision: {name}")
                        aliases[folded] = name
                        kinds[name] = inferred_kind
                    if kind == "directory":
                        continue
                    if info.file_size < 0 or info.file_size > MAX_FILE_BYTES:
                        raise _fail("wheel member exceeds the file byte limit")
                    files += 1
                    total += info.file_size
                    if files > MAX_FILES:
                        raise _fail("wheel file count exceeds the fixed limit")
                    if total > MAX_UNPACKED_BYTES:
                        raise _fail("wheel content exceeds the uncompressed byte limit")
                    if relative.suffix in {".so", ".dylib"}:
                        native_extensions += 1
        except (OSError, zipfile.BadZipFile) as error:
            raise _fail(f"wheel ZIP is invalid: {wheel_name}") from error
    return files, total, native_extensions


def _write_file(archive: zipfile.ZipFile, info: zipfile.ZipInfo, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    digest = hashlib.sha256()
    written = 0
    descriptor = os.open(destination, flags, 0o400)
    try:
        with archive.open(info, "r") as source, os.fdopen(descriptor, "wb", closefd=True) as target:
            while block := source.read(CHUNK):
                written += len(block)
                if written > info.file_size or written > MAX_FILE_BYTES:
                    raise _fail("wheel member expanded beyond its declared size")
                target.write(block)
                digest.update(block)
            if written != info.file_size:
                raise _fail("wheel member size mismatch")
            target.flush()
            os.fsync(target.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return digest.hexdigest()


def _extract_wheels(wheels: list[VerifiedWheel], destination: Path) -> dict[str, dict[str, int | str]]:
    inventory: dict[str, dict[str, int | str]] = {}
    for _record, name, descriptor in wheels:
        try:
            stream, archive = _zip_from_descriptor(descriptor)
            with stream, archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    relative = _wheel_path(info.filename)
                    output = destination.joinpath(*relative.parts)
                    digest = _write_file(archive, info, output)
                    inventory[relative.as_posix()] = {
                        "mode": 0o400,
                        "sha256": digest,
                        "size": info.file_size,
                    }
        except NativeProjectPreparationError:
            raise
        except (EOFError, OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as error:
            raise _fail(f"wheel extraction failed: {name}") from error
    return dict(sorted(inventory.items()))


def _base_evidence(descriptor: Mapping[str, Any], status: str, diagnostic: str) -> dict[str, Any]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "status": status,
        "diagnostic": diagnostic,
        "manager": dict(descriptor["manager"]),
        "abi": descriptor["abi"],
        "platform": descriptor["platform"],
        "acquisition_content_sha256": descriptor["content_sha256"],
        "project_code_executed": False,
        "build_hooks_executed": False,
        "network_used": False,
        "host_manager_used": False,
        "production_eligible": False,
        "project_execution_proven": False,
    }


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise _fail("short evidence write")
        view = view[written:]


def _write_evidence(root: Path, evidence: Mapping[str, Any]) -> None:
    path = root / EVIDENCE_NAME
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        _write_all(descriptor, _canonical(evidence) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _seal_output(root: Path) -> None:
    for directory, names, _files in os.walk(root, topdown=False, followlinks=False):
        for name in names:
            path = Path(directory) / name
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise _fail("prepared output contains a link or special directory")
            path.chmod(0o500)
    root.chmod(0o500)


def _remove_partial(root: Path) -> None:
    if not root.exists() or root.is_symlink():
        return
    for directory, names, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o600)
        for name in names:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o700)
    root.chmod(0o700)
    shutil.rmtree(root)


def _safe_output(output: Path) -> None:
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise _fail("output must be an absent absolute path")
    parent = output.parent
    if parent.is_symlink() or not parent.is_dir() or parent.resolve() != parent.absolute():
        raise _fail("output parent must be a canonical regular directory")


def prepare_project(
    *,
    descriptor_path: Path,
    manager_lock_path: Path,
    wheelhouse: Path,
    output: Path,
    verifier: SignatureVerifier,
) -> dict[str, Any]:
    """Install one authenticated wheel closure without executing project code.

    Unsupported sdists/build hooks return canonical ``INCOMPLETE`` evidence.
    Integrity, platform, path, and closure violations fail closed and publish no
    preparation root.
    """

    descriptor = _authenticate_descriptor(descriptor_path, verifier)
    _validate_bundle_paths(descriptor_path, manager_lock_path, wheelhouse, descriptor)
    lock = _validate_lock(manager_lock_path, descriptor)
    artifacts = _artifact_closure(descriptor, lock)
    wheels = _validate_wheelhouse(wheelhouse, artifacts, effective_mode=0o400)
    try:
        unsupported = [record["filename"] for record in artifacts if record.get("kind") != "wheel"]
        if unsupported:
            return {
                **_base_evidence(
                    descriptor,
                    "INCOMPLETE",
                    "build hook required; sealed adapter does not execute project code or host toolchains",
                ),
                "unsupported_artifacts": sorted(unsupported),
                "artifact_count": len(artifacts),
            }
        _safe_output(output)
        try:
            file_count, unpacked_bytes, native_extensions = _preflight_wheels(wheels)
        except UnsupportedWheelLayoutError as error:
            return {
                **_base_evidence(descriptor, "INCOMPLETE", str(error)),
                "unsupported_artifacts": [error.wheel_name],
                "artifact_count": len(artifacts),
            }
        temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", suffix=".partial", dir=output.parent))
        claim = output.parent / f".{output.name}.installing"
        claim_descriptor: int | None = None
        try:
            claim_descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            inventory = _extract_wheels(wheels, temporary)
            if (
                len(inventory) != file_count
                or sum(int(record["size"]) for record in inventory.values()) != unpacked_bytes
            ):
                raise _fail("extracted wheel inventory differs from preflight")
            evidence = {
                **_base_evidence(descriptor, "COMPLETE", ""),
                "artifact_count": len(artifacts),
                "file_count": file_count,
                "unpacked_bytes": unpacked_bytes,
                "native_extension_count": native_extensions,
                "inventory_sha256": _digest_bytes(_canonical(inventory)),
            }
            _write_evidence(temporary, evidence)
            _seal_output(temporary)
            if output.exists() or output.is_symlink():
                raise _fail("output appeared during preparation")
            os.rename(temporary, output)
            return evidence
        except FileExistsError as error:
            raise _fail("output installation is already in progress") from error
        finally:
            if claim_descriptor is not None:
                os.close(claim_descriptor)
                claim.unlink(missing_ok=True)
            if temporary.exists():
                _remove_partial(temporary)
    finally:
        for _record, _name, wheel_descriptor in wheels:
            os.close(wheel_descriptor)


def _root(raw: str, *, writable: bool, private_tree: bool = False) -> Path:
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink():
        raise _fail("broker roots must be absolute non-symlink directories")
    resolved = path.resolve(strict=True)
    if resolved != path or not resolved.is_dir():
        raise _fail("broker root identity changed during resolution")
    mode = resolved.stat().st_mode
    if private_tree and (not mode & stat.S_IWUSR or mode & (stat.S_IRWXG | stat.S_IRWXO)):
        raise _fail("private broker root is not owner-only")
    if writable and not private_tree and not mode & stat.S_IWUSR:
        raise _fail("writable broker root is not owner-writable")
    if not writable and not private_tree and mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise _fail("immutable broker root is writable")
    return resolved


def _invocation_roots() -> tuple[Path, Path, Path, Path, str]:
    if len(sys.argv) != 6:
        raise _fail("project manager requires four roots and one fixed manager")
    capsule = _root(sys.argv[1], writable=True, private_tree=True)
    project = _root(sys.argv[2], writable=False)
    output = _root(sys.argv[3], writable=True)
    temporary = _root(sys.argv[4], writable=True)
    manager = sys.argv[5]
    roots = (capsule, project, output, temporary)
    if (
        manager not in MANAGER_VERSIONS
        or len(set(roots)) != len(roots)
        or any(
            left.is_relative_to(right) or right.is_relative_to(left)
            for index, left in enumerate(roots)
            for right in roots[index + 1 :]
        )
    ):
        raise _fail("manager plan or root separation is invalid")
    return capsule, project, output, temporary, manager


def _admit_initial_output(output: Path) -> bool:
    if {path.name for path in output.iterdir()} != BROKER_OUTPUTS:
        return False
    for name in BROKER_OUTPUTS:
        path = output / name
        if path.is_symlink():
            return False
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode) or not metadata.st_mode & stat.S_IWUSR:
            return False
    return True


def _public_key(capsule: Path) -> tuple[ed25519.Ed25519PublicKey, bytes]:
    path = capsule / "trust" / PUBLIC_KEY_NAME
    if path.is_symlink() or path.resolve(strict=True) != path.absolute():
        raise _fail("project acquisition public key path is not immutable")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            or not 0 < metadata.st_size <= MAX_PUBLIC_KEY_BYTES
        ):
            raise _fail("project acquisition public key is not a bounded immutable file")
        value = bytearray()
        while block := os.read(descriptor, min(CHUNK, MAX_PUBLIC_KEY_BYTES + 1 - len(value))):
            value.extend(block)
            if len(value) > MAX_PUBLIC_KEY_BYTES:
                raise _fail("project acquisition public key exceeds its byte limit")
    finally:
        os.close(descriptor)
    try:
        key = serialization.load_pem_public_key(bytes(value))
    except (TypeError, ValueError) as error:
        raise _fail("project acquisition public key is invalid PEM") from error
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise _fail("project acquisition public key is not Ed25519")
    return key, bytes(value)


def _broker_verifier(capsule: Path, manager: str) -> SignatureVerifier:
    key, public_pem = _public_key(capsule)
    key_id = _digest_bytes(public_pem)
    expected_manager = {"name": manager, "version": MANAGER_VERSIONS[manager]}

    def verify(payload: bytes, envelope: dict[str, str]) -> bool:
        algorithm = envelope.get("algorithm")
        envelope_key_id = envelope.get("key_id")
        encoded = envelope.get("value")
        if (
            algorithm != "Ed25519-SHA256"
            or envelope_key_id != key_id
            or not isinstance(encoded, str)
            or not 0 < len(encoded.encode("ascii", "strict")) <= MAX_SIGNATURE_TEXT_BYTES
        ):
            raise _fail("descriptor Ed25519-SHA256 envelope is invalid")
        try:
            signature = base64.b64decode(encoded, validate=True)
        except (ValueError, UnicodeEncodeError) as error:
            raise _fail("descriptor signature is not strict base64") from error
        if len(signature) != 64:
            raise _fail("descriptor Ed25519 signature length is invalid")
        try:
            signed = json.loads(payload.decode("ascii", "strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _fail("descriptor signed payload is invalid") from error
        if not isinstance(signed, dict) or signed.get("manager") != expected_manager:
            raise _fail("descriptor manager differs from the fixed broker plan")
        try:
            key.verify(signature, payload)
        except InvalidSignature as error:
            raise _fail("descriptor Ed25519 signature is invalid") from error
        return True

    return verify


def _write_result(output: Path, *, status: str, evidence: Mapping[str, Any]) -> None:
    result = {"evidence": dict(evidence), "schema": RESULT_SCHEMA, "status": status}
    descriptor = os.open(
        output / RESULT_NAME,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        _write_all(descriptor, _canonical(result) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rejected_evidence(manager: str, diagnostic: str) -> dict[str, Any]:
    return {
        "build_hooks_executed": False,
        "diagnostic": diagnostic,
        "host_manager_used": False,
        "manager": manager if manager in MANAGER_VERSIONS else "unknown",
        "network_used": False,
        "project_code_executed": False,
    }


def main() -> int:
    """Prepare one broker-fixed project wheel closure without spawning or network."""

    output: Path | None = None
    manager = "unknown"
    admitted_output = False
    try:
        capsule, project, output, _temporary, manager = _invocation_roots()
        admitted_output = _admit_initial_output(output)
        if not admitted_output:
            return EXIT_OUTPUT_COLLISION
        bundle = project / ".specfact-native-project"
        evidence = prepare_project(
            descriptor_path=bundle / "descriptor.json",
            manager_lock_path=bundle / "locks" / f"{manager}.json",
            wheelhouse=bundle / "wheelhouse",
            output=output / "site-packages",
            verifier=_broker_verifier(capsule, manager),
        )
        status = str(evidence.get("status", ""))
        if status not in {"COMPLETE", "INCOMPLETE"}:
            raise _fail("preparation returned an unsupported status")
        _write_result(output, status=status, evidence=evidence)
        return EXIT_COMPLETE if status == "COMPLETE" else EXIT_INCOMPLETE
    except FileExistsError:
        return EXIT_OUTPUT_COLLISION
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        if output is not None and admitted_output:
            try:
                _write_result(
                    output,
                    status="REJECTED",
                    evidence=_rejected_evidence(manager, str(error)),
                )
            except (FileExistsError, OSError):
                return EXIT_OUTPUT_COLLISION
        return EXIT_INVALID_REQUEST


__all__ = [
    "EVIDENCE_SCHEMA",
    "EXIT_COMPLETE",
    "EXIT_INCOMPLETE",
    "EXIT_INVALID_REQUEST",
    "EXIT_OUTPUT_COLLISION",
    "MANAGER_VERSIONS",
    "MAX_PUBLIC_KEY_BYTES",
    "RESULT_SCHEMA",
    "NativeProjectPreparationError",
    "main",
    "prepare_project",
]


if __name__ == "__main__":
    raise SystemExit(main())
