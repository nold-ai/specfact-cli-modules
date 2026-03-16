#!/usr/bin/env python3
"""Validate module publish inputs for specfact-cli-modules."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

import yaml
from packaging.version import InvalidVersion, Version


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


def _emit_line(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{message}\n")


def _fail(message: str) -> int:
    _emit_line(f"ERROR: {message}", error=True)
    return 1


def _warn(message: str) -> None:
    _emit_line(f"WARNING: {message}", error=True)


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be object: {path}")
    return data


def _bundle_dir(repo_root: Path, bundle: str) -> Path:
    bundle_name = bundle.strip()
    if not bundle_name.startswith("specfact-"):
        bundle_name = f"specfact-{bundle_name}"
    path = repo_root / "packages" / bundle_name
    if not path.exists():
        raise FileNotFoundError(f"Bundle directory not found: {path}")
    return path


def _find_registry_entry(registry: dict[str, object], module_name: str) -> dict[str, object] | None:
    modules = registry.get("modules")
    if not isinstance(modules, list):
        return None
    expected_id = f"nold-ai/{module_name}"
    for entry in modules:
        if isinstance(entry, dict) and entry.get("id") == expected_id:
            return entry
    return None


@beartype
@require(lambda argv: argv is None or all(isinstance(arg, str) for arg in argv), "argv must contain strings")
@ensure(lambda result: result in {0, 1}, "main must return a process exit code")
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate module publish preconditions")
    parser.add_argument("--bundle", required=True, help="Bundle name, e.g. specfact-backlog or backlog")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument(
        "--registry-index-path",
        default=None,
        help="Optional explicit registry index path used for version comparison",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    bundle_dir = _bundle_dir(repo_root, args.bundle)
    manifest_path = bundle_dir / "module-package.yaml"
    registry_path = (
        Path(args.registry_index_path).resolve() if args.registry_index_path else repo_root / "registry" / "index.json"
    )

    missing_paths = [path for path in (manifest_path, registry_path) if not path.exists()]
    if missing_paths:
        return _fail(f"Missing required publish input: {missing_paths[0]}")

    manifest = _load_yaml(manifest_path)
    module_name = bundle_dir.name
    manifest_version_raw = manifest.get("version")
    core_compatibility = str(manifest.get("core_compatibility", "")).strip()

    if not manifest_version_raw:
        return _fail("module-package.yaml missing 'version'")

    try:
        manifest_version = Version(str(manifest_version_raw))
    except InvalidVersion as exc:
        return _fail(f"Invalid manifest version '{manifest_version_raw}': {exc}")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = _find_registry_entry(registry, module_name)
    if entry is None:
        _warn(f"No registry entry found for nold-ai/{module_name}; skipping monotonic comparison")
        _emit_line("OK: publish validation passed")
        return 0

    latest_raw = entry.get("latest_version")
    if not latest_raw:
        return _fail(f"Registry entry for nold-ai/{module_name} missing latest_version")

    try:
        latest_version = Version(str(latest_raw))
    except InvalidVersion as exc:
        return _fail(f"Invalid registry latest_version '{latest_raw}': {exc}")

    if manifest_version <= latest_version:
        return _fail(
            f"Bundle version must be greater than registry latest_version: "
            f"manifest={manifest_version} latest={latest_version}"
        )

    if not core_compatibility:
        _warn("core_compatibility is empty; verify compatibility range before publish")
    else:
        _warn(
            "Version bump detected; verify core_compatibility was intentionally reviewed/updated "
            f"(current: '{core_compatibility}')"
        )

    _emit_line("OK: publish validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
