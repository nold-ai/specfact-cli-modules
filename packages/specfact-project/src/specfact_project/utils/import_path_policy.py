"""Shared ignore and discovery policy for code import runtime scans."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from beartype import beartype
from icontract import ensure, require


DEFAULT_IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".specfact",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "env",
    "htmlcov",
    "node_modules",
    "site-packages",
    "venv",
}
DEFAULT_IGNORED_FILE_NAMES = {".DS_Store"}
DEFAULT_IGNORED_FILE_SUFFIXES = {".pyc", ".pyo"}
DEFAULT_IGNORED_SEGMENTS = (".eggs",)
_DEFAULT_SPECFACTIGNORE = Path(".specfact") / ".specfactignore"
_DEFAULT_HEAVY_IGNORED_ENTRY_THRESHOLD = 500
_DEFAULT_LARGE_REPO_FILE_THRESHOLD = 1000


@dataclass(slots=True)
class ImportDiscoveryResult:
    """Filtered discovery result with warning metadata."""

    files: list[Path]
    warnings: list[str]
    ignored_counts: dict[str, int]
    provisional_eta: str | None = None


@dataclass(slots=True, frozen=True)
class ImportDiscoveryOptions:
    """Configuration for runtime discovery scans."""

    extensions: frozenset[str]
    entry_point: Path | None = None
    include_tests: bool = True
    ignore_patterns: tuple[str, ...] = ()
    allow_hidden: bool = False
    heavy_ignored_entry_threshold: int = _DEFAULT_HEAVY_IGNORED_ENTRY_THRESHOLD
    large_repo_file_threshold: int = _DEFAULT_LARGE_REPO_FILE_THRESHOLD
    max_files: int | None = None


@dataclass(slots=True, frozen=True)
class _DiscoveryWalkContext:
    repo_root: Path
    patterns: tuple[str, ...]
    allow_hidden: bool
    explicit_roots: frozenset[Path]
    normalized_extensions: frozenset[str]
    include_tests: bool


def _resolve_entry_point(repo_root: Path, entry_point: Path | None) -> Path:
    if entry_point is None:
        return repo_root
    return entry_point if entry_point.is_absolute() else (repo_root / entry_point).resolve()


def _normalize_glob_pattern(pattern: str) -> str:
    normalized = pattern.strip()
    if not normalized:
        return ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized


def _as_tuple(patterns: Iterable[str]) -> tuple[str, ...]:
    return tuple(patterns)


def _normalize_extensions(extensions: Iterable[str]) -> frozenset[str]:
    return frozenset(ext if ext.startswith(".") else f".{ext}" for ext in extensions)


def _relative_path(path: Path, repo_root: Path) -> Path | None:
    try:
        return path.relative_to(repo_root)
    except ValueError:
        return None


def _explicit_root_set(explicit_roots: Iterable[Path]) -> set[Path]:
    return {root.resolve() for root in explicit_roots if root.exists()}


def _is_explicit_root_path(path: Path, explicit_roots: Iterable[Path]) -> bool:
    resolved_path = path.resolve()
    return any(resolved_path == root or root in resolved_path.parents for root in explicit_roots)


def _contains_ignored_dir(parts: tuple[str, ...]) -> bool:
    return any(part in DEFAULT_IGNORED_DIR_NAMES for part in parts)


def _contains_ignored_segment(relative_path: Path) -> bool:
    return any(segment in relative_path.as_posix() for segment in DEFAULT_IGNORED_SEGMENTS)


def _is_hidden_path(parts: tuple[str, ...], allow_hidden: bool) -> bool:
    if allow_hidden:
        return False
    return any(part.startswith(".") for part in parts if part not in {".", ".."})


def _is_ignored_file(path: Path) -> bool:
    return path.is_file() and (path.name in DEFAULT_IGNORED_FILE_NAMES or path.suffix in DEFAULT_IGNORED_FILE_SUFFIXES)


def _has_glob_metacharacters(pattern: str) -> bool:
    return any(char in pattern for char in "*?[]")


def _matches_dir_pattern(rel_posix: str, pattern: str) -> bool:
    dir_pattern = pattern.rstrip("/")
    return rel_posix == dir_pattern or rel_posix.startswith(f"{dir_pattern}/")


def _matches_simple_pattern(rel_posix: str, pattern: str) -> bool:
    return not _has_glob_metacharacters(pattern) and (rel_posix == pattern or rel_posix.startswith(f"{pattern}/"))


def _matches_ignore_pattern(relative_path: Path, patterns: Iterable[str]) -> bool:
    rel_posix = relative_path.as_posix()
    rel_with_sep = f"{rel_posix}/"
    for pattern in patterns:
        cleaned = _normalize_glob_pattern(pattern)
        if not cleaned:
            continue
        if cleaned.endswith("/") and _matches_dir_pattern(rel_posix, cleaned):
            return True
        if fnmatch(rel_posix, cleaned) or fnmatch(rel_with_sep, f"{cleaned}/"):
            return True
        if _matches_simple_pattern(rel_posix, cleaned):
            return True
    return False


@beartype
@require(lambda repo_root: repo_root.is_dir(), "repo_root must exist")
@ensure(lambda result: isinstance(result, list), "Must return list")
def load_specfactignore_patterns(repo_root: Path, ignore_file: Path | None = None) -> list[str]:
    """Load repo-local ignore patterns from `.specfact/.specfactignore`."""

    path = ignore_file or (repo_root / _DEFAULT_SPECFACTIGNORE)
    if not path.exists():
        return []

    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        normalized = _normalize_glob_pattern(stripped)
        if normalized:
            patterns.append(normalized)
    return patterns


@beartype
@require(lambda repo_root: repo_root.is_dir(), "repo_root must exist")
@ensure(lambda result: isinstance(result, bool), "Must return bool")
def should_ignore_path(
    path: Path,
    repo_root: Path,
    *,
    ignore_patterns: Iterable[str] = (),
    allow_hidden: bool = False,
    explicit_roots: Iterable[Path] = (),
) -> bool:
    """Return True when a file or directory should be excluded from import scans."""

    relative_path = _relative_path(path, repo_root)
    if relative_path is None:
        return True

    explicit_root_set = _explicit_root_set(explicit_roots)
    if explicit_root_set and _is_explicit_root_path(path, explicit_root_set):
        return False

    parts = tuple(relative_path.parts)
    ignored_by_structure = any(
        (
            _contains_ignored_dir(parts),
            _contains_ignored_segment(relative_path),
            _is_hidden_path(parts, allow_hidden),
            _is_ignored_file(path),
        )
    )
    if ignored_by_structure:
        return True
    return _matches_ignore_pattern(relative_path, ignore_patterns)


@beartype
@require(lambda repo_root: repo_root.is_dir(), "repo_root must exist")
@ensure(lambda result: isinstance(result, bool), "Must return bool")
def should_skip_path(
    path: Path,
    repo_root: Path,
    *,
    ignore_patterns: Iterable[str] = (),
    allow_hidden: bool = False,
    explicit_roots: Iterable[Path] = (),
) -> bool:
    """Backward-compatible alias for callers adopting the shared import policy."""

    return should_ignore_path(
        path,
        repo_root,
        ignore_patterns=ignore_patterns,
        allow_hidden=allow_hidden,
        explicit_roots=explicit_roots,
    )


def _count_ignored_entries(path: Path) -> int:
    if not path.exists():
        return 1
    if not path.is_dir():
        return 1
    try:
        with os.scandir(path) as entries:
            count = sum(1 for _ in entries)
    except OSError:
        return 1
    return max(count, 1)


def _record_ignored_count(ignored_counts: dict[str, int], name: str, count: int) -> None:
    ignored_counts[name] = ignored_counts.get(name, 0) + count


def _filter_dirnames(
    current_path: Path,
    dirnames: list[str],
    context: _DiscoveryWalkContext,
    ignored_counts: dict[str, int],
) -> list[str]:
    kept_dirnames: list[str] = []
    for dirname in dirnames:
        child = current_path / dirname
        if should_ignore_path(
            child,
            context.repo_root,
            ignore_patterns=context.patterns,
            allow_hidden=context.allow_hidden,
            explicit_roots=context.explicit_roots,
        ):
            _record_ignored_count(ignored_counts, dirname, _count_ignored_entries(child))
            continue
        kept_dirnames.append(dirname)
    return kept_dirnames


def _should_include_file(file_path: Path, context: _DiscoveryWalkContext) -> bool:
    if file_path.suffix not in context.normalized_extensions:
        return False
    if should_ignore_path(
        file_path,
        context.repo_root,
        ignore_patterns=context.patterns,
        allow_hidden=context.allow_hidden,
        explicit_roots=context.explicit_roots,
    ):
        return False
    return context.include_tests or not _is_test_path(file_path)


def _build_warnings(
    files: list[Path],
    ignored_counts: dict[str, int],
    options: ImportDiscoveryOptions,
) -> list[str]:
    warnings: list[str] = []
    for ignored_name, count in sorted(ignored_counts.items()):
        if count >= options.heavy_ignored_entry_threshold:
            warnings.append(
                f"Ignored heavy artifact tree '{ignored_name}' ({count} matching entries) to avoid inflated import duration."
            )
    if len(files) >= options.large_repo_file_threshold:
        warnings.append(
            "Repository size may materially extend import duration; remaining time is derived from live processed work."
        )
    return warnings


def _build_provisional_eta(files: list[Path]) -> str | None:
    count = len(files)
    if count == 0:
        return None
    if count < 50:
        return "less than a minute"
    minutes = max(1, count // 200)
    return f"{minutes} minute(s)"


def _finalize_discovery(
    files: list[Path],
    ignored_counts: dict[str, int],
    options: ImportDiscoveryOptions,
) -> ImportDiscoveryResult:
    files.sort()
    warnings = _build_warnings(files, ignored_counts, options)
    return ImportDiscoveryResult(
        files=files,
        warnings=warnings,
        ignored_counts=ignored_counts,
        provisional_eta=_build_provisional_eta(files),
    )


def _process_candidate_file(
    file_path: Path,
    *,
    context: _DiscoveryWalkContext,
    ignored_counts: dict[str, int],
    files: list[Path],
    filename: str,
) -> bool:
    if not _should_include_file(file_path, context):
        if file_path.suffix in context.normalized_extensions:
            _record_ignored_count(ignored_counts, filename, 1)
        return False
    files.append(file_path)
    return True


@beartype
@require(lambda repo_root: repo_root.is_dir(), "repo_root must exist")
@ensure(lambda result: isinstance(result, ImportDiscoveryResult), "Must return ImportDiscoveryResult")
def _discover_code_files_with_options(repo_root: Path, options: ImportDiscoveryOptions) -> ImportDiscoveryResult:
    """Discover source files while pruning ignored directories before traversal."""

    resolved_repo_root = repo_root.resolve()
    root = _resolve_entry_point(resolved_repo_root, options.entry_point).resolve()
    patterns = options.ignore_patterns or _as_tuple(load_specfactignore_patterns(resolved_repo_root))
    context = _DiscoveryWalkContext(
        repo_root=resolved_repo_root,
        patterns=patterns,
        allow_hidden=options.allow_hidden,
        explicit_roots=frozenset(_explicit_root_set((root,) if options.entry_point is not None else ())),
        normalized_extensions=_normalize_extensions(options.extensions),
        include_tests=options.include_tests,
    )

    files: list[Path] = []
    ignored_counts: dict[str, int] = {}

    for current_dir, dirnames, filenames in os.walk(root):
        current_path = Path(current_dir)
        dirnames[:] = _filter_dirnames(current_path, dirnames, context, ignored_counts)

        for filename in filenames:
            file_path = current_path / filename
            included = _process_candidate_file(
                file_path,
                context=context,
                ignored_counts=ignored_counts,
                files=files,
                filename=filename,
            )
            if included and options.max_files is not None and len(files) >= options.max_files:
                return _finalize_discovery(files, ignored_counts, options)

    return _finalize_discovery(files, ignored_counts, options)


@beartype
@require(lambda repo_root: repo_root.is_dir(), "repo_root must exist")
@ensure(lambda result: isinstance(result, ImportDiscoveryResult), "Must return ImportDiscoveryResult")
def discover_code_files(
    repo_root: Path,
    options: ImportDiscoveryOptions | None = None,
    **kwargs: object,
) -> ImportDiscoveryResult:
    """Discover source files while pruning ignored directories before traversal."""
    if options is None:
        options = ImportDiscoveryOptions(
            extensions=_normalize_extensions(kwargs.pop("extensions", ())),
            entry_point=kwargs.pop("entry_point", None),
            include_tests=bool(kwargs.pop("include_tests", True)),
            ignore_patterns=_as_tuple(kwargs.pop("ignore_patterns", ()) or ()),
            allow_hidden=bool(kwargs.pop("allow_hidden", False)),
            heavy_ignored_entry_threshold=int(
                kwargs.pop("heavy_ignored_entry_threshold", _DEFAULT_HEAVY_IGNORED_ENTRY_THRESHOLD)
            ),
            large_repo_file_threshold=int(kwargs.pop("large_repo_file_threshold", _DEFAULT_LARGE_REPO_FILE_THRESHOLD)),
            max_files=kwargs.pop("max_files", None),
        )
    elif kwargs:
        unexpected = ", ".join(sorted(str(key) for key in kwargs))
        raise TypeError(f"Unexpected discovery keyword overrides with options object: {unexpected}")
    return _discover_code_files_with_options(
        repo_root,
        options,
    )


def _is_test_path(file_path: Path) -> bool:
    name = file_path.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return any(part in {"test", "tests", "spec"} for part in file_path.parts)
