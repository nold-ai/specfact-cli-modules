#!/usr/bin/env python3
"""Align registry/index.json and registry/modules artifacts with packages/*/module-package.yaml.

**Not** a substitute for CI: ``publish-modules`` is the canonical path that signs, selects bundles,
and opens registry PRs. Use this script only for deliberate local tooling or recovery — never from
pre-commit — or you risk skipping or confusing the real publish flow on ``dev``/``main``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

import yaml


_FuncT = TypeVar("_FuncT", bound=Callable[..., Any])

if TYPE_CHECKING:
    from beartype import beartype
    from icontract import ensure, require
else:
    try:
        from beartype import beartype
    except ImportError:  # pragma: no cover - exercised in plain-python CI/runtime

        def beartype(func: _FuncT) -> _FuncT:
            return func

    try:
        from icontract import ensure, require
    except ImportError:  # pragma: no cover - exercised in plain-python CI/runtime

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


_IGNORED_DIR_NAMES = {".git", "tests", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "logs"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _emit_line(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{message}\n")


def _bundle_dir(repo_root: Path, bundle: str) -> Path:
    name = bundle.strip()
    if not name.startswith("specfact-"):
        name = f"specfact-{name}"
    path = repo_root / "packages" / name
    if not path.is_dir():
        msg = f"Bundle directory not found: {path}"
        raise FileNotFoundError(msg)
    return path


def _write_bundle_tarball(bundle_dir: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, mode="w:gz") as tar:
        for path in sorted(bundle_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(bundle_dir)
            if any(part in _IGNORED_DIR_NAMES for part in rel.parts):
                continue
            if path.suffix.lower() in _IGNORED_SUFFIXES:
                continue
            bundle_name = bundle_dir.name
            tar.add(path, arcname=f"{bundle_name}/{rel.as_posix()}")


def _load_module_manifest(bundle_dir: Path) -> tuple[dict[str, object], str, str]:
    manifest_path = bundle_dir / "module-package.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"Invalid manifest: {manifest_path}"
        raise ValueError(msg)
    bundle_name = bundle_dir.name
    module_id = str(data.get("name") or f"nold-ai/{bundle_name}").strip()
    version = str(data.get("version") or "").strip()
    if not module_id or not version:
        msg = f"Manifest missing name or version: {manifest_path}"
        raise ValueError(msg)
    return data, module_id, version


def _load_registry_index(repo_root: Path) -> tuple[Path, dict[str, object]]:
    registry_path = repo_root / "registry" / "index.json"
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(reg, dict):
        msg = "registry/index.json root must be an object"
        raise ValueError(msg)
    return registry_path, reg


def _prepare_registry_output_dirs(repo_root: Path) -> tuple[Path, Path]:
    modules_dir = repo_root / "registry" / "modules"
    signatures_dir = repo_root / "registry" / "signatures"
    modules_dir.mkdir(parents=True, exist_ok=True)
    signatures_dir.mkdir(parents=True, exist_ok=True)
    return modules_dir, signatures_dir


def _build_registry_tarball_and_digest(
    bundle_dir: Path, modules_dir: Path, bundle_name: str, version: str
) -> tuple[str, str]:
    artifact_name = f"{bundle_name}-{version}.tar.gz"
    artifact_path = modules_dir / artifact_name
    _write_bundle_tarball(bundle_dir, artifact_path)
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    (artifact_path.with_suffix(artifact_path.suffix + ".sha256")).write_text(f"{digest}\n", encoding="utf-8")
    return artifact_name, digest


def _maybe_write_tarball_signature(
    manifest: dict[str, object], signatures_dir: Path, bundle_name: str, version: str
) -> None:
    integrity = manifest.get("integrity")
    if not isinstance(integrity, dict):
        return
    signature_text = str(integrity.get("signature") or "").strip()
    if not signature_text:
        return
    sig_path = signatures_dir / f"{bundle_name}-{version}.tar.sig"
    sig_path.write_text(signature_text + "\n", encoding="utf-8")


def _upsert_registry_module_row(
    registry: dict[str, object],
    *,
    module_id: str,
    manifest: dict[str, object],
    release: dict[str, str],
) -> None:
    version = release["version"]
    digest = release["digest"]
    artifact_name = release["artifact"]
    modules = registry.get("modules")
    if not isinstance(modules, list):
        msg = "registry index missing modules list"
        raise ValueError(msg)
    download_url = f"modules/{artifact_name}"
    entry: dict[str, object] | None = next(
        (item for item in modules if isinstance(item, dict) and str(item.get("id") or "").strip() == module_id),
        None,
    )
    if entry is None:
        entry = {"id": module_id}
        modules.append(entry)
    entry["latest_version"] = version
    entry["download_url"] = download_url
    entry["checksum_sha256"] = digest
    for key in ("tier", "publisher", "bundle_dependencies", "description", "core_compatibility"):
        if key in manifest:
            entry[key] = manifest[key]


@beartype
@require(lambda repo_root: repo_root.is_dir(), "repo_root must be an existing directory")
@require(lambda bundle: bool(bundle.strip()), "bundle must be non-empty")
def _sync_one_bundle(repo_root: Path, bundle: str) -> None:
    bundle_dir = _bundle_dir(repo_root, bundle)
    manifest, module_id, version = _load_module_manifest(bundle_dir)
    registry_path, registry = _load_registry_index(repo_root)
    modules_dir, signatures_dir = _prepare_registry_output_dirs(repo_root)
    bundle_name = bundle_dir.name
    artifact_name, digest = _build_registry_tarball_and_digest(bundle_dir, modules_dir, bundle_name, version)
    _maybe_write_tarball_signature(manifest, signatures_dir, bundle_name, version)
    _upsert_registry_module_row(
        registry,
        module_id=module_id,
        manifest=manifest,
        release={"version": version, "digest": digest, "artifact": artifact_name},
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    _emit_line(f"synced registry for {module_id} v{version} ({artifact_name})")


@beartype
@ensure(lambda result: result in {0, 1}, "main must return a process exit code")
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", type=Path, help="Repository root")
    parser.add_argument(
        "--bundle",
        action="append",
        dest="bundles",
        default=[],
        help="Bundle directory name under packages/ (repeatable), e.g. specfact-code-review",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    if not args.bundles:
        parser.error("at least one --bundle is required")
    for bundle in args.bundles:
        _sync_one_bundle(repo_root, bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
