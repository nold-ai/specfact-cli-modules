#!/usr/bin/env python3
# ruff: noqa: N999
"""Sign SpecFact module manifests with checksum/signature over full module payload."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import os
import subprocess
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

import yaml


_FuncT = TypeVar("_FuncT", bound=Callable[..., Any])

if TYPE_CHECKING:
    from icontract import ensure, require
else:
    try:
        from icontract import ensure, require
    except ImportError:  # pragma: no cover - exercised in plain-python signing environments

        def require(
            _condition: Callable[..., bool],
            _description: str | None = None,
        ) -> Callable[[_FuncT], _FuncT]:
            def decorator(func: _FuncT) -> _FuncT:
                @wraps(func)
                def wrapper(*args: Any, **kwargs: Any) -> Any:
                    return func(*args, **kwargs)

                return cast(_FuncT, wrapper)

            return decorator

        def ensure(
            _condition: Callable[..., bool],
            _description: str | None = None,
        ) -> Callable[[_FuncT], _FuncT]:
            return require(_condition, _description)


try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
except ImportError:  # pragma: no cover - exercised only without signing dependencies
    hashes = None
    ed25519 = None
    padding = None
    rsa = None
    serialization = None


_IGNORED_MODULE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "logs"}
_IGNORED_MODULE_FILE_SUFFIXES = {".pyc", ".pyo"}
_PAYLOAD_FROM_FS_IGNORED_DIRS = _IGNORED_MODULE_DIR_NAMES | {".git", "tests"}


class _IndentedSafeDumper(yaml.SafeDumper):
    """Safe dumper that indents sequence items under their parent key."""

    @ensure(lambda result: result is None)
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow=flow, indentless=False)


def _canonical_payload(manifest_data: dict[str, Any]) -> bytes:
    payload = dict(manifest_data)
    payload.pop("integrity", None)
    return yaml.safe_dump(payload, sort_keys=True, allow_unicode=False).encode("utf-8")


def _is_hashable_module_file(path: Path, *, module_dir: Path, ignored_dirs: set[str]) -> bool:
    rel = path.resolve().relative_to(module_dir)
    return (
        not any(part in ignored_dirs for part in rel.parts) and path.suffix.lower() not in _IGNORED_MODULE_FILE_SUFFIXES
    )


def _sorted_hashable_files(paths: list[Path], *, module_dir: Path, ignored_dirs: set[str]) -> list[Path]:
    return sorted(
        (
            path
            for path in paths
            if path.is_file() and _is_hashable_module_file(path, module_dir=module_dir, ignored_dirs=ignored_dirs)
        ),
        key=lambda path: path.resolve().relative_to(module_dir).as_posix(),
    )


def _sorted_index_files(paths: list[Path], *, module_dir: Path, ignored_dirs: set[str]) -> list[Path]:
    return sorted(
        (path for path in paths if _is_hashable_module_file(path, module_dir=module_dir, ignored_dirs=ignored_dirs)),
        key=lambda path: path.resolve().relative_to(module_dir).as_posix(),
    )


def _git_module_files(module_dir: Path, *, ignored_dirs: set[str]) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", module_dir.as_posix()],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    files = [Path.cwd() / line.strip() for line in listed if line.strip()]
    return _sorted_hashable_files(files, module_dir=module_dir, ignored_dirs=ignored_dirs)


def _index_module_files(module_dir: Path, *, ignored_dirs: set[str]) -> list[Path]:
    repo_root = Path.cwd().resolve()
    try:
        relative_module_dir = module_dir.resolve().relative_to(repo_root).as_posix()
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "-z", "--", relative_module_dir],
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        raise ValueError(f"Unable to read staged module payload for {module_dir}: {exc}") from exc
    files = [repo_root / path.decode("utf-8") for path in listed if path]
    return _sorted_index_files(files, module_dir=module_dir, ignored_dirs=ignored_dirs)


def _module_files(module_dir: Path, *, payload_from_filesystem: bool, staged_snapshot: bool) -> list[Path]:
    ignored_dirs = _PAYLOAD_FROM_FS_IGNORED_DIRS if payload_from_filesystem else _IGNORED_MODULE_DIR_NAMES
    if staged_snapshot:
        return _index_module_files(module_dir, ignored_dirs=ignored_dirs)
    if payload_from_filesystem:
        return _sorted_hashable_files(list(module_dir.rglob("*")), module_dir=module_dir, ignored_dirs=ignored_dirs)
    try:
        return _git_module_files(module_dir, ignored_dirs=ignored_dirs)
    except (subprocess.CalledProcessError, OSError):
        return _sorted_hashable_files(list(module_dir.rglob("*")), module_dir=module_dir, ignored_dirs=ignored_dirs)


def _index_file_bytes(path: Path) -> bytes:
    try:
        relative_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        return subprocess.run(
            ["git", "show", f":{relative_path}"],
            check=True,
            capture_output=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        raise ValueError(f"Unable to read staged file {path}: {exc}") from exc


def _payload_file_data(path: Path, *, module_dir: Path, staged_snapshot: bool) -> bytes:
    rel = path.resolve().relative_to(module_dir).as_posix()
    if rel not in {"module-package.yaml", "metadata.yaml"}:
        return _index_file_bytes(path) if staged_snapshot else path.read_bytes()
    content = _index_file_bytes(path) if staged_snapshot else path.read_bytes()
    raw = yaml.safe_load(content)
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid manifest YAML: {path}")
    return _canonical_payload(raw)


def _module_payload(
    module_dir: Path,
    payload_from_filesystem: bool = False,
    *,
    staged_snapshot: bool = False,
) -> bytes:
    if not module_dir.is_dir():
        raise ValueError(f"Module directory not found: {module_dir}")
    resolved_module_dir = module_dir.resolve()
    entries = []
    for path in _module_files(
        resolved_module_dir,
        payload_from_filesystem=payload_from_filesystem,
        staged_snapshot=staged_snapshot,
    ):
        relative_path = path.resolve().relative_to(resolved_module_dir).as_posix()
        digest = hashlib.sha256(
            _payload_file_data(path, module_dir=resolved_module_dir, staged_snapshot=staged_snapshot)
        ).hexdigest()
        entries.append(f"{relative_path}:{digest}")
    return "\n".join(entries).encode("utf-8")


def _first_environment_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _private_key_pem(key_file: Path | None) -> str:
    inline_pem = _first_environment_value(
        "SPECFACT_MODULE_PRIVATE_SIGN_KEY",
        "SPECFACT_MODULE_SIGNING_PRIVATE_KEY_PEM",
    )
    if inline_pem:
        return inline_pem
    configured_file = _first_environment_value(
        "SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE",
        "SPECFACT_MODULE_SIGNING_PRIVATE_KEY_FILE",
    )
    effective_file = key_file or (Path(configured_file) if configured_file else None)
    return effective_file.read_text(encoding="utf-8") if effective_file else ""


def _signing_serialization() -> Any:
    if serialization is None:
        raise ValueError(
            "Unable to import cryptography backend for signing. "
            "Install signing dependencies (`python3 -m pip install cryptography cffi`) "
            "or run via project environment (`hatch run python scripts/sign-modules.py ...`)."
        )
    return serialization


def _signing_primitives() -> tuple[Any, Any, Any, Any]:
    if any(dependency is None for dependency in (hashes, ed25519, padding, rsa)):
        raise ValueError("cryptography signing primitives are unavailable")
    return hashes, ed25519, padding, rsa


def _is_encrypted_key_error(error: ValueError | TypeError) -> bool:
    message = str(error).lower()
    return "password was not given" in message or "private key is encrypted" in message


def _load_private_key_from_pem(pem: str, password: bytes | None) -> Any:
    return _signing_serialization().load_pem_private_key(pem.encode("utf-8"), password=password)


def _prompt_for_private_key(pem: str) -> Any:
    prompted = getpass.getpass("Enter signing key passphrase: ")
    try:
        return _load_private_key_from_pem(pem, prompted.encode("utf-8"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Failed to load private key from PEM: {error}") from error


def _load_private_key(
    key_file: Path | None = None,
    *,
    passphrase: str | None = None,
    prompt_for_passphrase: bool = False,
) -> Any | None:
    pem = _private_key_pem(key_file)
    if not pem:
        return None
    password = passphrase.encode("utf-8") if passphrase is not None else None
    try:
        return _load_private_key_from_pem(pem, password)
    except (TypeError, ValueError) as error:
        if _is_encrypted_key_error(error) and prompt_for_passphrase:
            return _prompt_for_private_key(pem)
        if _is_encrypted_key_error(error) and passphrase is None:
            raise ValueError(
                "Private key is encrypted. Provide passphrase via --passphrase, --passphrase-stdin, "
                "or SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE."
            ) from error
        raise ValueError(f"Failed to load private key from PEM: {error}") from error


def _resolve_passphrase(args: argparse.Namespace) -> str | None:
    explicit = (args.passphrase or "").strip()
    if explicit:
        return explicit
    env_value = os.environ.get("SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE", "").strip()
    if not env_value:
        env_value = os.environ.get("SPECFACT_MODULE_SIGNING_PRIVATE_KEY_PASSPHRASE", "").strip()
    if env_value:
        return env_value
    if args.passphrase_stdin:
        piped = sys.stdin.read().rstrip("\r\n")
        return piped if piped else None
    return None


def _manifest_data(path: Path, *, staged_snapshot: bool) -> dict[str, Any]:
    content = _index_file_bytes(path) if staged_snapshot else path.read_bytes()
    raw = yaml.safe_load(content)
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid manifest YAML: {path}")
    return raw


def _read_manifest_version(path: Path, *, staged_snapshot: bool = False) -> str | None:
    raw = _manifest_data(path, staged_snapshot=staged_snapshot)
    value = raw.get("version")
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def _read_manifest_version_from_git(git_ref: str, path: Path) -> str | None:
    try:
        output = subprocess.run(
            ["git", "show", f"{git_ref}:{path.as_posix()}"],
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


def _iter_manifests() -> list[Path]:
    roots = [Path("packages")]
    manifests: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        manifests.extend(sorted(root.rglob("module-package.yaml")))
    return manifests


def _ensure_valid_git_ref(git_ref: str) -> None:
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{git_ref}^{{commit}}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {details}" if details else ""
        raise ValueError(f"--base-ref is invalid or not resolvable: {git_ref}{suffix}") from exc


def _module_has_git_changes_since(module_dir: Path, git_ref: str) -> bool:
    try:
        changed = subprocess.run(
            ["git", "diff", "--name-only", git_ref, "--", module_dir.as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", module_dir.as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ValueError(f"Unable to inspect module changes since {git_ref}: {exc}") from exc
    return bool(changed or untracked)


def _module_has_index_changes_since(module_dir: Path, git_ref: str) -> bool:
    try:
        changed = subprocess.run(
            ["git", "diff", "--cached", "--name-only", git_ref, "--", module_dir.as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ValueError(f"Unable to inspect staged module changes since {git_ref}: {exc}") from exc
    return bool(changed)


def _module_has_staged_changes(module_dir: Path) -> bool:
    try:
        changed = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", module_dir.as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ValueError(f"Unable to inspect staged module changes for {module_dir}: {exc}") from exc
    return bool(changed)


def _parse_semver(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"Unsupported version format for auto-bump (expected x.y.z): {version}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _bump_semver(version: str, bump_type: str) -> str:
    major, minor, patch = _parse_semver(version)
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    if bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unsupported bump type: {bump_type}")


def _write_manifest(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.dump(
            data,
            Dumper=_IndentedSafeDumper,
            sort_keys=False,
            allow_unicode=False,
            default_flow_style=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _has_unstaged_manifest_changes(manifest_path: Path) -> bool:
    try:
        changed = subprocess.run(
            ["git", "diff", "--name-only", "--", manifest_path.as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ValueError(f"Unable to inspect unstaged manifest changes for {manifest_path}: {exc}") from exc
    return bool(changed)


def _report(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _auto_bump_manifest_version(
    manifest_path: Path,
    *,
    base_ref: str,
    bump_type: str,
    staged_snapshot: bool,
) -> bool:
    current_version = _read_manifest_version(manifest_path, staged_snapshot=staged_snapshot)
    if not current_version:
        raise ValueError(f"Manifest missing version: {manifest_path}")

    previous_version = _read_manifest_version_from_git(base_ref, manifest_path)
    if previous_version is None or current_version != previous_version:
        return False

    raw = _manifest_data(manifest_path, staged_snapshot=staged_snapshot)
    bumped = _bump_semver(current_version, bump_type)
    raw["version"] = bumped
    _write_manifest(manifest_path, raw)
    _report(f"{manifest_path}: version {current_version} -> {bumped}")
    return True


def _enforce_version_bump_before_signing(
    manifest_path: Path,
    *,
    allow_same_version: bool,
    comparison_ref: str = "HEAD",
    staged_snapshot: bool,
) -> None:
    if allow_same_version:
        return

    current_version = _read_manifest_version(manifest_path, staged_snapshot=staged_snapshot)
    if not current_version:
        raise ValueError(f"Manifest missing version: {manifest_path}")

    previous_version = _read_manifest_version_from_git(comparison_ref, manifest_path)
    if previous_version is None:
        return
    if current_version != previous_version:
        return

    module_dir = manifest_path.parent
    has_changes = (
        _module_has_index_changes_since(module_dir, comparison_ref)
        if staged_snapshot
        else _module_has_git_changes_since(module_dir, comparison_ref)
    )
    if not has_changes:
        return

    raise ValueError(
        f"Module version must be incremented before signing changed module contents: {manifest_path} "
        f"(current version {current_version})."
    )


def _sign_payload(payload: bytes, private_key: Any) -> str:
    crypto_hashes, crypto_ed25519, crypto_padding, crypto_rsa = _signing_primitives()

    if isinstance(private_key, crypto_ed25519.Ed25519PrivateKey):
        signature = private_key.sign(payload)
    elif isinstance(private_key, crypto_rsa.RSAPrivateKey):
        signature = private_key.sign(payload, crypto_padding.PKCS1v15(), crypto_hashes.SHA256())
    else:
        msg = "Unsupported private key type for signing (RSA and Ed25519 only)"
        raise ValueError(msg)
    return base64.b64encode(signature).decode("ascii")


@require(lambda manifest_path: manifest_path.is_file(), "manifest_path must be a file")
@ensure(lambda result: result is None, "sign_manifest returns None")
def sign_manifest(
    manifest_path: Path,
    private_key: Any | None,
    *,
    payload_from_filesystem: bool = False,
    staged_snapshot: bool = False,
) -> None:
    if staged_snapshot and _has_unstaged_manifest_changes(manifest_path):
        raise ValueError(f"Refusing to overwrite unstaged manifest changes: {manifest_path}")
    raw = _manifest_data(manifest_path, staged_snapshot=staged_snapshot)

    payload = _module_payload(
        manifest_path.parent,
        payload_from_filesystem=payload_from_filesystem,
        staged_snapshot=staged_snapshot,
    )
    checksum = f"sha256:{hashlib.sha256(payload).hexdigest()}"
    integrity: dict[str, str] = {"checksum": checksum}

    if private_key is not None:
        integrity["signature"] = _sign_payload(payload, private_key)

    raw["integrity"] = integrity
    _write_manifest(manifest_path, raw)

    status = "checksum+signature" if "signature" in integrity else "checksum"
    _report(f"{manifest_path}: {status}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--key-file",
        type=Path,
        default=None,
        help=(
            "Path to PEM private key (overrides SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE). "
            "Supported keys: Ed25519 and RSA."
        ),
    )
    parser.add_argument(
        "--passphrase", default="", help="Passphrase for encrypted private key (discouraged in shell history)"
    )
    parser.add_argument(
        "--passphrase-stdin",
        action="store_true",
        help="Read private-key passphrase from stdin (for secure piping/CI use)",
    )
    parser.add_argument(
        "--allow-unsigned",
        action="store_true",
        help="Allow checksum-only signing without private key (local testing only).",
    )
    parser.add_argument(
        "--payload-from-filesystem",
        action="store_true",
        help=(
            "Build payload from filesystem (rglob) with same excludes as publish tarball, "
            "so checksum matches install verification."
        ),
    )
    parser.add_argument(
        "--allow-same-version",
        action="store_true",
        help="Bypass version-bump enforcement for changed module contents (not recommended).",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Select only manifests whose module payload changed since --base-ref.",
    )
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Select only manifests whose module payload is staged for the pending commit.",
    )
    parser.add_argument(
        "--base-ref",
        default="HEAD",
        help="Git ref used for change detection when --changed-only is set (default: HEAD).",
    )
    parser.add_argument(
        "--bump-version",
        choices=("patch", "minor", "major"),
        default="",
        help="Auto-bump changed module version when unchanged from --base-ref before signing.",
    )
    parser.add_argument("manifests", nargs="*", help="module-package.yaml path(s)")
    return parser


def _selection_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.changed_only and args.staged_only:
        parser.error("Use only one of --changed-only or --staged-only.")
    if args.changed_only:
        return "changed"
    if args.staged_only:
        return "staged"
    parser.error("Provide one or more manifests, or use --changed-only or --staged-only.")
    return ""


def _discover_manifests(mode: str, base_ref: str) -> list[Path]:
    if mode == "changed":
        return [manifest for manifest in _iter_manifests() if _module_has_git_changes_since(manifest.parent, base_ref)]
    return [manifest for manifest in _iter_manifests() if _module_has_staged_changes(manifest.parent)]


def _select_manifests(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[Path]:

    if args.manifests:
        if args.staged_only:
            parser.error("Do not combine explicit manifests with --staged-only.")
        return [Path(manifest) for manifest in args.manifests]

    mode = _selection_mode(args, parser)

    try:
        _ensure_valid_git_ref(args.base_ref)
    except ValueError as exc:
        parser.error(str(exc))
    return _discover_manifests(mode, args.base_ref)


def _sign_selected_manifests(
    manifests: list[Path], args: argparse.Namespace, parser: argparse.ArgumentParser, private_key: Any | None
) -> None:
    for manifest_path in manifests:
        try:
            if (args.changed_only or args.staged_only) and args.bump_version:
                _auto_bump_manifest_version(
                    manifest_path,
                    base_ref=args.base_ref,
                    bump_type=args.bump_version,
                    staged_snapshot=args.staged_only,
                )
            _enforce_version_bump_before_signing(
                manifest_path,
                allow_same_version=args.allow_same_version,
                comparison_ref=args.base_ref if args.changed_only else "HEAD",
                staged_snapshot=args.staged_only,
            )
            sign_manifest(
                manifest_path,
                private_key,
                payload_from_filesystem=args.payload_from_filesystem,
                staged_snapshot=args.staged_only,
            )
        except ValueError as exc:
            parser.error(str(exc))


@ensure(lambda result: result in {0, 1}, "main returns a process exit code")
def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    passphrase = _resolve_passphrase(args)
    try:
        private_key = _load_private_key(
            args.key_file,
            passphrase=passphrase,
            prompt_for_passphrase=sys.stdin.isatty() and not args.passphrase_stdin,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if private_key is None and not args.allow_unsigned:
        parser.error(
            "No signing key provided. Use --key-file <path> (recommended) "
            "or set SPECFACT_MODULE_PRIVATE_SIGN_KEY / SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE. "
            "For local testing only, re-run with --allow-unsigned."
        )

    try:
        manifests = _select_manifests(args, parser)
    except ValueError as exc:
        parser.error(str(exc))

    if (args.changed_only or args.staged_only) and not manifests:
        scope = f"since {args.base_ref}" if args.changed_only else "in the staged index"
        _report(f"No changed module manifests detected {scope}.")
        return 0

    _sign_selected_manifests(manifests, args, parser, private_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
