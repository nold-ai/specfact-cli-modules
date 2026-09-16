"""Attribute measured installed code only to byte-identical, metadata-owned source."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from icontract import ensure


@dataclass(frozen=True)
class InstalledSource:
    """A controller-verified correspondence, never a worker-supplied alias."""

    source: Path
    installed: Path
    digest: str
    distribution: str


@dataclass(frozen=True)
class CoverageBridge:
    """Allowed measurement roots and independently verifiable source correspondences."""

    directories: tuple[Path, ...]
    mappings: tuple[InstalledSource, ...]
    diagnostics: dict[str, str]
    candidates: dict[str, tuple[str, ...]]
    measured_origins: tuple[str, ...] = ()


@dataclass(frozen=True)
class DistributionRecord:
    """Read-only distribution ownership derived from sealed installation metadata."""

    name: str
    local: bool
    files: dict[str, str]
    error: str = ""


def _regular(path: Path, root: Path) -> bool:
    return (
        path.is_file()
        and not path.is_symlink()
        and path.resolve().is_relative_to(root.resolve())
        and path.stat().st_nlink == 1
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_origin(metadata: Path) -> bool:
    document = json.loads((metadata / "direct_url.json").read_text(encoding="utf-8"))
    url = urlsplit(document.get("url", ""))
    return (
        url.scheme == "file"
        and not url.netloc
        and unquote(url.path).rstrip("/") == "/opt/specfact/output/project"
        and not document.get("dir_info", {}).get("editable", False)
    )


def _record_row(row: list[str], files: dict[str, str]) -> None:
    """Retain only canonical Python ownership entries from one RECORD row."""
    if len(row) != 3:
        raise ValueError("malformed RECORD row")
    relative = PurePosixPath(row[0])
    if relative.as_posix() != row[0]:
        raise ValueError("noncanonical RECORD path")
    if relative.suffix != ".py":
        return  # Wheels also legitimately own ../bin entry points, not coverage source.
    if relative.is_absolute() or ".." in relative.parts or "\\" in row[0]:
        raise ValueError("unsafe Python RECORD path")
    if row[0] in files:
        raise ValueError("duplicate Python RECORD path")
    files[row[0]] = row[1]


def _record(metadata: Path) -> DistributionRecord:
    files: dict[str, str] = {}
    error = ""
    try:
        local = _local_origin(metadata)
    except (OSError, ValueError, TypeError, AttributeError):
        local = False
    try:
        with (metadata / "RECORD").open(newline="", encoding="utf-8") as stream:
            for row in csv.reader(stream):
                _record_row(row, files)
    except (OSError, ValueError, csv.Error) as exc:
        error = str(exc)
    return DistributionRecord(metadata.name, local, files, error)


def _verified_record(path: Path, encoded: str, site: Path) -> bool:
    if not _regular(path, site):
        return False
    algorithm, separator, value = encoded.partition("=")
    if not separator or algorithm not in {"sha256", "sha384", "sha512"}:
        return False
    actual = hashlib.new(algorithm, path.read_bytes()).digest()
    return base64.urlsafe_b64encode(actual).decode().rstrip("=") == value


def _snapshot_index(snapshot: Path) -> dict[str, list[Path]]:
    """Walk the snapshot once, retaining duplicates for fail-closed correspondence."""
    indexed: dict[str, list[Path]] = {}
    for directory, directories, files in os.walk(snapshot, followlinks=False):
        directories[:] = [
            name
            for name in directories
            if name not in {".git", ".venv", "venv", "__pycache__"}
            and not (Path(directory) / name).is_symlink()
            and not (Path(directory) / name / "pyvenv.cfg").is_file()
        ]
        for name in files:
            if name.endswith(".py"):
                indexed.setdefault(name, []).append(Path(directory) / name)
    return indexed


def _source_candidates(snapshot: Path, relative: str, index: dict[str, list[Path]]) -> list[Path]:
    """Require an entire recorded package path, never a basename-only match."""
    if len(PurePosixPath(relative).parts) < 2:
        candidate = snapshot / relative
        return [candidate] if candidate.is_file() else []
    return [
        candidate
        for candidate in index.get(PurePosixPath(relative).name, [])
        if candidate.relative_to(snapshot).as_posix().endswith("/" + relative) or candidate == snapshot / relative
    ]


def _owned_directory(
    installed: Path, site: Path, record: DistributionRecord, owners: dict[str, list[str]]
) -> Path | None:
    """Choose the smallest native coverage directory without foreign Python owners."""
    directory = installed.parent
    if directory == site:
        return None
    for candidate in directory.rglob("*.py"):
        relative = candidate.relative_to(site).as_posix()
        if owners.get(relative) != [record.name] or not _verified_record(candidate, record.files[relative], site):
            return None
    return directory


@dataclass
class _CoverageContext:
    """Indexes shared by source planning within one immutable runtime attachment."""

    snapshot: Path
    site: Path
    owners: dict[str, list[str]]
    sources: dict[str, list[Path]]
    directories: dict[tuple[Path, str], Path | None]


def _source_identity_error(source: Path, relative: str, record: DistributionRecord, context: _CoverageContext) -> str:
    installed = context.site / relative
    if context.owners.get(relative) != [record.name]:
        return "ambiguous_distribution_ownership"
    if _source_candidates(context.snapshot, relative, context.sources) != [source]:
        return "ambiguous_snapshot_source"
    if not _regular(source, context.snapshot) or not _verified_record(installed, record.files[relative], context.site):
        return "invalid_record_content"
    if _digest(source) != _digest(installed):
        return "installed_source_differs"
    return ""


def _source_mapping(
    source: Path, record: DistributionRecord, context: _CoverageContext
) -> tuple[InstalledSource | None, Path | None, str]:
    matches = [relative for relative in record.files if source.as_posix().endswith("/" + relative)]
    if not matches:
        return None, None, ""
    if record.error or len(matches) != 1:
        return None, None, "invalid_distribution_record"
    relative = matches[0]
    if error := _source_identity_error(source, relative, record, context):
        return None, None, error
    installed = context.site / relative
    cache_key = (installed.parent, record.name)
    if cache_key not in context.directories:
        context.directories[cache_key] = _owned_directory(installed, context.site, record, context.owners)
    directory = context.directories[cache_key]
    if directory is None:
        return None, None, "coverage_directory_ownership_unavailable"
    return InstalledSource(source, installed, _digest(source), record.name), directory, ""


def _distribution_context(snapshot: Path, site: Path) -> tuple[list[DistributionRecord], _CoverageContext]:
    records = [_record(path) for path in sorted(site.glob("*.dist-info")) if path.is_dir() and not path.is_symlink()]
    owners: dict[str, list[str]] = {}
    for record in records:
        for relative in record.files:
            owners.setdefault(relative, []).append(record.name)
    local = [record for record in records if record.local]
    index = _snapshot_index(snapshot) if local else {}
    return local, _CoverageContext(snapshot, site, owners, index, {})


def _candidate_paths(source: Path, records: list[DistributionRecord], site: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(site / relative)
                for record in records
                for relative in record.files
                if source.as_posix().endswith("/" + relative)
            }
        )
    )


def _measured_origins(records: list[DistributionRecord], site: Path, directories: set[Path]) -> tuple[str, ...]:
    """Retain every measured owned origin, including generated or renamed packages."""
    return tuple(
        sorted(
            {
                str(site / relative)
                for record in records
                for relative in record.files
                if any(parent in directories for parent in (site / relative).parents)
            }
        )
    )


@ensure(lambda result, files: {row.source for row in result.mappings} <= {file.resolve() for file in files})
def plan_installed_coverage(files: list[Path], *, snapshot: Path, site_packages: Path) -> CoverageBridge:
    """Read sealed metadata without importing packages or changing native import paths."""
    snapshot, site = snapshot.resolve(), site_packages.resolve()
    records, context = _distribution_context(snapshot, site)
    sources = {file.resolve() for file in files if file.suffix == ".py"}
    mappings, directories, diagnostics = [], set(), {}
    for source in sorted(sources):
        if not source.is_relative_to(snapshot):
            continue
        for record in records:
            mapping, directory, error = _source_mapping(source, record, context)
            if error:
                diagnostics[str(source)] = error
            if mapping is not None and directory is not None:
                mappings.append(mapping)
                directories.add(directory)
    candidates = {str(source): _candidate_paths(source, records, site) for source in sources}
    return CoverageBridge(
        tuple(sorted(directories)),
        tuple(mappings),
        diagnostics,
        candidates,
        _measured_origins(records, site, directories),
    )


def _coverage_index(rows: dict[str, Any], snapshot: Path) -> dict[Path, list[tuple[str, Any]]]:
    """Resolve each measured name once while retaining ambiguous aliases."""
    indexed: dict[Path, list[tuple[str, Any]]] = {}
    for name, row in rows.items():
        indexed.setdefault((snapshot / name).resolve(), []).append((name, row))
    return indexed


def _executed(rows: list[tuple[str, Any]]) -> bool:
    """Coverage may enumerate unexecuted source files; rows alone prove no execution."""
    return any(isinstance(row.get("executed_lines"), list) and row["executed_lines"] for _, row in rows)


def _coverage_rows(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("files", {})
    if not isinstance(rows, dict) or not all(
        isinstance(name, str) and isinstance(row, dict) for name, row in rows.items()
    ):
        raise ValueError("invalid_installed_coverage_rows")
    return rows


def _coverage_alias(
    mapping: InstalledSource, indexed: dict[Path, list[tuple[str, Any]]], snapshot: Path
) -> tuple[Any, str]:
    if (
        not _regular(mapping.source, snapshot)
        or not _regular(mapping.installed, mapping.installed.parent)
        or _digest(mapping.source) != mapping.digest
        or _digest(mapping.installed) != mapping.digest
    ):
        return None, "source_identity_changed_after_execution"
    if _executed(indexed.get(mapping.source, [])):
        return None, ""
    measured = indexed.get(mapping.installed, [])
    if len(measured) != 1:
        return None, "installed_coverage_missing_or_ambiguous"
    return measured[0][1], ""


def _origin_diagnostics(
    diagnostics: dict[str, str],
    bridge: CoverageBridge,
    indexed: dict[Path, list[tuple[str, Any]]],
    relocations: dict[str, str] | None,
    snapshot: Path,
) -> dict[str, str]:
    retained = {}
    for source, error in diagnostics.items():
        if not _executed(indexed.get(Path(source), [])):
            retained[source] = error
            continue
        candidates = bridge.candidates.get(source, ())
        if relocations is None or any(path not in relocations for path in candidates):
            retained[source] = error + ":coverage_origin_unavailable"
        elif any((snapshot / relocations[path]).resolve() == Path(source) for path in candidates):
            retained[source] = error + ":coverage_alias_origin_ambiguous"
    return retained


def _unverified_origins(bridge: CoverageBridge, relocations: dict[str, str], snapshot: Path) -> set[tuple[Path, Path]]:
    """Separate native relocation claims from independently verified source identities."""
    verified = {(mapping.installed, mapping.source) for mapping in bridge.mappings}
    observed = {(Path(origin), (snapshot / relocations[origin]).resolve()) for origin in bridge.measured_origins}
    return observed - verified


def _unverified_aliases(
    bridge: CoverageBridge,
    indexed: dict[Path, list[tuple[str, Any]]],
    relocations: dict[str, str] | None,
    snapshot: Path,
) -> dict[str, str]:
    """Native renamed paths cannot bypass controller source correspondence checks."""
    if not bridge.measured_origins:
        return {}
    relocations = relocations or {}
    executed = {Path(source) for source in bridge.candidates if _executed(indexed.get(Path(source), []))}
    if any(origin not in relocations for origin in bridge.measured_origins):
        return {str(source): "coverage_origin_unavailable" for source in executed}
    return {
        str(destination): "coverage_alias_origin_unverified"
        for _origin, destination in _unverified_origins(bridge, relocations, snapshot)
        if destination in executed
    }


@ensure(
    lambda result, bridge, payload: (
        set(result[0]["files"]) <= set(payload.get("files", {})) | {str(row.source) for row in bridge.mappings}
    )
)
def attribute_installed_coverage(
    bridge: CoverageBridge, payload: dict[str, Any], *, snapshot: Path, relocations: dict[str, str] | None = None
) -> tuple[dict[str, Any], dict[str, str]]:
    """Create an evaluation copy; retain the raw measured paths and percentages."""
    rows = _coverage_rows(payload)
    indexed = _coverage_index(rows, snapshot)
    attributed = dict(rows)
    diagnostics = _origin_diagnostics(dict(bridge.diagnostics), bridge, indexed, relocations, snapshot)
    for source, error in _unverified_aliases(bridge, indexed, relocations, snapshot).items():
        diagnostics.setdefault(source, error)
    for mapping in bridge.mappings:
        row, error = _coverage_alias(mapping, indexed, snapshot)
        if error:
            diagnostics[str(mapping.source)] = error
        if row is not None:
            for name, _original in indexed.get(mapping.source, []):
                attributed.pop(name, None)
            attributed[str(mapping.source)] = row
    return {**payload, "files": attributed}, diagnostics
