"""Shared helpers for resolving packaged project-bundle Jinja templates."""

from __future__ import annotations

from pathlib import Path

from beartype import beartype
from icontract import ensure, require


def _candidate_template_roots() -> tuple[Path, ...]:
    package_root = Path(__file__).parent.parent
    return (
        package_root / "resources" / "templates",
        package_root.parent.parent / "resources" / "templates",
    )


def _target(root: Path, subdir: str | None) -> Path:
    return root / subdir if subdir else root


def _matches_required_glob(path: Path, required_glob: str | None) -> bool:
    return path.exists() and (required_glob is None or any(path.glob(required_glob)))


@beartype
@require(
    lambda templates_dir: templates_dir is None or isinstance(templates_dir, Path), "templates_dir must be Path or None"
)
@ensure(lambda result: isinstance(result, Path), "must resolve to a Path")
def resolve_project_templates_dir(
    templates_dir: Path | None = None,
    *,
    subdir: str | None = None,
    required_glob: str | None = None,
) -> Path:
    """Return the preferred project-bundle templates directory."""
    if templates_dir is not None:
        return Path(templates_dir)

    roots = _candidate_template_roots()
    for root in roots:
        candidate = _target(root, subdir)
        if _matches_required_glob(candidate, required_glob):
            return candidate

    checked = ", ".join(str(_target(r, subdir)) for r in roots)
    raise RuntimeError(
        f"No packaged template root matched required_glob={required_glob!r}; "
        f"candidates (after subdir={subdir!r}): {checked}"
    )


@beartype
@require(
    lambda templates_dir: templates_dir is None or isinstance(templates_dir, Path), "templates_dir must be Path or None"
)
@ensure(lambda result: isinstance(result, Path), "must resolve to a Path")
def resolve_templates_dir(
    templates_dir: Path | None = None,
    subdir: str | None = None,
    required_glob: str | None = None,
) -> Path:
    """Backward-compatible alias for project template resolution."""
    return resolve_project_templates_dir(templates_dir=templates_dir, subdir=subdir, required_glob=required_glob)


@beartype
@require(
    lambda templates_dir: templates_dir is None or isinstance(templates_dir, Path), "templates_dir must be Path or None"
)
@ensure(lambda result: isinstance(result, Path), "must resolve to a Path")
def resolve_runtime_template_dir(templates_dir: Path | None = None) -> Path:
    """Backward-compatible alias for runtime template resolution."""
    return resolve_project_templates_dir(templates_dir=templates_dir)
