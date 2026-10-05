"""Trusted project acquisition and authenticated offline preparation inputs.

This maintainer harness validates already fetched bytes. Network clients and
credentials stay outside this module, and no project-controlled code executes
while a bundle is created or verified.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from packaging.utils import canonicalize_name, parse_sdist_filename, parse_wheel_filename


SCHEMA = "specfact-macos-project-acquisition-v1"
ABIS = {"3.11": "cp311", "3.12": "cp312", "3.13": "cp313"}
MANAGER_VERSIONS = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
TRUSTED_ARTIFACT_HOSTS = frozenset({"files.pythonhosted.org", "github.com"})
MAX_SOURCE_FILES = 100_000
MAX_SOURCE_BYTES = 512 * 1024 * 1024
MAX_ARTIFACTS = 4_096
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_BUNDLE_BYTES = 1 << 30
Signer = Callable[[bytes], Mapping[str, str]]
Verifier = Callable[[bytes, dict[str, str]], bool]
SourceVerifier = Callable[[Mapping[str, Any], str, str], Mapping[str, Any]]


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _check_bundle_size(root: Path) -> None:
    total = 0
    for path in root.rglob("*"):
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise _fail("bundle_file_invalid")
        if metadata.st_size > MAX_BUNDLE_BYTES - total:
            raise _fail("bundle_bytes_exceeded")
        total += metadata.st_size


def _fail(reason: str) -> ValueError:
    return ValueError(f"acquisition_{reason}")


def build_acquisition_request(entry: Mapping[str, Any], abi: str) -> dict[str, Any]:
    """Create the only network-capable request from trusted corpus metadata."""
    manager = entry.get("manager")
    url, commit = entry.get("url"), entry.get("commit")
    if manager not in MANAGER_VERSIONS:
        raise _fail("manager_not_admitted")
    if abi not in ABIS:
        raise _fail("abi_not_admitted")
    if not isinstance(url, str) or not re.fullmatch(r"https://github\.com/[^/]+/[^/]+\.git", url):
        raise _fail("source_url_not_admitted")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise _fail("source_commit_invalid")
    name = entry.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
        raise _fail("project_invalid")
    groups, environment = entry.get("groups"), entry.get("environment")
    if (
        not isinstance(groups, list)
        or any(
            not isinstance(group, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", group)
            for group in groups
        )
        or not isinstance(environment, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", environment)
    ):
        raise _fail("manager_selection_invalid")
    corpus_identity = hashlib.sha256(_canonical_json(dict(entry))).hexdigest()
    return {
        "schema": "specfact-macos-project-acquisition-request-v1",
        "project": name,
        "corpus_identity": corpus_identity,
        "source": {
            "url": url,
            "commit": commit,
            "archive_url": f"{url.removesuffix('.git')}/archive/{commit}.tar.gz",
        },
        "manager": {"name": manager, "version": MANAGER_VERSIONS[manager]},
        "selection": {"groups": groups, "environment": environment},
        "abi": ABIS[abi],
        "platform": "macos-arm64",
        "network": "trusted-acquisition-only",
        "execute_project_code": False,
    }


def _safe_archive_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or name.startswith("/") or "\\" in name or "\0" in name or ".." in path.parts:
        raise _fail("source_archive_path_invalid")
    return path


def _extract_source(archive: Path, destination: Path) -> dict[str, dict[str, Any]]:
    destination.mkdir(mode=0o700)
    try:
        with tarfile.open(archive, "r:*") as bundle:
            members = bundle.getmembers()
            if not members or len(members) > MAX_SOURCE_FILES:
                raise _fail("source_archive_file_count")
            roots = {_safe_archive_name(member.name).parts[0] for member in members}
            strip_root = next(iter(roots)) if len(roots) == 1 else None
            inventory: dict[str, dict[str, Any]] = {}
            total = 0
            for member in members:
                original = _safe_archive_name(member.name)
                parts = original.parts[1:] if strip_root else original.parts
                if not parts:
                    continue
                relative = PurePosixPath(*parts)
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise _fail("source_archive_special_file")
                output = destination.joinpath(*relative.parts)
                if not output.resolve().is_relative_to(destination.resolve()):
                    raise _fail("source_archive_escape")
                if member.isdir():
                    output.mkdir(parents=True, exist_ok=True)
                    continue
                if member.size < 0 or member.size > MAX_SOURCE_BYTES - total:
                    raise _fail("source_archive_too_large")
                total += member.size
                source = bundle.extractfile(member)
                if source is None:
                    raise _fail("source_archive_unreadable")
                output.parent.mkdir(parents=True, exist_ok=True)
                mode = 0o755 if member.mode & 0o111 else 0o644
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                digest = hashlib.sha256()
                written = 0
                descriptor = os.open(output, flags, mode)
                try:
                    os.fchmod(descriptor, mode)
                    with os.fdopen(descriptor, "wb", closefd=True) as stream:
                        while written < member.size:
                            block = source.read(min(1024 * 1024, member.size - written))
                            if not block:
                                raise _fail("source_archive_size_mismatch")
                            stream.write(block)
                            digest.update(block)
                            written += len(block)
                        if source.read(1) != b"":
                            raise _fail("source_archive_size_mismatch")
                except Exception:
                    output.unlink(missing_ok=True)
                    raise
                inventory[relative.as_posix()] = {
                    "sha256": digest.hexdigest(),
                    "size": written,
                    "mode": mode,
                }
    except (OSError, tarfile.TarError) as error:
        raise _fail("source_archive_invalid") from error
    if not inventory:
        raise _fail("source_archive_empty")
    return inventory


def _artifact_record(artifact: Mapping[str, Any], abi: str) -> tuple[dict[str, Any], Path]:
    required = {"package", "version", "filename", "url", "path", "sha256"}
    if set(artifact) != required:
        raise _fail("artifact_fields_invalid")
    filename, package, version = artifact["filename"], artifact["package"], artifact["version"]
    if not all(isinstance(value, str) and value for value in (filename, package, version)):
        raise _fail("artifact_identity_invalid")
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise _fail("artifact_filename_invalid")
    url = artifact["url"]
    if not isinstance(url, str):
        raise _fail("artifact_url_invalid")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in TRUSTED_ARTIFACT_HOSTS or Path(parsed.path).name != filename:
        raise _fail("artifact_url_not_admitted")
    path = artifact["path"]
    if not isinstance(path, Path) or path.is_symlink() or not path.is_file() or path.name != filename:
        raise _fail("artifact_path_invalid")
    expected_hash = artifact["sha256"]
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise _fail("artifact_hash_invalid")
    actual_hash = _sha256(path)
    if actual_hash != expected_hash:
        raise _fail("artifact_hash_mismatch")
    try:
        if filename.endswith(".whl"):
            parsed_name, parsed_version, _build, tags = parse_wheel_filename(filename)
            tag_strings = sorted(str(tag) for tag in tags)
            target_minor = int(abi[3:])

            def interpreter_compatible(interpreter: str, selected_abi: str) -> bool:
                if interpreter == selected_abi or "py3" in interpreter.split("."):
                    return True
                match = re.fullmatch(r"cp3(\d+)", interpreter)
                return bool(match and int(match.group(1)) <= target_minor)

            compatible = any(
                (tag.platform == "any" and tag.abi == "none" and interpreter_compatible(tag.interpreter, abi))
                or (
                    interpreter_compatible(tag.interpreter, abi)
                    and (tag.abi in {"none", "abi3"} or tag.interpreter == abi)
                    and tag.platform.startswith("macosx_")
                    and (tag.platform.endswith("_arm64") or tag.platform.endswith("_universal2"))
                )
                for tag in tags
            )
            kind, build_hook = "wheel", False
            if not compatible:
                raise _fail("artifact_wheel_tag_incompatible")
        else:
            parsed_name, parsed_version = parse_sdist_filename(filename)
            tag_strings = []
            kind, build_hook = "sdist", True
    except ValueError as error:
        if str(error).startswith("acquisition_"):
            raise
        raise _fail("artifact_filename_invalid") from error
    if canonicalize_name(package) != canonicalize_name(parsed_name) or str(parsed_version) != version:
        raise _fail("artifact_filename_identity_mismatch")
    return (
        {
            "package": canonicalize_name(package),
            "version": version,
            "filename": filename,
            "url": url,
            "sha256": actual_hash,
            "size": path.stat().st_size,
            "kind": kind,
            "tags": tag_strings,
            "build_hook_required": build_hook,
        },
        path,
    )


def _manager_lock(request: Mapping[str, Any], records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "specfact-macos-offline-manager-lock-v1",
        "manager": request["manager"],
        "selection": request["selection"],
        "abi": request["abi"],
        "platform": request["platform"],
        "artifacts": [
            {key: record[key] for key in ("package", "version", "filename", "sha256", "kind", "tags")}
            for record in records
        ],
    }


def _trusted_source_evidence(
    request: Mapping[str, Any], archive_sha256: str, tree_sha256: str, verifier: SourceVerifier
) -> dict[str, Any]:
    evidence = dict(verifier(request, archive_sha256, tree_sha256))
    source = request["source"]
    required = {
        "schema": "specfact-trusted-source-fetch-v1",
        "source_url": source["url"],
        "archive_url": source["archive_url"],
        "commit": source["commit"],
        "archive_sha256": archive_sha256,
        "tree_sha256": tree_sha256,
        "authenticated_transport": True,
    }
    if any(evidence.get(key) != value for key, value in required.items()):
        raise _fail("trusted_source_evidence_mismatch")
    if evidence.get("method") not in {"git-checkout", "github-commit-api-and-archive"}:
        raise _fail("trusted_source_method_invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("git_tree", ""))):
        raise _fail("trusted_source_tree_invalid")
    if set(evidence) != {*required, "method", "git_tree"}:
        raise _fail("trusted_source_evidence_fields_invalid")
    return evidence


def create_acquisition_bundle(
    request: Mapping[str, Any],
    source_archive: Path,
    *,
    artifacts: Sequence[Mapping[str, Any]],
    destination: Path,
    signer: Signer,
    source_verifier: SourceVerifier,
) -> dict[str, Any]:
    """Validate trusted fetch results and emit one authenticated offline bundle."""
    if request.get("schema") != "specfact-macos-project-acquisition-request-v1":
        raise _fail("request_invalid")
    if source_archive.is_symlink() or not source_archive.is_file():
        raise _fail("source_archive_invalid")
    if source_archive.stat().st_size > MAX_BUNDLE_BYTES:
        raise _fail("bundle_bytes_exceeded")
    if not artifacts or len(artifacts) > MAX_ARTIFACTS:
        raise _fail("artifact_count_invalid")
    if destination.exists() or destination.is_symlink():
        raise _fail("destination_exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        copied_archive = temporary / "source.tar.gz"
        shutil.copyfile(source_archive, copied_archive)
        copied_archive.chmod(0o600)
        tree = _extract_source(copied_archive, temporary / "source")
        bundle_bytes = copied_archive.stat().st_size + sum(record["size"] for record in tree.values())
        if bundle_bytes > MAX_BUNDLE_BYTES:
            raise _fail("bundle_bytes_exceeded")
        archive_sha256 = _sha256(copied_archive)
        tree_sha256 = _digest(tree)
        source_evidence = _trusted_source_evidence(request, archive_sha256, tree_sha256, source_verifier)
        wheelhouse = temporary / "wheelhouse"
        wheelhouse.mkdir(mode=0o700)
        records: list[dict[str, Any]] = []
        names: set[str] = set()
        total = 0
        for artifact in artifacts:
            record, source = _artifact_record(artifact, request["abi"])
            if record["filename"] in names:
                raise _fail("artifact_filename_duplicate")
            names.add(record["filename"])
            total += record["size"]
            if total > MAX_ARTIFACT_BYTES:
                raise _fail("artifact_bytes_exceeded")
            if record["size"] > MAX_BUNDLE_BYTES - bundle_bytes:
                raise _fail("bundle_bytes_exceeded")
            bundle_bytes += record["size"]
            shutil.copyfile(source, wheelhouse / record["filename"])
            (wheelhouse / record["filename"]).chmod(0o600)
            record["mode"] = 0o600
            records.append(record)
        records.sort(key=lambda item: (item["package"], item["version"], item["filename"]))
        lock = _manager_lock(request, records)
        locks = temporary / "locks"
        locks.mkdir(mode=0o700)
        lock_path = locks / f"{request['manager']['name']}.json"
        lock_bytes = _canonical_json(lock)
        lock_path.write_bytes(lock_bytes)
        lock_path.chmod(0o600)
        unsigned = {
            "schema": SCHEMA,
            "project": request["project"],
            "corpus_identity": request["corpus_identity"],
            "abi": request["abi"],
            "platform": request["platform"],
            "manager": request["manager"],
            "source": {
                **request["source"],
                "archive_path": "source.tar.gz",
                "archive_sha256": archive_sha256,
                "tree_sha256": tree_sha256,
                "inventory": tree,
                "trusted_fetch": source_evidence,
            },
            "artifacts": records,
            "manager_lock": {
                "path": lock_path.relative_to(temporary).as_posix(),
                "sha256": hashlib.sha256(lock_bytes).hexdigest(),
            },
            "acquisition_executed_project_code": False,
        }
        content_sha256 = _digest(unsigned)
        signed = {**unsigned, "content_sha256": content_sha256}
        signature = dict(signer(_canonical_json(signed)))
        if set(signature) != {"algorithm", "key_id", "value"} or not all(
            isinstance(value, str) and value for value in signature.values()
        ):
            raise _fail("signature_invalid")
        descriptor = {**signed, "signature": signature}
        (temporary / "descriptor.json").write_bytes(_canonical_json(descriptor))
        (temporary / "descriptor.json").chmod(0o600)
        (temporary / "COMPLETE").write_text(content_sha256 + "\n", encoding="ascii")
        (temporary / "COMPLETE").chmod(0o600)
        _check_bundle_size(temporary)
        os.replace(temporary, destination)
        return descriptor
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _inventory_source(root: Path) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    source = root / "source"
    if source.is_symlink() or not source.is_dir():
        raise _fail("source_tree_missing")
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise _fail("source_tree_link")
        if path.is_dir():
            continue
        if not path.is_file():
            raise _fail("source_tree_special")
        relative = path.relative_to(source).as_posix()
        inventory[relative] = {
            "sha256": _sha256(path),
            "size": path.stat().st_size,
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    return inventory


def verify_acquisition_bundle(root: Path, *, verifier: Verifier) -> dict[str, Any]:
    """Verify signature, source, generated lock and complete artifact closure."""
    if root.is_symlink() or not root.is_dir():
        raise _fail("bundle_missing")
    _check_bundle_size(root)
    for name in ("descriptor.json", "COMPLETE", "source.tar.gz"):
        path = root / name
        if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise _fail("bundle_metadata_mode_invalid")
    try:
        descriptor = json.loads((root / "descriptor.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _fail("descriptor_invalid") from error
    if not isinstance(descriptor, dict) or descriptor.get("schema") != SCHEMA:
        raise _fail("descriptor_invalid")
    signature = descriptor.pop("signature", None)
    if not isinstance(signature, dict) or not verifier(_canonical_json(descriptor), signature):
        raise _fail("signature_invalid")
    content_sha256 = descriptor.get("content_sha256")
    unsigned = {key: value for key, value in descriptor.items() if key != "content_sha256"}
    if not isinstance(content_sha256, str) or content_sha256 != _digest(unsigned):
        raise _fail("content_digest_mismatch")
    try:
        if (root / "COMPLETE").read_text(encoding="ascii") != content_sha256 + "\n":
            raise _fail("completion_marker_invalid")
    except OSError as error:
        raise _fail("completion_marker_missing") from error
    source = descriptor.get("source", {})
    archive = root / source.get("archive_path", "")
    if archive.is_symlink() or not archive.is_file() or _sha256(archive) != source.get("archive_sha256"):
        raise _fail("source_archive_mismatch")
    inventory = _inventory_source(root)
    if inventory != source.get("inventory") or _digest(inventory) != source.get("tree_sha256"):
        raise _fail("source_tree_mismatch")
    seen: set[str] = set()
    for record in descriptor.get("artifacts", []):
        if not isinstance(record, dict) or record.get("filename") in seen:
            raise _fail("artifact_descriptor_invalid")
        seen.add(record["filename"])
        path = root / "wheelhouse" / record["filename"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size != record.get("size"):
            raise _fail("artifact_missing")
        if stat.S_IMODE(path.stat().st_mode) != record.get("mode") or record.get("mode") != 0o600:
            raise _fail("artifact_mode_mismatch")
        if _sha256(path) != record.get("sha256"):
            raise _fail("artifact_hash_mismatch")
    wheelhouse = root / "wheelhouse"
    actual_files: set[str] = set()
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise _fail("wheelhouse_missing")
    for path in wheelhouse.iterdir():
        if path.is_symlink() or not path.is_file():
            raise _fail("wheelhouse_special_file")
        actual_files.add(path.name)
    if actual_files != seen:
        raise _fail("wheelhouse_inventory_mismatch")
    lock = descriptor.get("manager_lock", {})
    lock_path = root / lock.get("path", "")
    if (
        lock_path.is_symlink()
        or not lock_path.is_file()
        or not lock_path.resolve().is_relative_to(root.resolve())
        or stat.S_IMODE(lock_path.stat().st_mode) != 0o600
        or _sha256(lock_path) != lock.get("sha256")
    ):
        raise _fail("manager_lock_mismatch")
    return {**descriptor, "signature": signature}


def install_acquisition_bundle(staged: Path, cache: Path, *, verifier: Verifier) -> Path:
    """Atomically install verified content, preserving a valid concurrent winner."""
    descriptor = verify_acquisition_bundle(staged, verifier=verifier)
    if cache.is_symlink() or (cache.exists() and not cache.is_dir()):
        raise _fail("cache_root_invalid")
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = cache / descriptor["content_sha256"]
    if destination.exists():
        verify_acquisition_bundle(destination, verifier=verifier)
        return destination
    temporary = cache / f".{descriptor['content_sha256']}.{os.getpid()}.partial"
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(staged, temporary, symlinks=False)
    verify_acquisition_bundle(temporary, verifier=verifier)
    try:
        os.rename(temporary, destination)
    except OSError:
        shutil.rmtree(temporary, ignore_errors=True)
        verify_acquisition_bundle(destination, verifier=verifier)
    return destination


def open_offline_bundle(cache: Path, content_sha256: str, *, verifier: Verifier) -> Path:
    """Open only one exact, complete, previously authenticated cache entry."""
    if not re.fullmatch(r"[0-9a-f]{64}", content_sha256):
        raise _fail("cache_identity_invalid")
    if cache.is_symlink() or not cache.is_dir():
        raise _fail("cache_root_invalid")
    destination = cache / content_sha256
    descriptor = verify_acquisition_bundle(destination, verifier=verifier)
    if descriptor["content_sha256"] != content_sha256:
        raise _fail("cache_identity_mismatch")
    return destination
