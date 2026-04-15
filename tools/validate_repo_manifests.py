#!/usr/bin/env python3
"""Validate bundle manifests and registry JSON in specfact-cli-modules.

Registry ``latest_version`` describes the last **published** row in git. A package
``module-package.yaml`` may use a **higher** semver (ahead of publish); that is allowed so local
and PR work does not rewrite ``registry/`` before ``publish-modules`` runs on ``dev``/``main``.
"""

from __future__ import annotations

import json
import re
import sys
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


ROOT = Path(__file__).resolve().parent.parent


def _emit_line(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{message}\n")


REQUIRED_KEYS = {"name", "version", "tier", "publisher", "description", "bundle_group_command"}


def _validate_yaml(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    found_keys = {match.group("key") for match in re.finditer(r"(?m)^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:", text)}
    missing = sorted(REQUIRED_KEYS - found_keys)
    if missing:
        errors.append(f"{path}: missing keys: {', '.join(missing)}")
    return errors


def _validate_registry(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]

    if not isinstance(data, dict):
        return [f"{path}: registry root must be an object"]
    if "modules" not in data or not isinstance(data["modules"], list):
        return [f"{path}: expected 'modules' list"]
    return []


def _sha256_from_sidecar(text: str) -> str:
    first = text.strip().splitlines()[0].strip()
    return first.split()[0].strip().lower()


def _parse_registry_module_fields(mod: dict) -> tuple[str, str, str, str] | list[str]:
    module_id = str(mod.get("id") or "").strip()
    latest_version = str(mod.get("latest_version") or "").strip()
    checksum = str(mod.get("checksum_sha256") or "").strip().lower()
    download_url = str(mod.get("download_url") or "").strip()
    if not module_id or not latest_version or not checksum or not download_url:
        return ["missing id, latest_version, checksum_sha256, or download_url"]
    return (module_id, latest_version, checksum, download_url)


def _validate_registry_download_url(label: str, module_id: str, latest_version: str, download_url: str) -> list[str]:
    if not download_url.startswith("modules/") or not download_url.endswith(".tar.gz"):
        return [
            f"{label}: download_url {download_url!r} must look like modules/<bundle>-<version>.tar.gz",
        ]
    slug = module_id.rsplit("/", maxsplit=1)[-1]
    expected_url = f"modules/{slug}-{latest_version}.tar.gz"
    if download_url != expected_url:
        return [f"{label}: download_url {download_url!r} must match expected pattern {expected_url!r}"]
    return []


def _validate_registry_sidecar(root: Path, label: str, download_url: str, checksum: str) -> list[str]:
    sidecar = root / "registry" / f"{download_url}.sha256"
    if not sidecar.is_file():
        return [f"{label}: missing checksum sidecar {sidecar}"]
    try:
        got = _sha256_from_sidecar(sidecar.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"{label}: cannot read sidecar {sidecar} ({exc})"]
    if got != checksum:
        return [f"{label}: checksum_sha256 {checksum!r} does not match sidecar {sidecar} ({got!r})"]
    return []


def _semver_triplet(version: str) -> tuple[int, int, int] | None:
    parts = version.strip().split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _manifest_registry_version_relation(manifest_version: str, registry_version: str) -> str:
    """Return ``eq`` | ``gt`` | ``lt`` | ``unknown`` (non-comparable semver triplets)."""
    mt = _semver_triplet(manifest_version)
    rt = _semver_triplet(registry_version)
    if mt is not None and rt is not None:
        if mt < rt:
            return "lt"
        if mt > rt:
            return "gt"
        return "eq"
    if manifest_version == registry_version:
        return "eq"
    return "unknown"


def _validate_registry_manifest_alignment(
    root: Path, label: str, slug: str, module_id: str, latest_version: str
) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "packages" / slug / "module-package.yaml"
    if not manifest_path.is_file():
        return [f"{label}: expected package manifest {manifest_path}"]
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return [f"{label}: cannot parse {manifest_path} ({exc})"]
    if not isinstance(raw, dict):
        return [f"{label}: {manifest_path} must parse to a mapping"]

    manifest_name = str(raw.get("name") or "").strip()
    if manifest_name != module_id:
        errors.append(f"{label}: {manifest_path} name {manifest_name!r} does not match registry id {module_id!r}")

    manifest_version = str(raw.get("version") or "").strip()
    relation = _manifest_registry_version_relation(manifest_version, latest_version)
    if relation == "lt":
        errors.append(
            f"{label}: {manifest_path} version {manifest_version!r} is behind "
            f"registry latest_version {latest_version!r}"
        )
    elif relation == "unknown":
        errors.append(
            f"{label}: {manifest_path} version {manifest_version!r} does not match "
            f"registry latest_version {latest_version!r} (expected semver x.y.z for both or exact match)"
        )
    # ``gt``: manifest is ahead of the published registry row — normal between publish runs; CI
    # (`publish-modules`) updates registry + artifacts. Do not require local registry edits here.

    return errors


def _registry_module_consistency_errors(root: Path, label: str, mod: dict) -> list[str]:
    """Return errors for one registry module dict, or an empty list when checks pass."""
    parsed = _parse_registry_module_fields(mod)
    if isinstance(parsed, list):
        return [f"{label}: {parsed[0]}"]

    module_id, latest_version, checksum, download_url = parsed
    errors = _validate_registry_download_url(label, module_id, latest_version, download_url)
    if errors:
        return errors

    slug = module_id.rsplit("/", maxsplit=1)[-1]
    errors = _validate_registry_sidecar(root, label, download_url, checksum)
    if errors:
        return errors

    return _validate_registry_manifest_alignment(root, label, slug, module_id, latest_version)


@beartype
@require(lambda root: root.is_dir(), "root must be a directory")
@require(lambda registry_path: registry_path.is_file(), "registry_path must be a file")
def validate_registry_consistency(root: Path, registry_path: Path) -> list[str]:
    """Cross-check registry/index.json against tarball sidecars and package manifests."""
    errors: list[str] = []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{registry_path}: cannot load registry for consistency check ({exc})"]

    modules = data.get("modules")
    if not isinstance(modules, list):
        return errors

    for idx, mod in enumerate(modules):
        if not isinstance(mod, dict):
            errors.append(f"{registry_path}: modules[{idx}] must be an object")
            continue
        label = f"{registry_path}: module {str(mod.get('id') or '').strip()!r}"
        errors.extend(_registry_module_consistency_errors(root, label, mod))

    return errors


@beartype
@require(lambda registry_path: registry_path.is_file(), "registry_path must be a file")
def registry_module_ids(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    modules = data.get("modules")
    if not isinstance(modules, list):
        return set()
    return {str(m["id"]).strip() for m in modules if isinstance(m, dict) and str(m.get("id") or "").strip()}


@beartype
@require(lambda manifest_path: manifest_path.is_file(), "manifest_path must be a file")
@require(lambda registry_ids: isinstance(registry_ids, set), "registry_ids must be a set")
def validate_manifest_bundle_dependency_refs(manifest_path: Path, registry_ids: set[str]) -> list[str]:
    """Ensure each bundle_dependencies entry targets a module id present in registry/index.json."""
    errors: list[str] = []
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return [f"{manifest_path}: cannot parse YAML for bundle_dependencies check ({exc})"]
    if not isinstance(raw, dict):
        return []
    deps = raw.get("bundle_dependencies")
    if deps is None:
        return []
    if not isinstance(deps, list):
        return [f"{manifest_path}: bundle_dependencies must be a list when present"]
    for dep in deps:
        dep_id = str(dep).strip()
        if not dep_id:
            continue
        if dep_id not in registry_ids:
            errors.append(
                f"{manifest_path}: bundle_dependencies references unknown module id {dep_id!r} "
                f"(no matching entry in registry/index.json)"
            )
    return errors


@beartype
@ensure(lambda result: result in {0, 1}, "main must return a process exit code")
def main() -> int:
    manifest_paths = sorted(ROOT.glob("packages/*/module-package.yaml"))
    errors: list[str] = []

    registry_path = ROOT / "registry" / "index.json"
    errors.extend(_validate_registry(registry_path))
    if not errors:
        errors.extend(validate_registry_consistency(ROOT, registry_path))

    registry_ids: set[str] | None = None
    if not errors:
        try:
            registry_ids = registry_module_ids(registry_path)
        except (json.JSONDecodeError, OSError, TypeError, KeyError) as exc:
            errors.append(f"{registry_path}: cannot load module ids ({exc})")

    for manifest in manifest_paths:
        errors.extend(_validate_yaml(manifest))
        if registry_ids is not None:
            errors.extend(validate_manifest_bundle_dependency_refs(manifest, registry_ids))

    if errors:
        _emit_line("Manifest/registry validation failed:")
        for err in errors:
            _emit_line(f"- {err}")
        return 1

    _emit_line(f"Validated {len(manifest_paths)} manifests and registry/index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
