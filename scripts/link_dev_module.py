"""Prepare a live module source tree for workspace runtime validation."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml
from beartype import beartype
from icontract import ensure, require


MANIFEST_NAMES = ("module-package.yaml", "metadata.yaml")
IGNORED_RUNTIME_FILES = {".specfact-registry-id", ".specfact-install-verified-checksum"}


def _emit_line(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{message}\n")


def _resolve_source_dir(module_name: str, source_dir: Path | None) -> Path:
    if source_dir is not None:
        return source_dir.resolve()
    return (Path("packages") / module_name).resolve()


def _resolve_manifest_path(source_dir: Path) -> Path:
    for manifest_name in MANIFEST_NAMES:
        candidate = source_dir / manifest_name
        if candidate.exists():
            return candidate
    raise ValueError(f"No module manifest found under {source_dir}")


def _shadow_manifest_payload(source_manifest: Path) -> dict[str, object]:
    raw = yaml.safe_load(source_manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Manifest root must be a mapping: {source_manifest}")
    payload = dict(raw)
    payload.pop("integrity", None)
    return payload


def _replace_target(target_dir: Path, force: bool) -> None:
    if not target_dir.exists() and not target_dir.is_symlink():
        return
    if not force:
        raise ValueError(f"Target already exists: {target_dir} (re-run with --force to replace it)")
    if target_dir.is_symlink() or target_dir.is_file():
        target_dir.unlink()
        return
    shutil.rmtree(target_dir)


@beartype
@require(lambda module_name: bool(module_name.strip()), "module_name must not be empty")
@ensure(lambda result: result.is_dir(), "shadow module directory must exist")
def link_dev_module(
    module_name: str,
    *,
    source_dir: Path | None = None,
    shadow_root: Path | None = None,
    force: bool = False,
) -> Path:
    """Create a runtime-validation shadow module with symlinked live content."""
    resolved_source = _resolve_source_dir(module_name, source_dir)
    if not resolved_source.is_dir():
        raise ValueError(f"Module source directory not found: {resolved_source}")

    source_manifest = _resolve_manifest_path(resolved_source)
    effective_shadow_root = (shadow_root or Path.cwd() / ".specfact" / "modules").resolve()
    target_dir = effective_shadow_root / module_name

    _replace_target(target_dir, force)
    target_dir.mkdir(parents=True, exist_ok=True)

    for child in sorted(resolved_source.iterdir()):
        if child.name in MANIFEST_NAMES or child.name in IGNORED_RUNTIME_FILES:
            continue
        (target_dir / child.name).symlink_to(child.resolve(), target_is_directory=child.is_dir())

    manifest_payload = _shadow_manifest_payload(source_manifest)
    manifest_name = source_manifest.name
    (target_dir / manifest_name).write_text(
        yaml.safe_dump(manifest_payload, sort_keys=False),
        encoding="utf-8",
    )
    return target_dir


@beartype
@ensure(lambda result: result in {0, 1}, "main must return a process exit code")
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module_name", help="Module directory name, e.g. specfact-code-review")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Optional source directory override (default: packages/<module-name>)",
    )
    parser.add_argument(
        "--shadow-root",
        type=Path,
        default=None,
        help="Optional shadow root override (default: <cwd>/.specfact/modules)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace any existing shadow module at the target location.",
    )
    args = parser.parse_args(argv)

    try:
        target_dir = link_dev_module(
            args.module_name,
            source_dir=args.source_dir,
            shadow_root=args.shadow_root,
            force=args.force,
        )
    except ValueError as exc:
        _emit_line(f"ERROR: {exc}", error=True)
        return 1

    _emit_line(f"Linked dev module '{args.module_name}' -> {target_dir}")
    _emit_line("Use SPECFACT_ALLOW_UNSIGNED=1 for runtime validation with the shadow module.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
