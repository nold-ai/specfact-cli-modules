"""Prepare and seal project dependencies through the native macOS broker."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import urlsplit

from specfact_code_review.run import native_backend, native_execution, native_project_manager, runtime_native
from specfact_code_review.run.native_project_catalog import resolve_project_artifact
from specfact_code_review.run.runtime_artifacts import load_runtime, seal_runtime, validate_build_artifact
from specfact_code_review.run.runtime_models import PreparedRuntime, ProjectPlan, ProjectRuntimeError, document_digest
from specfact_code_review.run.runtime_sources import is_excluded_source, source_identity, verify_inputs


_MANAGER_VERSIONS = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
_RESULT_SCHEMA = "specfact-native-project-preparation-result-v1"
_MAX_RESULT_BYTES = 4 << 20
_MAX_RUNTIME_FILES = 100_000
_MAX_RUNTIME_BYTES = 512 << 20
_MAX_NATIVE_IMAGES = 1_024
_MAX_NATIVE_BYTES = 256 << 20
_MAX_NATIVE_INVENTORY_BYTES = 1 << 20
_COPY_BLOCK_BYTES = 1 << 20
_MAX_ACQUISITION_BUNDLE_BYTES = 1 << 30
_MAX_ACQUISITION_ARCHIVE_BYTES = _MAX_ACQUISITION_BUNDLE_BYTES
_MAX_ACQUISITION_FILES = 120_000
_MAX_ACQUISITION_PATH_BYTES = 512
_ACQUISITION_TIMEOUT_SECONDS = 60
_ACQUISITION_URL_ENV = "SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_URL"

_Identity = tuple[int, int, int, int, int, int, int]
_TreeEntry = tuple[str, _Identity]


def _identity(metadata: os.stat_result) -> _Identity:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _runtime_tree(root: Path, *, exclude_vcs: bool = False) -> dict[str, _TreeEntry]:
    """Capture a bounded, indirection-free tree without following project links."""
    entries: dict[str, _TreeEntry] = {}
    files = 0
    total = 0
    pending = [root]
    try:
        while pending:
            current = pending.pop()
            metadata = current.lstat()
            relative = "." if current == root else current.relative_to(root).as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                raise ProjectRuntimeError(f"project_native_runtime_symlink:{relative}")
            if not stat.S_ISDIR(metadata.st_mode):
                raise ProjectRuntimeError(f"project_native_runtime_root_invalid:{relative}")
            entries[relative] = ("directory", _identity(metadata))
            children = sorted(os.scandir(current), key=lambda entry: entry.name)
            for child in children:
                if exclude_vcs and current == root and child.name == ".git":
                    continue  # Copied VCS context has its own verification boundary.
                path = Path(child.path)
                child_relative = path.relative_to(root).as_posix()
                child_metadata = child.stat(follow_symlinks=False)
                if stat.S_ISLNK(child_metadata.st_mode):
                    raise ProjectRuntimeError(f"project_native_runtime_symlink:{child_relative}")
                if stat.S_ISDIR(child_metadata.st_mode):
                    pending.append(path)
                    continue
                if not stat.S_ISREG(child_metadata.st_mode):
                    raise ProjectRuntimeError(f"project_native_runtime_special_file:{child_relative}")
                if child_metadata.st_nlink != 1:
                    raise ProjectRuntimeError(f"project_native_runtime_hardlink:{child_relative}")
                files += 1
                total += child_metadata.st_size
                if files > _MAX_RUNTIME_FILES or total > _MAX_RUNTIME_BYTES:
                    raise ProjectRuntimeError("project_native_runtime_bounds_exceeded")
                entries[child_relative] = ("file", _identity(child_metadata))
    except FileNotFoundError as exc:
        raise ProjectRuntimeError("project_native_runtime_identity_changed") from exc
    return entries


def _assert_tree_identity(root: Path, expected: dict[str, _TreeEntry]) -> None:
    if _runtime_tree(root) != expected:
        raise ProjectRuntimeError("project_native_runtime_identity_changed")


def _copy_regular_file(source: Path, destination: Path, expected: _Identity) -> None:
    source_descriptor = -1
    destination_descriptor = -1
    try:
        source_descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        if _identity(os.fstat(source_descriptor)) != expected:
            raise ProjectRuntimeError("project_native_runtime_identity_changed")
        destination_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400,
        )
        copied = 0
        while block := os.read(source_descriptor, _COPY_BLOCK_BYTES):
            copied += len(block)
            if copied > expected[4]:
                raise ProjectRuntimeError("project_native_runtime_identity_changed")
            view = memoryview(block)
            while view:
                written = os.write(destination_descriptor, view)
                view = view[written:]
        if copied != expected[4] or _identity(os.fstat(source_descriptor)) != expected:
            raise ProjectRuntimeError("project_native_runtime_identity_changed")
        os.fsync(destination_descriptor)
    except OSError as exc:
        raise ProjectRuntimeError("project_native_runtime_identity_changed") from exc
    finally:
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
        if source_descriptor >= 0:
            os.close(source_descriptor)
    if _identity(source.lstat()) != expected:
        raise ProjectRuntimeError("project_native_runtime_identity_changed")


def _copy_runtime_tree(source: Path, destination: Path) -> None:
    snapshot = _runtime_tree(source)
    destination.mkdir(mode=0o700)
    directories = sorted(
        (Path(name) for name, (kind, _identity_value) in snapshot.items() if kind == "directory" and name != "."),
        key=lambda path: (len(path.parts), path.as_posix()),
    )
    for relative in directories:
        (destination / relative).mkdir(mode=0o700)
    for name, (kind, identity) in sorted(snapshot.items()):
        if kind == "file":
            _copy_regular_file(source / name, destination / name, identity)
    _assert_tree_identity(source, snapshot)
    for relative in reversed(directories):
        (destination / relative).chmod(0o500)
    destination.chmod(0o500)


def _native_filename(path: Path) -> bool:
    return path.name.endswith(".dylib") or path.name.endswith(".so") or ".so." in path.name


def _admit_native_extensions(
    site_packages: Path,
    *,
    capsule_root: Path,
    declared_count: object,
) -> list[dict[str, Any]]:
    """Admit a bounded, stable Mach-O closure through its native ARM64 slices."""
    if not isinstance(declared_count, int) or isinstance(declared_count, bool) or declared_count < 0:
        raise ProjectRuntimeError("project_native_extension_count_invalid")
    before = _runtime_tree(site_packages)
    candidates = runtime_native._macho_candidates(site_packages)
    native_candidates = [path for path in candidates if _native_filename(path)]
    counted = sum(path.suffix in {".so", ".dylib"} for path in native_candidates)
    if counted != declared_count:
        raise ProjectRuntimeError(
            f"project_native_extension_count_mismatch:declared={declared_count}:observed={counted}"
        )
    native_bytes = sum(path.lstat().st_size for path in candidates)
    if len(candidates) > _MAX_NATIVE_IMAGES or native_bytes > _MAX_NATIVE_BYTES:
        raise ProjectRuntimeError("project_native_macho_inventory_bounds_exceeded")
    for path in native_candidates:
        if not runtime_native._is_macho(path.read_bytes()[:4]):
            relative = path.relative_to(site_packages).as_posix()
            raise ProjectRuntimeError(f"project_native_macho_architecture_unsupported:{relative}:require arm64 Mach-O")
    try:
        records = runtime_native.inventory_native(
            site_packages,
            capsule_root=capsule_root,
            declared=(),
            target_loader=False,
        )
    finally:
        _assert_tree_identity(site_packages, before)
    inventoried = {str(record["path"]) for record in records}
    expected = {path.relative_to(site_packages).as_posix() for path in native_candidates}
    if not expected.issubset(inventoried):
        raise ProjectRuntimeError("project_native_macho_inventory_incomplete")
    for record in records:
        architectures = record.get("architectures")
        if not isinstance(architectures, tuple) or "arm64" not in architectures:
            raise ProjectRuntimeError(
                f"project_native_macho_architecture_unsupported:{record.get('path', '')}:"
                f"architectures={','.join(architectures or ())}; require arm64"
            )
    encoded = json.dumps(records, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(records) > _MAX_NATIVE_IMAGES or len(encoded) > _MAX_NATIVE_INVENTORY_BYTES:
        raise ProjectRuntimeError("project_native_macho_inventory_bounds_exceeded")
    return records


def _cache_key(plan: ProjectPlan, runtime: Any) -> str:
    return document_digest(
        {
            "schema": "specfact-native-project-runtime-cache-v2",
            "project": plan.identity,
            "environment": runtime.environment_id,
            "worker": runtime.identity,
            "manager": {"name": plan.manager, "version": _MANAGER_VERSIONS.get(plan.manager, "")},
        }
    )[7:]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while block := stream.read(_COPY_BLOCK_BYTES):
                digest.update(block)
    except OSError as exc:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed") from exc
    return digest.hexdigest()


def _source_inventory(root: Path) -> dict[str, dict[str, Any]]:
    source = root / "source"
    if source.is_symlink() or not source.is_dir():
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
    inventory: dict[str, dict[str, Any]] = {}
    try:
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
            if path.is_dir():
                continue
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
            inventory[path.relative_to(source).as_posix()] = {
                "sha256": _sha256(path),
                "size": metadata.st_size,
                "mode": stat.S_IMODE(metadata.st_mode),
            }
    except OSError as exc:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed") from exc
    return inventory


def _digest_document(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _verify_source_closure(bundle: Path, descriptor: Mapping[str, Any]) -> None:
    source = descriptor.get("source")
    expected_fields = {
        "url",
        "commit",
        "archive_url",
        "archive_path",
        "archive_sha256",
        "tree_sha256",
        "inventory",
        "trusted_fetch",
    }
    if not isinstance(source, dict) or set(source) != expected_fields:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
    archive = bundle / "source.tar.gz"
    try:
        metadata = archive.lstat()
    except OSError as exc:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed") from exc
    inventory = _source_inventory(bundle)
    trusted = source.get("trusted_fetch")
    trusted_fields = {
        "schema",
        "method",
        "source_url",
        "archive_url",
        "commit",
        "git_tree",
        "archive_sha256",
        "tree_sha256",
        "authenticated_transport",
    }
    if (
        source.get("archive_path") != "source.tar.gz"
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or _sha256(archive) != source.get("archive_sha256")
        or inventory != source.get("inventory")
        or _digest_document(inventory) != source.get("tree_sha256")
        or not isinstance(trusted, dict)
        or set(trusted) != trusted_fields
        or trusted.get("schema") != "specfact-trusted-source-fetch-v1"
        or trusted.get("method") not in {"git-checkout", "github-commit-api-and-archive"}
        or trusted.get("authenticated_transport") is not True
        or trusted.get("source_url") != source.get("url")
        or trusted.get("archive_url") != source.get("archive_url")
        or trusted.get("commit") != source.get("commit")
        or trusted.get("archive_sha256") != source.get("archive_sha256")
        or trusted.get("tree_sha256") != source.get("tree_sha256")
        or re.fullmatch(r"[0-9a-f]{40}", str(trusted.get("git_tree", ""))) is None
    ):
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed")


def _verify_bundle_layout(root: Path) -> None:
    expected = {"COMPLETE", "descriptor.json", "locks", "source", "source.tar.gz", "wheelhouse"}
    try:
        if {entry.name for entry in os.scandir(root)} != expected:
            raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
        files = 0
        total = 0
        for path in root.rglob("*"):
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
            if stat.S_ISDIR(metadata.st_mode):
                continue
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
            files += 1
            total += metadata.st_size
            if files > _MAX_ACQUISITION_FILES or total > _MAX_ACQUISITION_BUNDLE_BYTES:
                raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
    except OSError as exc:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed") from exc


def _verify_acquisition_bundle(
    bundle: Path,
    plan: ProjectPlan,
    runtime: Any,
    *,
    verifier: Callable[[bytes, dict[str, str]], bool] | None = None,
) -> dict[str, Any]:
    """Authenticate the complete publisher bundle before it reaches project code."""
    try:
        root = bundle.resolve(strict=True)
        if bundle.is_symlink() or root != bundle.absolute() or not root.is_dir():
            raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
        _verify_bundle_layout(root)
        selected_verifier = verifier or native_project_manager._broker_verifier(Path(runtime.root), plan.manager)
        descriptor_path = root / "descriptor.json"
        descriptor = native_project_manager._authenticate_descriptor(descriptor_path, selected_verifier)
        manager = descriptor["manager"]["name"]
        lock_path = root / "locks" / f"{manager}.json"
        wheelhouse = root / "wheelhouse"
        native_project_manager._validate_bundle_paths(descriptor_path, lock_path, wheelhouse, descriptor)
        lock = native_project_manager._validate_lock(lock_path, descriptor)
        artifacts = native_project_manager._artifact_closure(descriptor, lock)
        wheels = native_project_manager._validate_wheelhouse(wheelhouse, artifacts)
        for _record, _name, file_descriptor in wheels:
            os.close(file_descriptor)
        complete = root / "COMPLETE"
        if (
            complete.is_symlink()
            or not complete.is_file()
            or stat.S_IMODE(complete.stat().st_mode) != 0o600
            or complete.read_text(encoding="ascii") != f"{descriptor['content_sha256']}\n"
        ):
            raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
        _verify_source_closure(root, descriptor)
        _descriptor(root, plan, runtime.environment_id)
        return descriptor
    except ProjectRuntimeError:
        raise
    except (KeyError, OSError, TypeError, ValueError, UnicodeError) as exc:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed") from exc


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def _safe_archive_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    try:
        encoded = name.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise ProjectRuntimeError("project_native_acquisition_archive_invalid") from exc
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or "\0" in name
        or len(encoded) > _MAX_ACQUISITION_PATH_BYTES
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
    return path


class _AcquisitionTarInfo(tarfile.TarInfo):
    """Bound physical headers before tarfile allocates extension metadata."""

    def _proc_member(self, source: tarfile.TarFile) -> tarfile.TarInfo:
        count = getattr(source, "_specfact_acquisition_headers", 0) + 1
        maximum = _MAX_ACQUISITION_ARCHIVE_BYTES + 1024 * _MAX_ACQUISITION_FILES
        metadata = {tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK}
        chain = getattr(source, "_specfact_acquisition_metadata_chain", 0) + 1 if self.type in metadata else 0
        # Extension metadata always requires a following physical header.
        maximum_headers = 2 * _MAX_ACQUISITION_FILES - int(self.type in metadata)
        if (
            count > maximum_headers
            or source.fileobj.tell() > maximum
            or chain > 64
            or self.size < 0
            or self.size > _MAX_ACQUISITION_ARCHIVE_BYTES
            or (self.type in metadata and self.size > 64 * 1024)
            or (self.type not in metadata and not (self.isfile() or self.isdir()))
            or self.issparse()
        ):
            raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
        vars(source).update(_specfact_acquisition_headers=count, _specfact_acquisition_metadata_chain=chain)
        if self.type in {tarfile.XHDTYPE, tarfile.XGLTYPE}:
            position = source.fileobj.tell()
            payload = source.fileobj.read(self.size)
            source.fileobj.seek(position)
            if b"GNU.sparse." in payload:
                raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
        return super()._proc_member(source)


def _acquisition_members(source: tarfile.TarFile) -> list[tuple[PurePosixPath, tarfile.TarInfo]]:
    parsed = []
    total = 0
    for member in source:
        if (
            len(parsed) >= _MAX_ACQUISITION_FILES
            or member.size < 0
            or member.size > _MAX_ACQUISITION_ARCHIVE_BYTES - total
            or member.issym()
            or member.islnk()
            or member.issparse()
            or not (member.isfile() or member.isdir())
            or (member.isdir() and member.size != 0)
        ):
            raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
        total += member.size
        parsed.append((_safe_archive_path(member.name), member))
    if not parsed:
        raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
    return parsed


def _extract_acquisition_archive(archive: Path, destination: Path) -> None:
    try:
        with tarfile.open(archive, "r:*", tarinfo=_AcquisitionTarInfo) as source:
            parsed = _acquisition_members(source)
            roots = {path.parts[0] for path, _member in parsed}
            strip_root = next(iter(roots)) if len(roots) == 1 else None
            total = 0
            seen: set[str] = set()
            destination.mkdir(mode=0o700)
            for original, member in parsed:
                parts = original.parts[1:] if strip_root else original.parts
                if not parts:
                    continue
                relative = PurePosixPath(*parts)
                folded = relative.as_posix().casefold()
                if folded in seen or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                seen.add(folded)
                output = destination.joinpath(*relative.parts)
                if not output.absolute().is_relative_to(destination.absolute()):
                    raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                if member.isdir():
                    output.mkdir(parents=True, exist_ok=True, mode=0o700)
                    continue
                if member.size < 0 or member.size > _MAX_ACQUISITION_ARCHIVE_BYTES - total:
                    raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                total += member.size
                stream = source.extractfile(member)
                if stream is None:
                    raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(output, flags, 0o600)
                written = 0
                try:
                    with os.fdopen(descriptor, "wb", closefd=True) as target:
                        while written < member.size:
                            block = stream.read(min(_COPY_BLOCK_BYTES, member.size - written))
                            if not block:
                                raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                            target.write(block)
                            written += len(block)
                        if stream.read(1):
                            raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                except Exception:
                    output.unlink(missing_ok=True)
                    raise
                mode = stat.S_IMODE(member.mode)
                if mode & 0o022 or mode not in {0o400, 0o500, 0o600, 0o644, 0o700, 0o755}:
                    raise ProjectRuntimeError("project_native_acquisition_archive_invalid")
                output.chmod(mode)
    except ProjectRuntimeError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise ProjectRuntimeError("project_native_acquisition_archive_invalid") from exc


def _download_acquisition_bundle(
    url: str,
    destination: Path,
    *,
    expected_digest: str | None = None,
    expected_size: int | None = None,
    transport: str = "https",
) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ProjectRuntimeError("project_native_acquisition_url_invalid")
    bound = expected_digest is not None or expected_size is not None
    if bound and (
        not isinstance(expected_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", expected_digest) is None
        or type(expected_size) is not int
        or not 0 < expected_size <= _MAX_ACQUISITION_ARCHIVE_BYTES
        or transport not in {"https", "ghcr"}
    ):
        raise ProjectRuntimeError("project_native_acquisition_locator_invalid")
    archive = destination.parent / f".{destination.name}.tar.partial"
    try:
        if transport == "ghcr":
            match = re.fullmatch(r"/v2/(.+)/blobs/(sha256:[0-9a-f]{64})", parsed.path)
            if not bound or parsed.hostname != "ghcr.io" or match is None or match.group(2) != expected_digest:
                raise ProjectRuntimeError("project_native_acquisition_locator_invalid")
            repository = match.group(1)
            response = native_backend._open_registry_blob(
                repository=repository,
                digest=cast(str, expected_digest),
                size=cast(int, expected_size),
                allowlist=(
                    ("ghcr.io", f"/v2/{repository}/blobs/"),
                    ("pkg-containers.githubusercontent.com", "/"),
                ),
                max_redirects=4,
            )
            content_length: str | None = str(expected_size)
        else:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/octet-stream", "User-Agent": "specfact-code-review-native/1"},
            )
            response = urllib.request.build_opener(_RejectRedirects()).open(
                request,
                timeout=_ACQUISITION_TIMEOUT_SECONDS,
            )
            content_length = response.headers.get("Content-Length")
        with response, archive.open("xb") as output:
            if content_length is not None and (
                not content_length.isdecimal()
                or int(content_length) > _MAX_ACQUISITION_ARCHIVE_BYTES
                or (bound and int(content_length) != expected_size)
            ):
                raise ProjectRuntimeError("project_native_acquisition_archive_size_mismatch")
            digest = hashlib.sha256()
            written = 0
            while block := response.read(min(_COPY_BLOCK_BYTES, 64 * 1024)):
                written += len(block)
                if written > _MAX_ACQUISITION_ARCHIVE_BYTES:
                    raise ProjectRuntimeError("project_native_acquisition_archive_too_large")
                output.write(block)
                digest.update(block)
            output.flush()
            os.fsync(output.fileno())
        if bound and (written != expected_size or f"sha256:{digest.hexdigest()}" != expected_digest):
            raise ProjectRuntimeError("project_native_acquisition_archive_digest_mismatch")
        _extract_acquisition_archive(archive, destination)
    except ProjectRuntimeError:
        raise
    except (OSError, urllib.error.URLError, native_backend.NativeRegistryError) as exc:
        raise ProjectRuntimeError("project_native_acquisition_failed") from exc
    finally:
        archive.unlink(missing_ok=True)


def _acquisition_cache() -> Path:
    configured = os.environ.get(
        "SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_CACHE",
        str(Path.home() / ".cache/specfact/code-review/project-acquisitions-v1"),
    )
    root = Path(configured).expanduser().absolute()
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise ProjectRuntimeError("project_native_acquisition_cache_invalid") from exc
    if root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise ProjectRuntimeError("project_native_acquisition_cache_invalid")
    return root


def _read_binding(cache: Path, key: str) -> str | None:
    path = cache / "bindings" / key
    if not path.exists():
        return None
    try:
        metadata = path.lstat()
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise ProjectRuntimeError("project_native_acquisition_binding_invalid") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or re.fullmatch(r"[0-9a-f]{64}", value) is None
    ):
        raise ProjectRuntimeError("project_native_acquisition_binding_invalid")
    return value


def _write_binding(cache: Path, key: str, content: str) -> None:
    bindings = cache / "bindings"
    bindings.mkdir(mode=0o700, exist_ok=True)
    if bindings.is_symlink() or not bindings.is_dir() or bindings.resolve() != bindings.absolute():
        raise ProjectRuntimeError("project_native_acquisition_binding_invalid")
    temporary = bindings / f".{key}.{os.getpid()}.partial"
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            payload = f"{content}\n".encode("ascii")
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise ProjectRuntimeError("project_native_acquisition_binding_invalid")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, bindings / key)
    finally:
        temporary.unlink(missing_ok=True)


def _install_acquisition_bundle(staged: Path, cache: Path, plan: ProjectPlan, runtime: Any) -> Path:
    descriptor = _verify_acquisition_bundle(staged, plan, runtime)
    content = str(descriptor["content_sha256"])
    if re.fullmatch(r"[0-9a-f]{64}", content) is None:
        raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
    destination = cache / content
    if destination.exists():
        _verify_acquisition_bundle(destination, plan, runtime)
    else:
        try:
            os.rename(staged, destination)
        except OSError as exc:
            if not destination.exists():
                raise ProjectRuntimeError("project_native_acquisition_cache_publish_failed") from exc
            _verify_acquisition_bundle(destination, plan, runtime)
    _write_binding(cache, _cache_key(plan, runtime), content)
    return destination


def _resolve_acquisition_bundle(
    plan: ProjectPlan,
    runtime: Any,
    *,
    offline: bool,
    acquisition_url: str | None,
) -> Path:
    cache = _acquisition_cache()
    key = _cache_key(plan, runtime)
    content = _read_binding(cache, key)
    if content is not None:
        selected = cache / content
        _verify_acquisition_bundle(selected, plan, runtime)
        return selected
    explicit = os.environ.get("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE", "").strip()
    if explicit:
        selected = Path(explicit).expanduser().absolute()
        _verify_acquisition_bundle(selected, plan, runtime)
        with tempfile.TemporaryDirectory(prefix=".installing-", dir=cache) as raw:
            staged = Path(raw) / "bundle"
            shutil.copytree(selected, staged, symlinks=True)
            return _install_acquisition_bundle(staged, cache, plan, runtime)
    if offline:
        raise ProjectRuntimeError("project_runtime_offline_cache_miss: run runtime prepare with acquisition first")
    locator = (acquisition_url or os.environ.get(_ACQUISITION_URL_ENV, "")).strip()
    catalog_entry = None
    if not locator:
        try:
            catalog_entry = resolve_project_artifact(plan, environment_id=runtime.environment_id)
        except ValueError as exc:
            raise ProjectRuntimeError(str(exc)) from exc
        locator = catalog_entry.url
    try:
        with tempfile.TemporaryDirectory(prefix=".acquiring-", dir=cache) as raw:
            staged = Path(raw) / "bundle"
            if catalog_entry is None:
                _download_acquisition_bundle(locator, staged)
            else:
                _download_acquisition_bundle(
                    locator,
                    staged,
                    expected_digest=catalog_entry.digest,
                    expected_size=catalog_entry.size,
                    transport=catalog_entry.transport,
                )
            return _install_acquisition_bundle(staged, cache, plan, runtime)
    except ProjectRuntimeError:
        raise
    except OSError as exc:
        raise ProjectRuntimeError("project_native_acquisition_failed") from exc


def _descriptor(bundle: Path, plan: ProjectPlan, environment_id: str) -> dict[str, Any]:
    path = bundle / "descriptor.json"
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _MAX_RESULT_BYTES:
        raise ProjectRuntimeError("project_native_acquisition_descriptor_invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectRuntimeError("project_native_acquisition_descriptor_invalid") from exc
    abi = environment_id.removeprefix("darwin-arm64-")
    expected_manager = {"name": plan.manager, "version": _MANAGER_VERSIONS.get(plan.manager)}
    if (
        not isinstance(value, dict)
        or value.get("schema") != "specfact-macos-project-acquisition-v1"
        or value.get("corpus_identity") != plan.identity
        or value.get("abi") != abi
        or value.get("platform") != "macos-arm64"
        or value.get("manager") != expected_manager
    ):
        raise ProjectRuntimeError("project_native_acquisition_binding_mismatch")
    return cast(dict[str, Any], value)


def _copy_immutable(source: Path, destination: Path) -> None:
    def copy_file(src: str, dst: str) -> str:
        source_path = Path(src)
        metadata = source_path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ProjectRuntimeError("project_native_acquisition_contains_indirection")
        copied = shutil.copyfile(src, dst, follow_symlinks=False)
        Path(dst).chmod(0o500 if metadata.st_mode & 0o111 else 0o400)
        return copied

    shutil.copytree(source, destination, symlinks=False, copy_function=copy_file)
    for root, directories, _files in os.walk(destination, topdown=False):
        current = Path(root)
        for name in directories:
            (current / name).chmod(0o500)
    destination.chmod(0o500)


def _read_result(output: Path) -> dict[str, Any]:
    path = output / "project-preparation.json"
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _MAX_RESULT_BYTES:
        raise ProjectRuntimeError("project_native_preparation_result_missing")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectRuntimeError("project_native_preparation_result_invalid") from exc
    if (
        not isinstance(result, dict)
        or result.get("schema") != _RESULT_SCHEMA
        or result.get("status") not in {"COMPLETE", "INCOMPLETE", "REJECTED"}
        or not isinstance(result.get("evidence"), dict)
    ):
        raise ProjectRuntimeError("project_native_preparation_result_invalid")
    return cast(dict[str, Any], result)


def _execute(plan: ProjectPlan, runtime: Any, bundle: Path, artifact: Path) -> dict[str, Any]:
    lease = getattr(runtime, "native_lease", None)
    if lease is None:
        raise ProjectRuntimeError("project_native_capsule_lease_missing")
    temporary_parent = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="specfact-native-project-", dir=temporary_parent) as raw:
        invocation = Path(raw).resolve()
        invocation.chmod(0o700)
        project = invocation / "project"
        project.mkdir(mode=0o700)
        _copy_immutable(bundle, project / ".specfact-native-project")
        project.chmod(0o500)
        output = invocation / "output"
        output.mkdir(mode=0o700)
        temporary = invocation / "temporary"
        temporary.mkdir(mode=0o700)
        request = native_execution.prepare_native_execution(
            lease=lease,
            plan_id=f"project.{plan.manager}.v1",
            invocation_root=invocation,
            project_snapshot=project,
            output_root=output,
            temporary_root=temporary,
            environment={
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "NO_COLOR": "1",
                "PYTHONHASHSEED": "0",
                "PYTHONUTF8": "1",
                "TZ": "UTC",
            },
            descriptor_grants={"stdin": 0, "stdout": 1, "stderr": 2},
            timeout_ms=900_000,
            budget=native_execution.ResourceBudget(
                address_space_bytes=4 << 30,
                file_size_bytes=512 << 20,
                open_files=512,
                output_bytes=64 << 20,
            ),
        )
        with native_execution.NativeExecutionSession(native_execution.BinaryNativeExecutionTransport(lease)) as session:
            execution = session.wait(session.launch(request), 900_000)
        result = _read_result(output)
        if execution.returncode == 74 and result["status"] == "INCOMPLETE":
            diagnostic = str(
                cast(dict[str, Any], result["evidence"]).get("diagnostic", "unsupported dependency closure")
            )
            raise ProjectRuntimeError(f"project_native_preparation_incomplete:{diagnostic}")
        if execution.returncode != 0 or result["status"] != "COMPLETE":
            raise ProjectRuntimeError(f"project_native_preparation_failed:exit={execution.returncode}")
        site_packages = output / "site-packages"
        if site_packages.is_symlink() or not site_packages.is_dir():
            raise ProjectRuntimeError("project_native_preparation_incomplete:site-packages missing")
        evidence = cast(dict[str, Any], result["evidence"])
        artifact.mkdir(mode=0o700)
        sealed_site_packages = artifact / "site-packages"
        _copy_runtime_tree(site_packages, sealed_site_packages)
        native_extensions = _admit_native_extensions(
            sealed_site_packages,
            capsule_root=Path(runtime.root),
            declared_count=evidence.get("native_extension_count"),
        )
        metadata = _inspect_project_site(runtime, artifact, invocation)
        inventory = {
            **metadata,
            "native_extensions": native_extensions,
            "native_preparation": evidence,
            "pytest_arguments": [],
        }
        (artifact / "inventory.json").write_text(
            json.dumps(inventory, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return inventory


@contextmanager
def _private_preparation(prefix: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix=prefix, dir=Path(tempfile.gettempdir()).resolve()) as raw:
        root = Path(raw).resolve()
        root.chmod(0o700)
        try:
            yield root
        finally:
            for directory, _children, _files in os.walk(root, followlinks=False):
                Path(directory).chmod(0o700)


def _run_pip_phase(runtime: Any, operation: str, inputs: Path, destination: Path) -> None:
    """Launch a fixed domain through the existing owned, traced native broker."""
    lease = getattr(runtime, "native_lease", None)
    if lease is None:
        raise ProjectRuntimeError("project_native_capsule_lease_missing")
    with _private_preparation("specfact-native-pip-") as invocation:
        project = invocation / "project"
        _copy_immutable(inputs, project)
        output, temporary = invocation / "output", invocation / "temporary"
        output.mkdir(mode=0o700)
        temporary.mkdir(mode=0o700)
        try:
            request = native_execution.prepare_native_execution(
                lease=lease,
                plan_id={
                    "acquire": "acquisition.pip-wheels.v1",
                    "install": "project.pip-install.v1",
                    "hook": "project.python-build.v1",
                    "inspect": "project.wheel-inspect.v1",
                    "uv": "acquisition.uv-project.v1",
                }[operation],
                invocation_root=invocation,
                project_snapshot=project,
                output_root=output,
                temporary_root=temporary,
                environment={"LANG": "C.UTF-8", "PYTHONHASHSEED": "0"},
                descriptor_grants={"stdin": 0, "stdout": 1, "stderr": 2},
                timeout_ms=900_000,
                budget=native_execution.ResourceBudget(4 << 30, 512 << 20, 512, 64 << 20),
            )
            with native_execution.NativeExecutionSession(
                native_execution.BinaryNativeExecutionTransport(lease)
            ) as session:
                execution = session.wait(session.launch(request), 900_000)
            if execution.returncode:
                error = output / "preparation-error.json"
                diagnostic = "manager worker failed"
                if error.is_file() and not error.is_symlink() and error.stat().st_size <= _MAX_RESULT_BYTES:
                    try:
                        receipt = json.loads(error.read_text())
                    except (OSError, ValueError):
                        receipt = None
                    if isinstance(receipt, dict) and isinstance(receipt.get("diagnostic"), str):
                        diagnostic = receipt["diagnostic"][:4096]
                raise ProjectRuntimeError(f"project_native_preparation_incomplete:{operation}:{diagnostic}")
            # Broker-owned streams are retained privately, not copied into reusable environments.
            for name in ("managed-stdout.bin", "managed-stderr.bin"):
                (output / name).unlink(missing_ok=True)
            if operation == "uv":
                version = runtime.environment_id.removeprefix("darwin-arm64-cp")
                site = output / f"environment/lib/python{version[0]}.{version[1:]}/site-packages"
                if site.is_symlink() or site.resolve() != site or not site.is_dir():
                    raise ProjectRuntimeError("project_native_uv_environment_invalid")
                destination.mkdir(mode=0o700)
                _copy_runtime_tree(site, destination / "site-packages")
                lock = temporary / "source/uv.lock"
                metadata = lock.lstat()
                if lock.is_symlink() or not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= 16 << 20:
                    raise ProjectRuntimeError("project_native_uv_lock_missing")
                _copy_regular_file(lock, destination / "prepared.lock", _identity(metadata))
            else:
                _copy_runtime_tree(output, destination)
        finally:
            for directory, _directories, _files in os.walk(invocation, followlinks=False):
                Path(directory).chmod(0o700)


def prepare_source_environment(runtime: Any, destination: Path) -> None:
    """Inventory an empty source-only environment using the admitted interpreter."""
    with _private_preparation("specfact-native-source-") as root:
        inputs = root / "inputs"
        (inputs / "wheels").mkdir(parents=True, mode=0o700)
        (inputs / "request.json").write_text("{}\n")
        _run_pip_phase(runtime, "install", inputs, destination)
        path = destination / "environment-inventory.json"
        if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_RESULT_BYTES:
            raise ProjectRuntimeError("project_native_inventory_invalid")
        inventory = json.loads(path.read_text())
        if not isinstance(inventory, dict) or set(inventory) != {
            "installed",
            "environment",
            "member_graphs",
            "analyzer_conflicts",
        }:
            raise ProjectRuntimeError("project_native_inventory_invalid")
        _record_native_inventory(runtime, inventory)
        inventory.update(source_roots=[], pytest_arguments=[], native_extensions=[])
        destination.chmod(0o700)
        (destination / "project-runtime.json").write_text(
            json.dumps(
                {
                    "schema": "native-source-environment-v1",
                    "inventory": inventory,
                }
            )
            + "\n"
        )
        (destination / "project-runtime.json").chmod(0o400)
        destination.chmod(0o500)


def _prepare_project_on_demand(plan: ProjectPlan, runtime: Any, artifact: Path) -> dict[str, Any]:
    from dataclasses import replace

    from specfact_code_review.run import native_project_pip

    if plan.manager == "hatch":
        return _prepare_hatch_on_demand(plan, runtime, artifact)
    if plan.manager == "uv":
        return _prepare_uv_on_demand(plan, runtime, artifact)
    if plan.manager == "poetry":
        return _prepare_poetry_on_demand(plan, runtime, artifact)
    if plan.manager != "pip":
        raise ProjectRuntimeError(f"project_native_managed_launch_required:{plan.manager}")
    verify_inputs(plan)
    with _private_preparation("specfact-pip-preparation-") as root:
        snapshot = root / "snapshot"
        _copy_native_snapshot(plan, snapshot)
        project_wheels = root / "project-wheels"
        built_requirements = _build_project_wheel(plan, runtime, snapshot, root, project_wheels)
        request = native_project_pip.dependency_request(
            replace(plan, root=snapshot), built_requirements=built_requirements
        )
        declarations = root / "declarations"
        declarations.mkdir(mode=0o700)
        (declarations / "request.json").write_text(json.dumps(request) + "\n")
        if project_wheels.exists():
            _copy_immutable(project_wheels, declarations / "wheels")
        acquired = root / "acquired"
        try:
            _run_pip_phase(runtime, "acquire", declarations, acquired)
            if project_wheels.exists():
                (acquired / "wheels").chmod(0o700)
                for wheel in project_wheels.iterdir():
                    target = acquired / "wheels" / wheel.name
                    if target.exists():
                        if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(wheel.read_bytes()).digest():
                            raise ProjectRuntimeError("project_native_root_wheel_collision")
                    else:
                        shutil.copyfile(wheel, target)
            manifest = native_project_pip.wheel_manifest(acquired / "wheels")
            acquired_manifest = json.loads((acquired / "wheel-manifest.json").read_text())
            if any(manifest.get(name) != digest for name, digest in acquired_manifest.items()):
                raise ProjectRuntimeError("project_native_wheel_digest_mismatch")
            installation = root / "installation"
            installation.mkdir(mode=0o700)
            _copy_immutable(acquired / "wheels", installation / "wheels")
            (installation / "request.json").write_text(json.dumps(manifest) + "\n")
            _run_pip_phase(runtime, "install", installation, artifact)
            site = artifact / "site-packages"
            count = sum(path.suffix in {".so", ".dylib"} for path in runtime_native._macho_candidates(site))
            metadata_path = artifact / "environment-inventory.json"
            if (
                not metadata_path.is_file()
                or metadata_path.is_symlink()
                or metadata_path.stat().st_size > _MAX_RESULT_BYTES
            ):
                raise ProjectRuntimeError("project_native_inventory_invalid")
            metadata = json.loads(metadata_path.read_text())
            if not isinstance(metadata, dict) or set(metadata) != {
                "installed",
                "environment",
                "member_graphs",
                "analyzer_conflicts",
            }:
                raise ProjectRuntimeError("project_native_inventory_invalid")
            _record_native_inventory(runtime, metadata)
            artifact.chmod(0o700)
            inventory = {
                **metadata,
                "pytest_arguments": [],
                "source_roots": list(plan.source_roots)
                or _bound_source_roots(snapshot, project_wheels, generated_destination=artifact / "source-overlay"),
                "native_extensions": _admit_native_extensions(
                    site, capsule_root=Path(runtime.root), declared_count=count
                ),
                "native_preparation": {
                    "status": "COMPLETE",
                    "manager": {"name": "pip", "version": native_project_pip.PIP_VERSION},
                    "project_catalog_used": False,
                    "host_manager_used": False,
                    "build_hooks_executed": built_requirements is not None,
                    "wheel_manifest": manifest,
                },
            }
            artifact.chmod(0o700)
            (artifact / "inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
            verify_inputs(plan)
            return inventory
        finally:
            for directory, _directories, _files in os.walk(root, followlinks=False):
                Path(directory).chmod(0o700)


def _record_native_inventory(runtime: Any, inventory: dict[str, Any]) -> dict[str, Any]:
    """Bind fresh target-interpreter metadata to the signed exact native version."""
    from specfact_code_review.run.runtime_interpreter import signed_versions

    try:
        expected = signed_versions().get(getattr(runtime, "environment_id", ""))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectRuntimeError(
            "project_native_preparation_incomplete:python_version:missing signed native metadata"
        ) from exc
    environment = inventory.get("environment")
    actual = environment.get("python_full_version") if isinstance(environment, dict) else None
    if not expected or not isinstance(actual, str) or actual != expected:
        raise ProjectRuntimeError(
            f"project_native_preparation_incomplete:python_version:expected={expected};observed={actual}"
        )
    return inventory


def _inspect_project_site(runtime: Any, artifact: Path, root: Path) -> dict[str, Any]:
    """Read metadata in a fresh sealed process after manager/hook exit."""
    inspection = root / "inventory-inputs"
    inspection.mkdir(mode=0o700)
    _copy_immutable(artifact / "site-packages", inspection / "site-packages")
    (inspection / "request.json").write_text(json.dumps({"schema": "native-site-inventory-v1"}))
    inspected = root / "inventory-output"
    _run_pip_phase(runtime, "inspect", inspection, inspected)
    inventory = _read_preparation_document(inspected / "environment-inventory.json")
    if set(inventory) != {"installed", "environment", "member_graphs", "analyzer_conflicts"}:
        raise ProjectRuntimeError("project_native_inventory_invalid")
    return _record_native_inventory(runtime, inventory)


def _prepare_uv_on_demand(plan: ProjectPlan, runtime: Any, artifact: Path) -> dict[str, Any]:
    from specfact_code_review.run import native_project_uv

    if not (plan.root / "pyproject.toml").is_file():
        raise ProjectRuntimeError("project_native_uv_configuration_missing:provide a uv pyproject.toml")
    verify_inputs(plan)
    with _private_preparation("specfact-uv-preparation-") as root:
        snapshot = root / "snapshot"
        _copy_native_snapshot(plan, snapshot)
        locked = (snapshot / "uv.lock").is_file()
        (snapshot / ".specfact-uv.json").write_text(
            json.dumps(
                {
                    "schema": native_project_uv.SCHEMA,
                    "environment": plan.environment,
                    "groups": list(plan.groups),
                    "extras": list(plan.extras),
                    "locked": locked,
                }
            )
        )
        _run_pip_phase(runtime, "uv", snapshot, artifact)
        if locked and _sha256(snapshot / "uv.lock") != _sha256(artifact / "prepared.lock"):
            raise ProjectRuntimeError("project_native_uv_lock_changed")
        inventory = _inspect_project_site(runtime, artifact, root)
        count = sum(
            path.suffix in {".so", ".dylib"} for path in runtime_native._macho_candidates(artifact / "site-packages")
        )
        inventory.update(
            source_roots=list(plan.source_roots)
            or _bound_source_roots(
                snapshot, artifact / "site-packages", installed=True, generated_destination=artifact / "source-overlay"
            ),
            pytest_arguments=[],
            native_extensions=_admit_native_extensions(
                artifact / "site-packages", capsule_root=Path(runtime.root), declared_count=count
            ),
            native_preparation={
                "status": "COMPLETE",
                "manager": {"name": "uv", "version": native_project_uv.VERSION},
                "project_catalog_used": False,
                "host_manager_used": False,
                "lock_sha256": _sha256(artifact / "prepared.lock"),
                "existing_lock_preserved": locked,
            },
        )
        artifact.chmod(0o700)
        (artifact / "inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
        verify_inputs(plan)
        return inventory


def _materialize_native_source_aliases(snapshot: Path) -> None:
    """Project only verified copied source aliases into an ordinary private tree."""
    if not any(path.is_symlink() for path in snapshot.rglob("*")):
        return
    from specfact_code_review.run.runner import _capture_native_snapshot

    expected = source_identity(snapshot)
    identity = _identity(snapshot.lstat())
    directories: list[str] = []
    entries = _capture_native_snapshot(snapshot, directories=directories, exclude_directory=is_excluded_source)
    with tempfile.TemporaryDirectory(prefix=".materializing-", dir=snapshot.parent) as raw:
        projection = Path(raw) / "snapshot"
        projection.mkdir(mode=0o700)
        for name in sorted(directories, key=lambda value: (len(PurePosixPath(value).parts), value)):
            (projection / name).mkdir(mode=0o700)
        for name, content in entries:
            target = projection / name
            target.write_bytes(content)
            target.chmod(0o500 if (snapshot / name).stat().st_mode & 0o111 else 0o400)
        _runtime_tree(projection)
        if source_identity(snapshot) != expected or _identity(snapshot.lstat()) != identity:
            raise ProjectRuntimeError("project_runtime_source_changed_during_copy")
        original = Path(raw) / "original"
        os.rename(snapshot, original)
        try:
            os.rename(projection, snapshot)
        except BaseException:
            os.rename(original, snapshot)
            raise
        for directory, _children, _files in os.walk(original, followlinks=False):
            Path(directory).chmod(0o700, follow_symlinks=False)
        shutil.rmtree(original)


def _copy_native_snapshot(plan: ProjectPlan, destination: Path) -> None:
    from specfact_code_review.run.runtime_builder import copy_project
    from specfact_code_review.run.runtime_vcs import copy_vcs_context

    copy_project(plan.root, destination, include_vcs=False)
    if source_identity(destination) != plan.source_identity:
        raise ProjectRuntimeError("project_runtime_source_changed_during_copy")
    _materialize_native_source_aliases(destination)
    if plan.vcs:
        copy_vcs_context(
            plan.vcs_repository or plan.root,
            destination,
            plan.vcs["commit"],
            tree=plan.vcs.get("tree"),
            bound_vcs=plan.vcs,
        )


def _copy_native_build_input(snapshot: Path, destination: Path) -> None:
    from specfact_code_review.run.runtime_builder import copy_project

    copy_project(snapshot, destination, include_vcs=False)
    metadata = snapshot / ".git"
    if metadata.exists():
        if metadata.is_symlink() or not metadata.is_dir():
            raise ProjectRuntimeError("project_native_vcs_snapshot_invalid")
        _copy_immutable(metadata, destination / ".git")


def _manager_phase(
    plan: ProjectPlan,
    runtime: Any,
    snapshot: Path,
    dependencies: Path,
    root: Path,
    operation: str,
    *,
    wheels: Path | None = None,
    sources: list[dict[str, Any]] | None = None,
    source_wheels: Path | None = None,
) -> Path:
    from specfact_code_review.run import native_project_hatch, native_project_poetry

    inputs = root / f"{operation}-inputs"
    _copy_native_build_input(snapshot, inputs)
    inputs.chmod(0o700)
    _copy_immutable(dependencies, inputs / ".specfact-build-dependencies")
    request = {
        "schema": native_project_poetry.SCHEMA if plan.manager == "poetry" else native_project_hatch.SCHEMA,
        "groups": list(plan.groups),
        "extras": list(plan.extras),
    }
    if plan.manager == "hatch":
        request["environment"] = plan.environment
    (inputs / f".specfact-{plan.manager}.json").write_text(json.dumps(request))
    (inputs / ".specfact-hook.json").write_text(json.dumps({"operation": operation, "extras": list(plan.extras)}))
    if wheels is not None:
        _copy_immutable(wheels, inputs / "wheelhouse")
    if sources is not None:
        (inputs / ".specfact-poetry-sources.json").write_text(json.dumps(sources))
    if source_wheels is not None:
        _copy_immutable(source_wheels, inputs / ".specfact-poetry-source-wheels")
    result = root / f"{operation}-output"
    _run_pip_phase(runtime, "hook", inputs, result)
    return result


def _merge_local_wheels(collections: list[Path], destination: Path) -> None:
    from specfact_code_review.run.native_project_pip import wheel_manifest

    destination.mkdir(mode=0o700, exist_ok=True)
    destination.chmod(0o700)
    for collection in collections:
        if not collection.is_dir():
            continue
        for name, digest in wheel_manifest(collection).items():
            target = destination / name
            if target.exists():
                if target.is_symlink() or _sha256(target) != digest:
                    raise ProjectRuntimeError("project_native_root_wheel_collision")
            else:
                shutil.copyfile(collection / name, target)
    wheel_manifest(destination)


def _prepare_hatch_on_demand(plan: ProjectPlan, runtime: Any, artifact: Path) -> dict[str, Any]:
    from dataclasses import replace

    from specfact_code_review.run import native_project_hatch, native_project_pip

    verify_inputs(plan)
    with _private_preparation("specfact-hatch-preparation-") as root:
        snapshot = root / "snapshot"
        _copy_native_snapshot(plan, snapshot)
        dependencies = _prepare_build_dependencies(runtime, ["hatch==1.18.0", "uv==0.12.13"], root, "hatch-manager")
        described = _manager_phase(plan, runtime, snapshot, dependencies, root, "hatch.describe")
        description = _read_preparation_document(described / "hook-result.json")
        if (
            set(description) != {"requirements", "extras", "groups", "skip_install", "dev_mode", "locked", "workspace"}
            or any(
                not isinstance(description[key], list)
                or len(description[key]) > 4096
                or any(not isinstance(value, str) for value in description[key])
                for key in ("requirements", "extras", "groups")
            )
            or any(type(description[key]) is not bool for key in ("skip_install", "dev_mode", "locked"))
        ):
            raise ProjectRuntimeError("project_native_hatch_description_invalid")
        workspace = native_project_hatch.validate_workspace(snapshot, description["workspace"])
        project_wheels = root / "project-wheels"
        built = (
            None
            if description["skip_install"]
            else _build_project_wheel(
                replace(plan, extras=tuple(description["extras"])),
                runtime,
                snapshot,
                root,
                project_wheels,
                editable=description["dev_mode"],
            )
        )
        build_roots = [root]
        built_requirements = list(built or ())
        workspace_wheels = []
        for index, member in enumerate(workspace):
            member_root = root / f"workspace-build-{index}"
            member_root.mkdir(mode=0o700)
            member_wheels = member_root / "wheels"
            built_requirements.extend(
                _build_project_wheel(
                    replace(plan, root=snapshot / member["path"], extras=tuple(member["extras"])),
                    runtime,
                    snapshot / member["path"],
                    member_root,
                    member_wheels,
                    editable=True,
                    workspace_snapshot=snapshot,
                )
                or ()
            )
            build_roots.append(member_root)
            workspace_wheels.append(member_wheels)
        local_wheels = root / "local-wheels"
        _merge_local_wheels([project_wheels, *workspace_wheels], local_wheels)
        request = native_project_pip.dependency_request(
            replace(plan, root=snapshot, manager="pip", groups=(), extras=()),
            built_requirements=[*description["requirements"], *built_requirements],
        )
        declarations = root / "declarations"
        declarations.mkdir(mode=0o700)
        (declarations / "request.json").write_text(json.dumps(request))
        _copy_immutable(local_wheels, declarations / "wheels")
        acquired = root / "acquired"
        _run_pip_phase(runtime, "acquire", declarations, acquired)
        acquired.chmod(0o700)
        wheelhouse = acquired / "wheels"
        wheelhouse.chmod(0o700)
        _merge_local_wheels(
            [
                local_wheels,
                *(
                    build_root / name / "wheels"
                    for build_root in build_roots
                    for name in (
                        "build-acquired",
                        "build-extra-acquired",
                        "build-editable-acquired",
                    )
                ),
            ],
            wheelhouse,
        )
        manifest = native_project_pip.wheel_manifest(wheelhouse)
        expected = _read_preparation_document(acquired / "wheel-manifest.json")
        if any(manifest.get(name) != digest for name, digest in expected.items()):
            raise ProjectRuntimeError("project_native_wheel_digest_mismatch")
        installed = _manager_phase(plan, runtime, snapshot, dependencies, root, "hatch.install", wheels=wheelhouse)
        _copy_runtime_tree(installed, artifact)
        # Hooks can replace their own Python globals or output. Read import
        # metadata in a fresh sealed worker that never imported Hatch/project code.
        inventory = _inspect_project_site(runtime, artifact, root)
        count = sum(
            path.suffix in {".so", ".dylib"} for path in runtime_native._macho_candidates(artifact / "site-packages")
        )
        artifact.chmod(0o700)
        source_roots = list(plan.source_roots) or _bound_source_roots(
            snapshot, project_wheels, generated_destination=artifact / "source-overlay"
        )
        for member_wheels in workspace_wheels:
            source_roots.extend(
                _bound_source_roots(snapshot, member_wheels, generated_destination=artifact / "source-overlay")
            )
        inventory.update(
            source_roots=list(dict.fromkeys(source_roots)),
            pytest_arguments=[],
            native_extensions=_admit_native_extensions(
                artifact / "site-packages", capsule_root=Path(runtime.root), declared_count=count
            ),
            native_preparation={
                "status": "COMPLETE",
                "manager": {"name": "hatch", "version": "1.18.0"},
                "project_catalog_used": False,
                "host_manager_used": False,
                "wheel_manifest": manifest,
                "build_hooks_executed": built is not None or bool(workspace),
                "workspace": workspace,
            },
        )
        artifact.chmod(0o700)
        (artifact / "inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
        verify_inputs(plan)
        return inventory


def _validated_poetry_sources(snapshot: Path, values: Any) -> list[dict[str, str]]:
    import tomllib

    from specfact_code_review.run.native_project_source import MAX_SOURCES, validate_declaration

    if not isinstance(values, list) or len(values) > MAX_SOURCES:
        raise ProjectRuntimeError("project_native_source_request_invalid")
    if not values:
        return []
    declarations = [validate_declaration(value) for value in values]
    lock = tomllib.loads((snapshot / "poetry.lock").read_text())
    expected = []
    for package in lock.get("package", []):
        source = package.get("source", {})
        if source.get("type") == "git":
            expected.append(
                {
                    "schema": "native-locked-git-v1",
                    "name": package["name"],
                    "version": package["version"],
                    "url": source.get("url"),
                    "reference": source.get("reference"),
                    "commit": source.get("resolved_reference"),
                    "subdirectory": source.get("subdirectory", ""),
                }
            )
    if any(value not in expected for value in declarations) or len({value["name"] for value in declarations}) != len(
        declarations
    ):
        raise ProjectRuntimeError("project_native_source_lock_mismatch")
    return declarations


def _prepare_poetry_sources(
    plan: ProjectPlan, runtime: Any, declarations: list[dict[str, str]], root: Path
) -> tuple[Path, list[dict[str, Any]]]:
    from dataclasses import replace

    from specfact_code_review.run import native_project_pip, native_project_source

    wheels = root / "source-wheels"
    wheels.mkdir(mode=0o700)
    bindings = []
    for index, declaration in enumerate(declarations):
        private = root / f"source-{index}"
        private.mkdir(mode=0o700)
        inputs = private / "declarations"
        inputs.mkdir(mode=0o700)
        (inputs / "request.json").write_text(
            json.dumps({"schema": native_project_source.REQUEST_SCHEMA, "declaration": declaration})
        )
        acquired = private / "acquired"
        _run_pip_phase(runtime, "acquire", inputs, acquired)
        receipt = native_project_source.verify_acquired(acquired, declaration)
        source = acquired / "source" / declaration["subdirectory"]
        built = private / "built-wheels"
        _build_project_wheel(
            replace(plan, root=source, manager="pip", extras=(), groups=()), runtime, source, private, built
        )
        manifest = native_project_pip.wheel_manifest(built)
        if len(manifest) != 1:
            raise ProjectRuntimeError("project_native_source_wheel_invalid:require one built wheel")
        wheel = built / next(iter(manifest))
        bindings.append(native_project_source.bind_wheel(wheel, declaration, receipt))
        shutil.copyfile(wheel, wheels / wheel.name)
    return wheels, bindings


def _admit_poetry_resolution(acquired: Path, request: dict[str, Any]) -> Path:
    import tomllib

    from specfact_code_review.run.native_project_poetry import VERSION

    lock = acquired / "poetry.lock"
    receipt = _read_preparation_document(acquired / "resolution.json")
    if (
        lock.is_symlink()
        or not lock.is_file()
        or not 0 < lock.stat().st_size <= 16 << 20
        or set(receipt) != {"manager", "content_hash", "lock_sha256"}
        or receipt["manager"] != {"name": "poetry", "version": VERSION}
        or receipt["content_hash"] != request["content_hash"]
        or receipt["lock_sha256"] != _sha256(lock)
    ):
        raise ProjectRuntimeError("project_native_poetry_resolution_binding_mismatch")
    try:
        content_hash = tomllib.loads(lock.read_text()).get("metadata", {}).get("content-hash")
    except (ValueError, UnicodeError) as exc:
        raise ProjectRuntimeError("project_native_poetry_resolution_binding_mismatch") from exc
    if content_hash != request["content_hash"]:
        raise ProjectRuntimeError("project_native_poetry_resolution_binding_mismatch")
    return lock


def _resolve_poetry_lock(
    runtime: Any, snapshot: Path, dependencies: Path, root: Path, description: dict[str, Any]
) -> None:
    from specfact_code_review.run.native_project_poetry import VERSION, validate_resolution_request

    if (snapshot / "poetry.lock").exists() or (snapshot / "poetry.lock").is_symlink():
        raise ProjectRuntimeError("project_native_poetry_resolution_existing_lock_rejected")
    if (
        description.get("manager") != {"name": "poetry", "version": VERSION}
        or description.get("lock_preserved") is not False
    ):
        raise ProjectRuntimeError("project_native_poetry_description_invalid")
    request = validate_resolution_request(description.get("resolution"))
    inputs = root / "resolution-inputs"
    inputs.mkdir(mode=0o700)
    (inputs / "request.json").write_text(json.dumps(request))
    _copy_immutable(dependencies, inputs / ".specfact-build-dependencies")
    acquired = root / "resolution-output"
    _run_pip_phase(runtime, "acquire", inputs, acquired)
    lock = _admit_poetry_resolution(acquired, request)
    snapshot.chmod(0o700)
    shutil.copyfile(lock, snapshot / "poetry.lock")


def _prepare_poetry_on_demand(plan: ProjectPlan, runtime: Any, artifact: Path) -> dict[str, Any]:
    from dataclasses import replace

    from specfact_code_review.run import native_project_pip, native_project_poetry

    verify_inputs(plan)
    with _private_preparation("specfact-poetry-preparation-") as root:
        snapshot = root / "snapshot"
        _copy_native_snapshot(plan, snapshot)
        dependencies = _prepare_build_dependencies(
            runtime, [f"poetry=={native_project_poetry.VERSION}"], root, "poetry-manager"
        )
        described = _manager_phase(plan, runtime, snapshot, dependencies, root, "poetry.describe")
        description = _read_preparation_document(described / "hook-result.json")
        generated_lock = description.get("locked") is False
        if generated_lock:
            _resolve_poetry_lock(runtime, snapshot, dependencies, root, description)
            validated_root = root / "resolved"
            validated_root.mkdir(mode=0o700)
            described = _manager_phase(plan, runtime, snapshot, dependencies, validated_root, "poetry.describe")
            description = _read_preparation_document(described / "hook-result.json")
        if (
            description.get("manager") != {"name": "poetry", "version": native_project_poetry.VERSION}
            or description.get("locked") is not True
            or description.get("lock_preserved") is not True
            or type(description.get("package_mode")) is not bool
            or any(
                not isinstance(description.get(key), list)
                or len(description[key]) > 4096
                or any(not isinstance(value, str) for value in description[key])
                for key in ("requirements", "groups", "extras")
            )
        ):
            raise ProjectRuntimeError("project_native_poetry_description_invalid")
        sources = _validated_poetry_sources(snapshot, description.get("sources", []))
        source_wheels, source_bindings = _prepare_poetry_sources(plan, runtime, sources, root)
        project_wheels = root / "project-wheels"
        built = (
            _build_project_wheel(plan, runtime, snapshot, root, project_wheels, editable=True, sources=sources)
            if description["package_mode"]
            else None
        )
        declarations = root / "declarations"
        declarations.mkdir(mode=0o700)
        request = native_project_pip.dependency_request(
            replace(plan, root=snapshot, manager="pip", groups=(), extras=()),
            built_requirements=description["requirements"],
        )
        (declarations / "request.json").write_text(json.dumps(request))
        acquired = root / "acquired"
        _run_pip_phase(runtime, "acquire", declarations, acquired)
        wheelhouse = acquired / "wheels"
        wheelhouse.chmod(0o700)
        expected = _read_preparation_document(acquired / "wheel-manifest.json")
        manifest = native_project_pip.wheel_manifest(wheelhouse)
        if manifest != expected:
            raise ProjectRuntimeError("project_native_wheel_digest_mismatch")
        for collection in (
            root / "build-acquired/wheels",
            root / "build-extra-acquired/wheels",
            root / "build-editable-acquired/wheels",
        ):
            if collection.is_dir():
                for wheel in collection.iterdir():
                    destination = wheelhouse / wheel.name
                    if destination.exists() and _sha256(destination) != _sha256(wheel):
                        raise ProjectRuntimeError("project_native_root_wheel_collision")
                    if not destination.exists():
                        shutil.copyfile(wheel, destination)
        manifest = native_project_pip.wheel_manifest(wheelhouse)
        installed = _manager_phase(
            plan,
            runtime,
            snapshot,
            dependencies,
            root,
            "poetry.install",
            wheels=wheelhouse,
            sources=source_bindings,
            source_wheels=source_wheels,
        )
        _copy_runtime_tree(installed, artifact)
        inventory = _inspect_project_site(runtime, artifact, root)
        count = sum(
            path.suffix in {".so", ".dylib"} for path in runtime_native._macho_candidates(artifact / "site-packages")
        )
        artifact.chmod(0o700)
        inventory.update(
            source_roots=list(plan.source_roots)
            or _bound_source_roots(snapshot, project_wheels, generated_destination=artifact / "source-overlay"),
            pytest_arguments=[],
            native_extensions=_admit_native_extensions(
                artifact / "site-packages", capsule_root=Path(runtime.root), declared_count=count
            ),
            native_preparation={
                "status": "COMPLETE",
                "manager": {"name": "poetry", "version": native_project_poetry.VERSION},
                "project_catalog_used": False,
                "host_manager_used": False,
                "wheel_manifest": manifest,
                "existing_lock_preserved": not generated_lock,
                "generated_preparation_lock": generated_lock,
                "source_bindings": source_bindings,
                "hook_provenance": "local_build",
                "production_eligible": False,
                "lock_sha256": _sha256(snapshot / "poetry.lock"),
                "build_hooks_executed": built is not None,
            },
        )
        artifact.chmod(0o700)
        if generated_lock:
            shutil.copyfile(snapshot / "poetry.lock", artifact / "preparation.lock")
        (artifact / "inventory.json").write_text(json.dumps(inventory, sort_keys=True) + "\n")
        verify_inputs(plan)
        return inventory


def _prepare_build_dependencies(runtime: Any, requirements: list[str], root: Path, name: str) -> Path:
    from specfact_code_review.run import native_project_pip

    inputs = root / f"{name}-inputs"
    inputs.mkdir(mode=0o700)
    (inputs / "request.json").write_text(
        json.dumps({"schema": native_project_pip.SCHEMA, "requirements": requirements, "constraints": []})
    )
    acquired = root / f"{name}-acquired"
    _run_pip_phase(runtime, "acquire", inputs, acquired)
    installation = root / f"{name}-installation"
    installation.mkdir(mode=0o700)
    _copy_immutable(acquired / "wheels", installation / "wheels")
    (installation / "request.json").write_text(json.dumps(native_project_pip.wheel_manifest(acquired / "wheels")))
    prepared = root / f"{name}-prepared"
    _run_pip_phase(runtime, "install", installation, prepared)
    return prepared


def _build_project_wheel(
    plan: ProjectPlan,
    runtime: Any,
    snapshot: Path,
    root: Path,
    wheels: Path,
    *,
    editable: bool = False,
    sources: list[dict[str, str]] | None = None,
    workspace_snapshot: Path | None = None,
) -> list[str] | None:
    from specfact_code_review.run import native_project_hooks, native_project_pip

    if not any((snapshot / name).exists() for name in ("pyproject.toml", "setup.py", "setup.cfg")):
        return None
    configuration = native_project_hooks.build_configuration(snapshot)
    declared = list(configuration["requires"])
    dependencies = _prepare_build_dependencies(runtime, declared, root, "build")
    build_requirements = list(declared)
    operations = ("requirements", "editable-requirements", "wheel") if editable else ("requirements", "wheel")
    source = workspace_snapshot or snapshot
    subdirectory = snapshot.relative_to(source).as_posix() if workspace_snapshot else ""
    for operation in operations:
        inputs = root / f"hook-{operation}-inputs"
        _copy_native_build_input(source, inputs)
        inputs.chmod(0o700)
        _copy_immutable(dependencies, inputs / ".specfact-build-dependencies")
        hook_request: dict[str, Any] = {"operation": operation, "extras": list(plan.extras)}
        if subdirectory:
            hook_request["project_subdirectory"] = subdirectory
        (inputs / ".specfact-hook.json").write_text(json.dumps(hook_request))
        result = root / f"hook-{operation}-output"
        _run_pip_phase(runtime, "hook", inputs, result)
        path = result / "hook-result.json"
        response = _read_preparation_document(path)
        if operation in {"requirements", "editable-requirements"}:
            additional = response.get("requirements")
            if (
                not isinstance(additional, list)
                or len(additional) > 4096
                or any(not isinstance(value, str) for value in additional)
            ):
                raise ProjectRuntimeError("project_native_build_requirements_invalid")
            for value in additional:
                native_project_pip.validate_requirement(value)
            if additional:
                build_requirements = list(dict.fromkeys([*build_requirements, *additional]))
                dependencies = _prepare_build_dependencies(
                    runtime,
                    build_requirements,
                    root,
                    "build-editable" if operation == "editable-requirements" else "build-extra",
                )
        else:
            if len(native_project_pip.wheel_manifest(result / "wheels")) != 1:
                raise ProjectRuntimeError("project_native_build_wheel_invalid")
            _copy_runtime_tree(result / "wheels", wheels)
    # Hook code may replace any function in its own process. Inspect the wheel in
    # a fresh sealed process with no backend or project modules imported.
    inspection = root / "inspection-inputs"
    inspection.mkdir(mode=0o700)
    _copy_immutable(wheels, inspection / "wheels")
    inspection_request: dict[str, Any] = {"extras": list(plan.extras)}
    if sources:
        inspection_request["sources"] = sources
    (inspection / "request.json").write_text(json.dumps(inspection_request))
    inspected = root / "inspection-output"
    _run_pip_phase(runtime, "inspect", inspection, inspected)
    response = _read_preparation_document(inspected / "wheel-requirements.json")
    requirements = response.get("requirements")
    if (
        not isinstance(requirements, list)
        or len(requirements) > 4096
        or any(not isinstance(value, str) for value in requirements)
    ):
        raise ProjectRuntimeError("project_native_build_requirements_invalid")
    return [native_project_pip.validate_requirement(value) for value in requirements]


def _read_preparation_document(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _MAX_RESULT_BYTES:
        raise ProjectRuntimeError("project_native_build_result_invalid")
    document = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ProjectRuntimeError("project_native_build_result_invalid")
    return document


def _source_suffix_index(project: Path) -> dict[tuple[str, ...], list[tuple[PurePosixPath, int]]]:
    candidates: dict[tuple[str, ...], list[tuple[PurePosixPath, int]]] = {}
    index_entries = 0
    for relative, (kind, identity) in _runtime_tree(project, exclude_vcs=True).items():
        path = PurePosixPath(relative)
        if kind != "file" or path.suffix not in {".py", ".pyi"}:
            continue
        for offset in range(len(path.parts)):
            index_entries += 1
            if index_entries > _MAX_RUNTIME_FILES:
                raise ProjectRuntimeError("project_native_source_root_bounds_exceeded:provide explicit source_roots")
            candidates.setdefault(path.parts[offset:], []).append((path, identity[4]))
    return candidates


def _matching_source_roots(
    project: Path, path: PurePosixPath, payload: bytes, candidates: list[tuple[PurePosixPath, int]]
) -> list[tuple[str, ...]]:
    return [
        candidate.parts[: -len(path.parts)]
        for candidate, size in candidates
        if size == len(payload) and (project / candidate).read_bytes() == payload
    ]


def _generated_source_files(
    packages: dict[str, set[tuple[str, ...]]],
    missing: list[tuple[PurePosixPath, bytes]],
    *,
    installed: bool,
    owners: dict[str, str] | None = None,
    owned_packages: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]] | None = None,
) -> list[tuple[PurePosixPath, bytes]] | None:
    generated: list[tuple[PurePosixPath, bytes]] = []
    lookups = 0
    for path, payload in missing:
        owner = owners.get(path.as_posix(), "") if owners is not None else path.parts[0]
        roots = packages.get(owner, set()) if owned_packages is None else set()
        if owned_packages is not None:
            for length in range(1, len(path.parts)):
                lookups += 1
                if lookups > _MAX_RUNTIME_FILES:
                    raise ProjectRuntimeError(
                        "project_native_source_root_bounds_exceeded:provide explicit source_roots"
                    )
                roots.update(owned_packages.get((owner, path.parts[:length]), set()))
        if owned_packages is not None and path.name in {"__init__.py", "__init__.pyi"}:
            roots.update(owned_packages.get((owner, path.parts), set()))
        if not roots and installed:
            continue
        if len(roots) != 1:
            return None
        generated.append((PurePosixPath(*next(iter(roots))) / path, payload))
    return generated


def _write_generated_source_files(destination: Path, generated: list[tuple[PurePosixPath, bytes]]) -> None:
    for path, payload in generated:
        target = destination / path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
        target.chmod(0o400)


def _distinct_source_roots(packages: dict[str, set[tuple[str, ...]]]) -> list[str]:
    return sorted({PurePosixPath(*root).as_posix() for roots in packages.values() for root in roots if root})


def _bound_source_roots(
    project: Path,
    wheels: Path,
    *,
    installed: bool = False,
    generated_destination: Path | None = None,
) -> list[str]:
    """Infer byte-bound imports while preserving missing built package modules."""
    if not wheels.is_dir():
        return []
    candidates = _source_suffix_index(project)
    owners = _installed_python_owners(wheels) if installed and generated_destination is not None else None
    packages: dict[str, set[tuple[str, ...]]] = {}
    source_packages: set[str] = set()
    owned_packages: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]] | None = {} if owners is not None else None
    missing: list[tuple[PurePosixPath, bytes]] = []
    comparisons = 0
    files = _installed_python_files(wheels) if installed else _wheel_python_files(wheels)
    for path, payload in files:
        represented = candidates.get(path.parts, [])
        if not represented:
            missing.append((path, payload))
            continue
        comparisons += len(represented)
        if comparisons > _MAX_RUNTIME_FILES:
            raise ProjectRuntimeError("project_native_source_root_bounds_exceeded:provide explicit source_roots")
        matches = _matching_source_roots(project, path, payload, represented)
        if len(matches) != 1:
            return []
        owner = owners.get(path.as_posix()) if owners is not None else path.parts[0]
        if owner is None:
            return []
        packages.setdefault(owner, set()).add(matches[0])
        source_packages.add(path.parts[0])
        if owned_packages is not None:
            owned_packages.setdefault((owner, path.parts[:-1]), set()).add(matches[0])
            for length in range(1, len(path.parts) - 1):
                owned_packages.setdefault((owner, (*path.parts[:length], "__init__.py")), set()).add(matches[0])
                owned_packages.setdefault((owner, (*path.parts[:length], "__init__.pyi")), set()).add(matches[0])
            if len(owned_packages) > _MAX_RUNTIME_FILES:
                raise ProjectRuntimeError("project_native_source_root_bounds_exceeded:provide explicit source_roots")
    if owners is not None and any(
        path.parts[0] in source_packages and path.as_posix() not in owners for path, _payload in missing
    ):
        return []
    generated = _generated_source_files(
        packages, missing, installed=installed, owners=owners, owned_packages=owned_packages
    )
    if generated is None or (generated and generated_destination is None):
        return []
    if generated_destination is not None:
        _write_generated_source_files(generated_destination, generated)
    return _distinct_source_roots(packages)


def _installed_python_owners(site: Path) -> dict[str, str]:
    """Bind overlay candidates to unique hashed installation RECORD owners."""
    from specfact_code_review.run.installed_coverage import _record_row, _verified_record

    owners: dict[str, str] = {}
    rows = 0
    try:
        for relative, (kind, identity) in _runtime_tree(site).items():
            path = PurePosixPath(relative)
            if (
                kind != "file"
                or len(path.parts) != 2
                or not path.parts[0].endswith(".dist-info")
                or path.name != "RECORD"
            ):
                continue
            if identity[4] > _MAX_RESULT_BYTES:
                raise ValueError("installation RECORD exceeds bounds")
            files: dict[str, str] = {}
            for row in csv.reader((site / relative).read_text(encoding="utf-8").splitlines()):
                rows += 1
                if rows > _MAX_RUNTIME_FILES:
                    raise ValueError("installation RECORD rows exceed bounds")
                if len(row) == 3 and (PurePosixPath(row[0]).is_absolute() or ".." in PurePosixPath(row[0]).parts):
                    # RECORD legitimately lists launch scripts outside site-packages.
                    normalized = Path(os.path.abspath(site / row[0]))
                    try:
                        relative_file = normalized.relative_to(Path(os.path.abspath(site)))
                    except ValueError:
                        continue
                    row = [relative_file.as_posix(), *row[1:]]
                _record_row(row, files, python_suffixes=(".py", ".pyi"))
            for name, digest in files.items():
                if name in owners or not _verified_record(site / name, digest, site):
                    raise ValueError("installation ownership is ambiguous or changed")
                owners[name] = path.parts[0]
    except (OSError, ValueError, csv.Error) as exc:
        raise ProjectRuntimeError("project_native_source_ownership_invalid") from exc
    return owners


def _installed_python_files(site: Path) -> Iterator[tuple[PurePosixPath, bytes]]:
    for relative, (kind, _identity_value) in _runtime_tree(site).items():
        path = PurePosixPath(relative)
        if (
            kind == "file"
            and path.suffix in {".py", ".pyi"}
            and not any(part.endswith(".dist-info") for part in path.parts)
        ):
            yield path, (site / path).read_bytes()


def _wheel_python_files(wheels: Path) -> Iterator[tuple[PurePosixPath, bytes]]:
    count, total = 0, 0
    for wheel in wheels.iterdir():
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                count += 1
                total += member.file_size
                if count > _MAX_RUNTIME_FILES or total > _MAX_RUNTIME_BYTES:
                    raise ProjectRuntimeError("project_native_build_wheel_bounds_exceeded")
                path = PurePosixPath(member.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise ProjectRuntimeError("project_native_build_wheel_invalid")
                if path.suffix not in {".py", ".pyi"} or any(
                    part.endswith((".data", ".dist-info")) for part in path.parts
                ):
                    continue
                yield path, archive.read(member)


def prepare_native_project_runtime(
    plan: ProjectPlan,
    *,
    runtime: Any,
    cache_root: Path | None = None,
    offline: bool = False,
    acquisition_url: str | None = None,
) -> PreparedRuntime:
    """Prepare actual project inputs; explicit historical bundles remain importable."""
    if getattr(runtime, "backend", "") != "darwin-arm64":
        raise ProjectRuntimeError("project_native_backend_required")
    if runtime.environment_id not in {"darwin-arm64-cp311", "darwin-arm64-cp312", "darwin-arm64-cp313"}:
        raise ProjectRuntimeError("project_native_environment_unsupported")
    cache = cache_root or Path.home() / ".cache/specfact/code-review/project-runtimes-v2"
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    if cache.is_symlink() or not cache.is_dir():
        raise ProjectRuntimeError("project_runtime_cache_symlink")
    destination = cache / _cache_key(plan, runtime)
    descriptor_path = destination / "project-runtime.json"
    if destination.exists():
        prepared = load_runtime(
            descriptor_path,
            plan=plan,
            environment_id=runtime.environment_id,
            worker_identity=runtime.identity,
        )
        _record_native_inventory(runtime, prepared.descriptor.get("inventory", {}))
        return prepared
    explicit_bundle = (
        acquisition_url
        or os.environ.get(_ACQUISITION_URL_ENV)
        or os.environ.get("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE")
    )
    legacy_binding = _read_binding(_acquisition_cache(), _cache_key(plan, runtime))
    if offline and not explicit_bundle and legacy_binding is None:
        raise ProjectRuntimeError("project_native_offline_cache_miss:prepare this project once online")
    bundle = (
        _resolve_acquisition_bundle(plan, runtime, offline=offline, acquisition_url=acquisition_url)
        if explicit_bundle or legacy_binding
        else None
    )
    with tempfile.TemporaryDirectory(prefix=".preparing-", dir=cache) as raw:
        artifact = Path(raw) / "artifact"
        inventory = (
            _execute(plan, runtime, bundle, artifact)
            if bundle is not None
            else _prepare_project_on_demand(plan, runtime, artifact)
        )
        _record_native_inventory(runtime, inventory)
        validate_build_artifact(artifact)
        seal_runtime(
            artifact,
            plan=plan,
            environment_id=runtime.environment_id,
            worker_identity=runtime.identity,
            inventory=inventory,
        )
        try:
            os.rename(artifact, destination)
        except OSError:
            if not destination.exists():
                raise
        prepared = load_runtime(
            descriptor_path,
            plan=plan,
            environment_id=runtime.environment_id,
            worker_identity=runtime.identity,
        )
        _record_native_inventory(runtime, prepared.descriptor.get("inventory", {}))
        return prepared
