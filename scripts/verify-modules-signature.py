#!/usr/bin/env python3
# ruff: noqa: N999
"""Verify bundled module checksums/signatures against full module payload."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import yaml
from beartype import beartype
from icontract import ensure, require


try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
except ImportError:  # pragma: no cover - exercised through runtime error path
    InvalidSignature = None
    hashes = None
    serialization = None
    ed25519 = None
    padding = None
    rsa = None


_IGNORED_MODULE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "logs"}
_PAYLOAD_FROM_FS_IGNORED_DIRS = _IGNORED_MODULE_DIR_NAMES | {".git", "tests"}
_IGNORED_MODULE_FILE_SUFFIXES = {".pyc", ".pyo"}
_MANIFEST_NAMES = {"module-package.yaml", "metadata.yaml"}


def _emit_line(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{message}\n")


def _canonical_manifest_payload(manifest_data: dict[str, Any]) -> bytes:
    payload = dict(manifest_data)
    payload.pop("integrity", None)
    return yaml.safe_dump(payload, sort_keys=True, allow_unicode=False).encode("utf-8")


def _ignored_dirs(*, payload_from_filesystem: bool) -> set[str]:
    return _PAYLOAD_FROM_FS_IGNORED_DIRS if payload_from_filesystem else _IGNORED_MODULE_DIR_NAMES


def _is_hashable(path: Path, *, module_dir_resolved: Path, ignored_dirs: set[str]) -> bool:
    rel = path.resolve().relative_to(module_dir_resolved)
    if any(part in ignored_dirs for part in rel.parts):
        return False
    return path.suffix.lower() not in _IGNORED_MODULE_FILE_SUFFIXES


def _filesystem_files(module_dir: Path, *, module_dir_resolved: Path, ignored_dirs: set[str]) -> list[Path]:
    return sorted(
        (
            p
            for p in module_dir.rglob("*")
            if p.is_file() and _is_hashable(p, module_dir_resolved=module_dir_resolved, ignored_dirs=ignored_dirs)
        ),
        key=lambda p: p.resolve().relative_to(module_dir_resolved).as_posix(),
    )


def _git_tracked_files(module_dir: Path, *, module_dir_resolved: Path, ignored_dirs: set[str]) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", module_dir.as_posix()],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    git_files = [(Path.cwd() / line.strip()) for line in listed if line.strip()]
    return sorted(
        (
            path
            for path in git_files
            if path.is_file() and _is_hashable(path, module_dir_resolved=module_dir_resolved, ignored_dirs=ignored_dirs)
        ),
        key=lambda p: p.resolve().relative_to(module_dir_resolved).as_posix(),
    )


def _module_files(module_dir: Path, *, payload_from_filesystem: bool) -> list[Path]:
    module_dir_resolved = module_dir.resolve()
    ignored_dirs = _ignored_dirs(payload_from_filesystem=payload_from_filesystem)
    if payload_from_filesystem:
        return _filesystem_files(module_dir, module_dir_resolved=module_dir_resolved, ignored_dirs=ignored_dirs)
    try:
        return _git_tracked_files(module_dir, module_dir_resolved=module_dir_resolved, ignored_dirs=ignored_dirs)
    except (subprocess.CalledProcessError, OSError, ValueError):
        return _filesystem_files(module_dir, module_dir_resolved=module_dir_resolved, ignored_dirs=ignored_dirs)


def _payload_entry(path: Path, *, module_dir_resolved: Path) -> str:
    rel = path.resolve().relative_to(module_dir_resolved).as_posix()
    if rel in _MANIFEST_NAMES:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid manifest YAML: {path}")
        data = _canonical_manifest_payload(raw)
    else:
        data = path.read_bytes()
    return f"{rel}:{hashlib.sha256(data).hexdigest()}"


def _module_payload(module_dir: Path, *, payload_from_filesystem: bool = False) -> bytes:
    module_dir_resolved = module_dir.resolve()
    entries = [
        _payload_entry(path, module_dir_resolved=module_dir_resolved)
        for path in _module_files(module_dir, payload_from_filesystem=payload_from_filesystem)
    ]
    return "\n".join(entries).encode("utf-8")


def _parse_checksum(checksum: str) -> tuple[str, str]:
    if ":" not in checksum:
        raise ValueError("Checksum must be in algo:hex format")
    algo, digest = checksum.split(":", 1)
    algo = algo.strip().lower()
    digest = digest.strip().lower()
    if algo not in {"sha256", "sha384", "sha512"}:
        raise ValueError(f"Unsupported checksum algorithm: {algo}")
    if not digest:
        raise ValueError("Checksum digest is empty")
    return algo, digest


def _checksum_matches(module_dir: Path, *, algo: str, digest: str, payload_from_filesystem: bool) -> bool:
    payload = _module_payload(module_dir, payload_from_filesystem=payload_from_filesystem)
    actual = hashlib.new(algo, payload).hexdigest().lower()
    return actual == digest


def _cryptography_backend_available() -> bool:
    return all(
        dependency is not None for dependency in (InvalidSignature, hashes, serialization, ed25519, padding, rsa)
    )


def _cryptography_backend() -> tuple[Any, Any, Any, Any, Any, Any]:
    if not _cryptography_backend_available():
        raise ValueError("cryptography backend missing; install with `python3 -m pip install cryptography cffi`")
    return (
        cast(Any, InvalidSignature),
        cast(Any, hashes),
        cast(Any, serialization),
        cast(Any, ed25519),
        cast(Any, padding),
        cast(Any, rsa),
    )


def _verify_signature(payload: bytes, signature_b64: str, public_key_pem: str) -> None:
    invalid_signature, crypto_hashes, crypto_serialization, crypto_ed25519, crypto_padding, crypto_rsa = (
        _cryptography_backend()
    )

    public_key = crypto_serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    signature = base64.b64decode(signature_b64, validate=True)

    try:
        if isinstance(public_key, crypto_rsa.RSAPublicKey):
            public_key.verify(signature, payload, crypto_padding.PKCS1v15(), crypto_hashes.SHA256())
            return
        if isinstance(public_key, crypto_ed25519.Ed25519PublicKey):
            public_key.verify(signature, payload)
            return
    except invalid_signature as exc:
        raise ValueError("Signature validation failed") from exc
    raise ValueError("Unsupported public key type (RSA or Ed25519 required)")


def _resolve_public_key(args: argparse.Namespace) -> str:
    if args.public_key_file:
        return Path(args.public_key_file).read_text(encoding="utf-8").strip()
    env_key_file = os.environ.get("SPECFACT_MODULE_PUBLIC_SIGN_KEY_FILE", "").strip()
    if not env_key_file:
        env_key_file = os.environ.get("SPECFACT_MODULE_SIGNING_PUBLIC_KEY_FILE", "").strip()
    if env_key_file:
        return Path(env_key_file).read_text(encoding="utf-8").strip()
    env_key_inline = os.environ.get("SPECFACT_MODULE_PUBLIC_SIGN_KEY", "").strip()
    if not env_key_inline:
        env_key_inline = os.environ.get("SPECFACT_MODULE_SIGNING_PUBLIC_KEY_PEM", "").strip()
    if env_key_inline:
        return env_key_inline
    env_key = (args.public_key_pem or "").strip()
    if env_key:
        return env_key
    default_paths = [
        Path("resources/keys/module-signing-public.pem"),
        Path("src/specfact_cli/resources/keys/module-signing-public.pem"),
        Path.home() / ".specfact" / "sign-keys" / "module-signing-public.pem",
    ]
    for default_path in default_paths:
        if default_path.exists():
            return default_path.read_text(encoding="utf-8").strip()
    return ""


def _iter_manifests() -> list[Path]:
    roots = [Path("packages")]
    manifests: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        manifests.extend(sorted(root.rglob("module-package.yaml")))
    return manifests


def _read_manifest_version(path: Path) -> str | None:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    value = raw.get("version")
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def _read_manifest_version_from_git(ref: str, manifest_path: Path) -> str | None:
    try:
        output = subprocess.run(
            ["git", "show", f"{ref}:{manifest_path.as_posix()}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    try:
        raw = yaml.safe_load(output.stdout)
    except yaml.YAMLError:
        return None
    if not isinstance(raw, dict):
        return None
    value = raw.get("version")
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def _resolve_version_check_base(explicit_base: str | None) -> str:
    if explicit_base and explicit_base.strip():
        return explicit_base.strip()

    env_base_ref = (os.environ.get("GITHUB_BASE_REF", "") or "").strip()
    if env_base_ref:
        return f"origin/{env_base_ref}"
    return "HEAD~1"


def _changed_manifests_from_git(base_ref: str) -> list[Path]:
    try:
        output = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                f"{base_ref}...HEAD",
                "--",
                "packages",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ValueError(f"Unable to diff manifests against base ref '{base_ref}': {exc}") from exc

    manifests: list[Path] = []
    seen: set[Path] = set()
    for line in output.stdout.splitlines():
        changed_path = Path(line.strip())
        if not changed_path:
            continue
        parts = changed_path.parts
        manifest: Path | None = None
        if len(parts) >= 2 and parts[0] == "packages":
            manifest = Path(*parts[:2]) / "module-package.yaml"
        if manifest and manifest.exists() and manifest not in seen:
            manifests.append(manifest)
            seen.add(manifest)
    return manifests


def _verify_version_bumps(base_ref: str) -> list[str]:
    failures: list[str] = []
    for manifest in _changed_manifests_from_git(base_ref):
        current_version = _read_manifest_version(manifest)
        previous_version = _read_manifest_version_from_git(base_ref, manifest)
        if not current_version or not previous_version:
            continue
        if current_version == previous_version:
            failures.append(
                f"FAIL {manifest}: module version was not incremented (still {current_version}) compared to {base_ref}"
            )
    return failures


@beartype
@require(lambda manifest_path: manifest_path.exists(), "manifest_path must exist")
@ensure(lambda result: result in {"git", "filesystem"}, "verification mode must be explicit")
def verify_manifest(
    manifest_path: Path,
    *,
    require_signature: bool,
    public_key_pem: str,
    payload_from_filesystem: bool = False,
) -> str:
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("manifest YAML must be object")
    integrity = raw.get("integrity")
    if not isinstance(integrity, dict):
        raise ValueError("missing integrity metadata")

    checksum = str(integrity.get("checksum", "")).strip()
    if not checksum:
        raise ValueError("missing integrity.checksum")
    algo, digest = _parse_checksum(checksum)
    verification_mode = "filesystem" if payload_from_filesystem else "git"
    payload = _module_payload(manifest_path.parent, payload_from_filesystem=payload_from_filesystem)
    actual = hashlib.new(algo, payload).hexdigest().lower()
    if actual != digest:
        if not payload_from_filesystem and _checksum_matches(
            manifest_path.parent,
            algo=algo,
            digest=digest,
            payload_from_filesystem=True,
        ):
            verification_mode = "filesystem"
            payload = _module_payload(manifest_path.parent, payload_from_filesystem=True)
        else:
            raise ValueError("checksum mismatch")

    signature = str(integrity.get("signature", "")).strip()
    if require_signature and not signature:
        raise ValueError("missing integrity.signature")
    if signature:
        if not public_key_pem:
            raise ValueError("public key required to verify signature")
        _verify_signature(payload, signature, public_key_pem)
    return verification_mode


@beartype
@ensure(lambda result: result in {0, 1}, "main must return a process exit code")
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-signature", action="store_true", help="Require integrity.signature for every manifest"
    )
    parser.add_argument("--public-key-file", default="", help="Path to PEM public key")
    parser.add_argument(
        "--public-key-pem",
        default="",
        help="Inline PEM public key content (optional; fallback after --public-key-file)",
    )
    parser.add_argument(
        "--enforce-version-bump",
        action="store_true",
        help="Fail when changed module manifests keep the same version as base ref",
    )
    parser.add_argument(
        "--version-check-base",
        default="",
        help="Git base ref for version-bump checks (default: origin/$GITHUB_BASE_REF or HEAD~1)",
    )
    parser.add_argument(
        "--payload-from-filesystem",
        action="store_true",
        help=(
            "Build payload from filesystem (rglob) with the same excludes as "
            "sign-modules, so verification matches manifests signed with "
            "--payload-from-filesystem."
        ),
    )
    args = parser.parse_args()

    public_key_pem = _resolve_public_key(args)
    manifests = _iter_manifests()
    if not manifests:
        _emit_line("No module-package.yaml manifests found.")
        return 0

    failures: list[str] = []
    for manifest in manifests:
        try:
            verification_mode = verify_manifest(
                manifest,
                require_signature=args.require_signature,
                public_key_pem=public_key_pem,
                payload_from_filesystem=args.payload_from_filesystem,
            )
            suffix = (
                " (filesystem payload)"
                if verification_mode == "filesystem" and not args.payload_from_filesystem
                else ""
            )
            _emit_line(f"OK  {manifest}{suffix}")
        except ValueError as exc:
            failures.append(f"FAIL {manifest}: {exc}")

    version_failures: list[str] = []
    if args.enforce_version_bump:
        base_ref = _resolve_version_check_base(args.version_check_base)
        try:
            version_failures = _verify_version_bumps(base_ref)
        except ValueError as exc:
            version_failures.append(f"FAIL version-check: {exc}")

    if failures or version_failures:
        if failures:
            _emit_line("\n".join(failures), error=True)
        if version_failures:
            _emit_line("\n".join(version_failures), error=True)
        return 1

    _emit_line(f"Verified {len(manifests)} module manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
