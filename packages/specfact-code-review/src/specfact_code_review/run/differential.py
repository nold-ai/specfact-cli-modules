"""Canonical C14 finding locations and differential lifecycle classification."""

from __future__ import annotations

import hashlib
import io
import json
import re
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Literal

from icontract import ensure, require


@dataclass(frozen=True)
class SourceSpan:
    """UTF-8-byte, one-based-line, half-open source location."""

    kind: Literal["source_span"]
    schema: Literal["source-span-v1"]
    path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    precision: Literal["exact", "line"]
    coordinate_system: str


@dataclass(frozen=True)
class LocatedFinding:
    analyzer: str
    location: SourceSpan


@dataclass(frozen=True)
class ContinuityResult:
    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""


@dataclass(frozen=True)
class DifferentialSnapshotSelection:
    baseline_commit: str
    target_tip_commit: str
    head_commit: str


@dataclass(frozen=True)
class DifferentialFinding:
    analyzer: str
    rule: str
    severity: str
    path: str
    line: int
    message: str
    blocking: bool


@dataclass(frozen=True)
class DifferentialClassification:
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    introduced: tuple[DifferentialFinding, ...]
    fixed: tuple[DifferentialFinding, ...]
    unchanged: tuple[DifferentialFinding, ...]
    unknown: tuple[DifferentialFinding, ...]
    evidence_digest: str
    reason: str = ""
    correspondence_evidence: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class FindingClassificationRequest:
    base_findings: list[dict[str, Any]]
    head_findings: list[dict[str, Any]]
    base_sources: dict[str, bytes]
    head_sources: dict[str, bytes]
    base_analysis_status: str = "pass"
    rename_facts: dict[str, str] | None = None
    rename_ambiguities: dict[str, list[str]] | None = None
    deleted_paths: tuple[str, ...] = ()
    added_paths: tuple[str, ...] = ()
    source_size_override: int | None = None
    changed_lines: dict[str, set[int]] | None = None


@dataclass
class _ClassificationState:
    introduced: list[DifferentialFinding]
    fixed: list[DifferentialFinding]
    unchanged: list[DifferentialFinding]
    unknown: list[DifferentialFinding]
    correspondence_evidence: list[dict[str, object]]
    correspondence_matrices: dict[tuple[bytes, bytes], tuple[list[list[int]], list[list[int]]]] = field(
        default_factory=dict
    )
    forbidden_costs: dict[tuple[bytes, bytes, int, int], int] = field(default_factory=dict)


@dataclass(frozen=True)
class _ContinuityContext:
    base_lines: list[bytes]
    head_lines: list[bytes]
    base_index: int
    head_index: int
    cells: int


@dataclass(frozen=True)
class _SuppressionDeltaContext:
    base_by_key: dict[tuple[str, int, str, str], SuppressionOccurrence]
    head_by_key: dict[tuple[str, int, str, str], SuppressionOccurrence]
    base_sources: dict[str, bytes]
    head_sources: dict[str, bytes]
    renames: dict[str, str]
    base_manifest_digest: str
    head_manifest_digest: str


@dataclass(frozen=True)
class ExactRenameFacts:
    pairs: tuple[tuple[str, str], ...]
    ambiguities: tuple[str, ...]
    algorithm: Literal["canonical-exact-rename-v1"] = "canonical-exact-rename-v1"


@dataclass(frozen=True)
class SuppressionOccurrence:
    path: str
    line: int
    family: str
    kind: str
    token: str


@dataclass(frozen=True)
class SuppressionEvidence:
    changed_hunk_digest: str = ""
    analyzers: tuple[str, ...] = ()
    family: str = ""
    base_blob_digest: str = ""
    head_blob_digest: str = ""
    occurrence_digest: str = ""
    base_manifest_digest: str = ""
    head_manifest_digest: str = ""


@dataclass(frozen=True)
class SuppressionFinding:
    kind: str
    path: str
    line: int
    blocking: bool
    evidence: SuppressionEvidence = SuppressionEvidence()


@dataclass(frozen=True)
class SuppressionClassification:
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    findings: tuple[SuppressionFinding, ...] = ()
    introduced: tuple[SuppressionOccurrence, ...] = ()
    unchanged: tuple[SuppressionOccurrence, ...] = ()
    missing_base_disposition: str = "ordinary"
    reason: str = ""


@dataclass(frozen=True)
class SuppressionCatalogResource:
    digest: str
    canonical_bytes: bytes


@dataclass(frozen=True)
class SuppressionCatalogContract:
    digest: str
    canonical_bytes: bytes


@dataclass(frozen=True)
class C14Checkpoint:
    suppression_catalog_contract: SuppressionCatalogContract


@dataclass(frozen=True)
class CatalogActivation:
    status: Literal["PASS", "UNKNOWN"]
    profile_activated: bool


class UnsupportedWaiverInput(ValueError):  # noqa: N818 - frozen public C14 contract name
    """Raised because C14 has no authenticated suppression-waiver input."""


def _physical_lines(source: bytes) -> list[bytes]:
    return source.splitlines()


@require(lambda line: line >= 1, "line numbers are one-based")
def line_fallback_location(path: str, source: bytes, *, line: int) -> SourceSpan:
    """Return a deterministic whole-physical-line fallback span."""

    lines = _physical_lines(source)
    payload = lines[line - 1] if line <= len(lines) else b""
    payload.decode("utf-8")
    return SourceSpan(
        "source_span",
        "source-span-v1",
        path,
        line,
        0,
        line,
        len(payload),
        "line",
        "utf8-byte-half-open",
    )


def _utf16_prefix_to_utf8_column(line: str, units: int) -> int:
    consumed = 0
    characters: list[str] = []
    for character in line:
        width = len(character.encode("utf-16-le")) // 2
        if consumed + width > units:
            break
        consumed += width
        characters.append(character)
        if consumed == units:
            break
    if consumed != units:
        raise ValueError("coordinate splits a UTF-16 surrogate pair or exceeds the line")
    return len("".join(characters).encode())


@ensure(lambda result: result.precision == "exact")
def convert_exact_location(
    *,
    path: str,
    source: bytes,
    coordinate_system: str,
    start: tuple[int, int],
    end: tuple[int, int],
) -> SourceSpan:
    """Convert exact adapter coordinates to canonical UTF-8 byte columns."""

    text_lines = source.decode("utf-8").splitlines()
    start_row, start_column = start
    end_row, end_column = end
    if (
        not 0 <= start_row < len(text_lines)
        or not 0 <= end_row < len(text_lines)
        or start_column < 0
        or end_column < 0
        or (end_row, end_column) < (start_row, start_column)
    ):
        raise ValueError("source coordinate is outside the decoded source")
    if coordinate_system == "utf16-code-units":
        canonical_start = _utf16_prefix_to_utf8_column(text_lines[start_row], start_column)
        canonical_end = _utf16_prefix_to_utf8_column(text_lines[end_row], end_column)
    else:
        if start_column > len(text_lines[start_row]) or end_column > len(text_lines[end_row]):
            raise ValueError("source column is outside the decoded line")
        canonical_start = len(text_lines[start_row][:start_column].encode())
        canonical_end = len(text_lines[end_row][:end_column].encode())
    return SourceSpan(
        "source_span",
        "source-span-v1",
        path,
        start_row + 1,
        canonical_start,
        end_row + 1,
        canonical_end,
        "exact",
        "utf8-byte-half-open",
    )


def normalize_location(
    *, analyzer: str, path: str, source: bytes, raw: dict[str, int]
) -> LocatedFinding | ContinuityResult:
    """Normalize one adapter's exact row/column record."""

    try:
        location = convert_exact_location(
            path=path,
            source=source,
            coordinate_system="unicode-code-points",
            start=(raw["row"] - 1, raw["column"]),
            end=(raw["end_row"] - 1, raw["end_column"]),
        )
    except (IndexError, UnicodeDecodeError, ValueError):
        return ContinuityResult("UNKNOWN", "invalid_source_coordinate")
    return LocatedFinding(analyzer, location)


def source_continuity(*, location: dict[str, str]) -> ContinuityResult:
    """Exclude selector and infrastructure identities from source continuity."""

    if location.get("kind") != "source_span":
        return ContinuityResult("UNKNOWN", "non_source_location")
    return ContinuityResult("PASS")


def select_differential_snapshots(*, merge_base: str, base_tip: str, head: str) -> DifferentialSnapshotSelection:
    """Select the merge-base as evidence baseline while retaining target-tip policy identity."""

    return DifferentialSnapshotSelection(merge_base, base_tip, head)


def _finding(value: dict[str, Any]) -> DifferentialFinding:
    return DifferentialFinding(
        analyzer=str(value.get("analyzer", "")),
        rule=str(value.get("rule", "")),
        severity=str(value.get("severity", "")),
        path=str(value.get("path", "")),
        line=int(value.get("line", 1)),
        message=" ".join(str(value.get("message", "")).split()),
        blocking=bool(value.get("blocking", False)),
    )


def _source_for(path: str, sources: dict[str, bytes]) -> bytes | None:
    if path in sources:
        return sources[path]
    if len(sources) == 1:
        return next(iter(sources.values()))
    return None


_MAX_SOURCE_BYTES = 16 * 1024 * 1024
_MAX_SOURCE_LINES = 20_000
_MAX_CORRESPONDENCE_CELLS = 4_000_000


def _edit_costs(
    base_lines: list[bytes],
    head_lines: list[bytes],
    *,
    forbidden_pair: tuple[int, int] | None = None,
) -> list[list[int]]:
    """Compute canonical insert/delete/replace/match costs, optionally forbidding one diagonal."""

    rows = len(base_lines) + 1
    columns = len(head_lines) + 1
    costs = [[0] * columns for _ in range(rows)]
    for base_index in range(1, rows):
        costs[base_index][0] = base_index
    for head_index in range(1, columns):
        costs[0][head_index] = head_index
    for base_index in range(1, rows):
        for head_index in range(1, columns):
            candidates = [
                costs[base_index - 1][head_index] + 1,
                costs[base_index][head_index - 1] + 1,
            ]
            if forbidden_pair != (base_index - 1, head_index - 1):
                replace_cost = 0 if base_lines[base_index - 1] == head_lines[head_index - 1] else 2
                candidates.append(costs[base_index - 1][head_index - 1] + replace_cost)
            costs[base_index][head_index] = min(candidates)
    return costs


def _suffix_edit_costs(base_lines: list[bytes], head_lines: list[bytes]) -> list[list[int]]:
    reversed_costs = _edit_costs(list(reversed(base_lines)), list(reversed(head_lines)))
    rows = len(base_lines)
    columns = len(head_lines)
    return [
        [reversed_costs[rows - base_index][columns - head_index] for head_index in range(columns + 1)]
        for base_index in range(rows + 1)
    ]


def _identity(finding: DifferentialFinding, *, normalized_path: str) -> tuple[str, str, str, str]:
    return finding.analyzer, finding.rule, normalized_path, finding.message


def _continuity(
    base: DifferentialFinding,
    head: DifferentialFinding,
    *,
    base_source: bytes | None,
    head_source: bytes | None,
    matrix_cache: dict[tuple[bytes, bytes], tuple[list[list[int]], list[list[int]]]],
    forbidden_cache: dict[tuple[bytes, bytes, int, int], int],
) -> tuple[Literal["unchanged", "introduced", "unknown"], dict[str, object]]:
    evidence: dict[str, object] = {
        "algorithm": "source-line-correspondence-v1",
        "base_line": base.line,
        "head_line": head.line,
        "bounds": {
            "max_source_bytes": _MAX_SOURCE_BYTES,
            "max_source_lines": _MAX_SOURCE_LINES,
            "max_cells": _MAX_CORRESPONDENCE_CELLS,
        },
    }
    context, reason = _continuity_context(base, head, base_source=base_source, head_source=head_source)
    if context is None:
        return "unknown", {**evidence, **reason}
    assert base_source is not None and head_source is not None
    evidence.update(
        _continuity_cost_evidence(
            context,
            source_key=(base_source, head_source),
            matrix_cache=matrix_cache,
            forbidden_cache=forbidden_cache,
        )
    )
    evidence.update(_continuity_anchor_evidence(context))
    return _continuity_decision(context, evidence)


def _continuity_context(
    base: DifferentialFinding,
    head: DifferentialFinding,
    *,
    base_source: bytes | None,
    head_source: bytes | None,
) -> tuple[_ContinuityContext | None, dict[str, object]]:
    if base_source is None or head_source is None:
        return None, {"reason": "missing_source"}
    base_lines = base_source.splitlines()
    head_lines = head_source.splitlines()
    cells = (len(base_lines) + 1) * (len(head_lines) + 1)
    if not _continuity_within_bounds(base_source, head_source, base_lines, head_lines, cells):
        return None, {"cells": cells, "reason": "correspondence_bounds"}
    base_index = base.line - 1
    head_index = head.line - 1
    context = _ContinuityContext(base_lines, head_lines, base_index, head_index, cells)
    if not _continuity_anchor_is_valid(context):
        return None, {"cells": cells, "reason": "invalid_source_anchor"}
    return context, {}


def _continuity_within_bounds(
    base_source: bytes,
    head_source: bytes,
    base_lines: list[bytes],
    head_lines: list[bytes],
    cells: int,
) -> bool:
    source_sizes_valid = max(len(base_source), len(head_source)) <= _MAX_SOURCE_BYTES
    source_lines_valid = max(len(base_lines), len(head_lines)) <= _MAX_SOURCE_LINES
    return source_sizes_valid and source_lines_valid and cells <= _MAX_CORRESPONDENCE_CELLS


def _continuity_anchor_is_valid(context: _ContinuityContext) -> bool:
    base_valid = 0 <= context.base_index < len(context.base_lines)
    head_valid = 0 <= context.head_index < len(context.head_lines)
    return base_valid and head_valid


def _continuity_cost_evidence(
    context: _ContinuityContext,
    *,
    source_key: tuple[bytes, bytes],
    matrix_cache: dict[tuple[bytes, bytes], tuple[list[list[int]], list[list[int]]]],
    forbidden_cache: dict[tuple[bytes, bytes, int, int], int],
) -> dict[str, object]:
    matrices = matrix_cache.get(source_key)
    if matrices is None:
        matrices = (
            _edit_costs(context.base_lines, context.head_lines),
            _suffix_edit_costs(context.base_lines, context.head_lines),
        )
        matrix_cache[source_key] = matrices
    forward, suffix = matrices
    global_cost = forward[-1][-1]
    pair_cost = 0 if context.base_lines[context.base_index] == context.head_lines[context.head_index] else 2
    forced_cost = (
        forward[context.base_index][context.head_index]
        + pair_cost
        + suffix[context.base_index + 1][context.head_index + 1]
    )
    forbidden_key = (*source_key, context.base_index, context.head_index)
    forbidden_cost = forbidden_cache.get(forbidden_key)
    if forbidden_cost is None:
        forbidden_cost = _edit_costs(
            context.base_lines,
            context.head_lines,
            forbidden_pair=(context.base_index, context.head_index),
        )[-1][-1]
        forbidden_cache[forbidden_key] = forbidden_cost
    return {
        "cells": context.cells,
        "global_cost": global_cost,
        "forced_cost": forced_cost,
        "forbidden_cost": forbidden_cost,
        "pair_cost": pair_cost,
    }


def _line_anchor(lines: list[bytes], index: int) -> tuple[bytes, bytes, bytes]:
    return (
        lines[index - 1] if index > 0 else b"<BOF>",
        lines[index],
        lines[index + 1] if index + 1 < len(lines) else b"<EOF>",
    )


def _continuity_anchor_evidence(context: _ContinuityContext) -> dict[str, object]:
    base_anchor = _line_anchor(context.base_lines, context.base_index)
    head_anchor = _line_anchor(context.head_lines, context.head_index)
    return {
        "base_anchor_digest": "sha256:" + hashlib.sha256(b"\0".join(base_anchor)).hexdigest(),
        "head_anchor_digest": "sha256:" + hashlib.sha256(b"\0".join(head_anchor)).hexdigest(),
        "base_distinct_location_count": context.base_lines.count(context.base_lines[context.base_index]),
        "head_distinct_location_count": context.head_lines.count(context.head_lines[context.head_index]),
    }


def _continuity_decision(
    context: _ContinuityContext,
    evidence: dict[str, object],
) -> tuple[Literal["unchanged", "introduced", "unknown"], dict[str, object]]:
    if evidence["base_distinct_location_count"] != 1 or evidence["head_distinct_location_count"] != 1:
        return "unknown", {**evidence, "decision": "ambiguous_source_anchor"}
    base_anchor = _line_anchor(context.base_lines, context.base_index)
    head_anchor = _line_anchor(context.head_lines, context.head_index)
    if base_anchor != head_anchor:
        return "introduced", {**evidence, "decision": "occurrence_anchor_changed"}
    pair_cost = _integer_evidence(evidence, "pair_cost")
    global_cost = _integer_evidence(evidence, "global_cost")
    forced_cost = _integer_evidence(evidence, "forced_cost")
    forbidden_cost = _integer_evidence(evidence, "forbidden_cost")
    if pair_cost == 0 and forced_cost == global_cost and forbidden_cost > global_cost:
        return "unchanged", {**evidence, "decision": "unique_optimal_match"}
    if forced_cost > global_cost or pair_cost != 0:
        return "introduced", {**evidence, "decision": "not_on_optimal_correspondence"}
    return "unknown", {**evidence, "decision": "alternate_optimal_correspondence"}


def _integer_evidence(evidence: dict[str, object], key: str) -> int:
    value = evidence[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"continuity evidence {key} is not an integer")
    return value


def _classification_digest(
    introduced: list[DifferentialFinding],
    fixed: list[DifferentialFinding],
    unchanged: list[DifferentialFinding],
    unknown: list[DifferentialFinding],
    correspondence_evidence: list[dict[str, object]],
) -> str:
    document = {
        "fixed": [finding.__dict__ for finding in fixed],
        "introduced": [finding.__dict__ for finding in introduced],
        "unchanged": [finding.__dict__ for finding in unchanged],
        "unknown": [finding.__dict__ for finding in unknown],
        "correspondence_evidence": correspondence_evidence,
    }
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def classify_findings(request: FindingClassificationRequest) -> DifferentialClassification:
    """Classify finding multiplicity using conservative exact-source continuity."""

    base_values = [_finding(value) for value in request.base_findings]
    head_values = [_finding(value) for value in request.head_findings]
    state = _ClassificationState([], [], [], [], [])
    early_result = _early_classification(request, base_values, head_values, state)
    if early_result is not None:
        return early_result
    renames = request.rename_facts or {}
    base_buckets, head_buckets = _finding_buckets(base_values, head_values, renames)
    for identity in sorted(set(base_buckets) | set(head_buckets)):
        _classify_identity(identity, base_buckets, head_buckets, request, state)
    return _final_classification(state)


def _early_classification(
    request: FindingClassificationRequest,
    base_values: list[DifferentialFinding],
    head_values: list[DifferentialFinding],
    state: _ClassificationState,
) -> DifferentialClassification | None:
    if request.base_analysis_status != "pass":
        return _classification_with_reason(state, "baseline_analysis_error")
    oversized = request.source_size_override is not None and request.source_size_override > _MAX_SOURCE_BYTES
    if request.rename_ambiguities or oversized:
        state.unknown.extend(head_values or base_values)
        return _classification_with_reason(state, "continuity_unavailable")
    return None


def _classification_with_reason(state: _ClassificationState, reason: str) -> DifferentialClassification:
    digest = _classification_digest(
        state.introduced,
        state.fixed,
        state.unchanged,
        state.unknown,
        state.correspondence_evidence,
    )
    return DifferentialClassification("UNKNOWN", (), (), (), tuple(state.unknown), digest, reason)


def _finding_buckets(
    base_values: list[DifferentialFinding],
    head_values: list[DifferentialFinding],
    renames: dict[str, str],
) -> tuple[
    dict[tuple[str, str, str, str], list[DifferentialFinding]],
    dict[tuple[str, str, str, str], list[DifferentialFinding]],
]:
    reverse_renames = {new: old for old, new in renames.items()}
    base_buckets: dict[tuple[str, str, str, str], list[DifferentialFinding]] = defaultdict(list)
    head_buckets: dict[tuple[str, str, str, str], list[DifferentialFinding]] = defaultdict(list)
    for finding in base_values:
        base_buckets[_identity(finding, normalized_path=finding.path)].append(finding)
    for finding in head_values:
        head_buckets[_identity(finding, normalized_path=reverse_renames.get(finding.path, finding.path))].append(
            finding
        )
    return base_buckets, head_buckets


def _classify_identity(
    identity: tuple[str, str, str, str],
    base_buckets: dict[tuple[str, str, str, str], list[DifferentialFinding]],
    head_buckets: dict[tuple[str, str, str, str], list[DifferentialFinding]],
    request: FindingClassificationRequest,
    state: _ClassificationState,
) -> None:
    base_bucket = list(base_buckets.get(identity, ()))
    head_bucket = list(head_buckets.get(identity, ()))
    severities = {finding.severity for finding in (*base_bucket, *head_bucket)}
    if _severity_multiset_changed(severities, base_bucket, head_bucket):
        state.unknown.extend(head_bucket or base_bucket)
        return
    for severity in sorted(severities):
        base_partition = [item for item in base_bucket if item.severity == severity]
        head_partition = [item for item in head_bucket if item.severity == severity]
        _classify_partition(identity, base_partition, head_partition, request, state)


def _severity_multiset_changed(
    severities: set[str],
    base_bucket: list[DifferentialFinding],
    head_bucket: list[DifferentialFinding],
) -> bool:
    return len(severities) > 1 and Counter(item.severity for item in base_bucket) != Counter(
        item.severity for item in head_bucket
    )


def _classify_partition(
    identity: tuple[str, str, str, str],
    base_partition: list[DifferentialFinding],
    head_partition: list[DifferentialFinding],
    request: FindingClassificationRequest,
    state: _ClassificationState,
) -> None:
    pair_count = min(len(base_partition), len(head_partition))
    for base_item, head_item in zip(base_partition[:pair_count], head_partition[:pair_count], strict=True):
        _classify_pair(identity, base_item, head_item, request, state)
    for base_item in base_partition[pair_count:]:
        _classify_removed_base(base_item, request, state)
    state.introduced.extend(head_partition[pair_count:])


def _classify_pair(
    identity: tuple[str, str, str, str],
    base_item: DifferentialFinding,
    head_item: DifferentialFinding,
    request: FindingClassificationRequest,
    state: _ClassificationState,
) -> None:
    continuity, continuity_evidence = _continuity(
        base_item,
        head_item,
        base_source=_source_for(base_item.path, request.base_sources),
        head_source=_source_for(head_item.path, request.head_sources),
        matrix_cache=state.correspondence_matrices,
        forbidden_cache=state.forbidden_costs,
    )
    state.correspondence_evidence.append(
        {
            **continuity_evidence,
            "identity": list(identity),
            "base_path": base_item.path,
            "head_path": head_item.path,
        }
    )
    destinations = {
        "unchanged": state.unchanged,
        "introduced": state.introduced,
        "unknown": state.unknown,
    }
    destinations[continuity].append(head_item)


def _classify_removed_base(
    base_item: DifferentialFinding,
    request: FindingClassificationRequest,
    state: _ClassificationState,
) -> None:
    renames = request.rename_facts or {}
    ambiguous_add_delete = base_item.path in request.deleted_paths and bool(request.added_paths)
    destination = state.unknown if base_item.path in renames or ambiguous_add_delete else state.fixed
    destination.append(base_item)


def _final_classification(state: _ClassificationState) -> DifferentialClassification:
    state.correspondence_evidence.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    digest = _classification_digest(
        state.introduced,
        state.fixed,
        state.unchanged,
        state.unknown,
        state.correspondence_evidence,
    )
    if state.unknown:
        status: Literal["PASS", "FAIL", "UNKNOWN"] = "UNKNOWN"
    elif any(finding.blocking for finding in (*state.introduced, *state.unchanged)):
        status = "FAIL"
    else:
        status = "PASS"
    return DifferentialClassification(
        status,
        tuple(state.introduced),
        tuple(state.fixed),
        tuple(state.unchanged),
        tuple(state.unknown),
        digest,
        correspondence_evidence=tuple(state.correspondence_evidence),
    )


def canonical_exact_renames(*, deleted: dict[str, str], added: dict[str, str]) -> ExactRenameFacts:
    """Pair only unique deleted/added paths with the same exact blob identity."""

    deleted_by_blob: dict[str, list[str]] = defaultdict(list)
    added_by_blob: dict[str, list[str]] = defaultdict(list)
    for path, blob in deleted.items():
        deleted_by_blob[blob].append(path)
    for path, blob in added.items():
        added_by_blob[blob].append(path)
    pairs: list[tuple[str, str]] = []
    ambiguities: list[str] = []
    for blob in sorted(set(deleted_by_blob) & set(added_by_blob)):
        old_paths = sorted(deleted_by_blob[blob])
        new_paths = sorted(added_by_blob[blob])
        if len(old_paths) == len(new_paths) == 1:
            pairs.append((old_paths[0], new_paths[0]))
        else:
            ambiguities.append(blob)
    return ExactRenameFacts(tuple(pairs), tuple(ambiguities))


_DIRECTIVE_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("ruff-noqa", "introduced_inline_suppression", re.compile(r"\b(?:noqa|ruff:\s*noqa)\b", re.I)),
    (
        "ruff-control",
        "introduced_inline_suppression",
        re.compile(r"\bruff:\s*(?:ignore|file-ignore|disable|enable)\s*\[", re.I),
    ),
    (
        "ruff-isort",
        "introduced_inline_suppression",
        re.compile(r"\b(?:ruff:\s*)?isort:\s*(?:skip_file|on|off|skip|split)\b", re.I),
    ),
    (
        "pylint",
        "introduced_inline_suppression",
        re.compile(r"\bpylint:\s*(?:disable(?:-next|-all|-msg)?|skip-file)\b", re.I),
    ),
    ("type-ignore", "introduced_inline_suppression", re.compile(r"\btype:\s*ignore(?:\[[^]]*\])?", re.I)),
    ("nosemgrep", "introduced_inline_suppression", re.compile(r"\bno(?:semgrep|sem)\b", re.I)),
    ("coverage", "introduced_inline_suppression", re.compile(r"\bpragma:\s*no\s+(?:cover|branch)\b", re.I)),
    (
        "basedpyright",
        "introduced_analyzer_result_control",
        re.compile(r"\bpyright:\s*(?:ignore(?:\[[^]]*\])?|strict|basic|standard|[A-Za-z][A-Za-z0-9]*\s*=)", re.I),
    ),
    (
        "crosshair",
        "introduced_analyzer_result_control",
        re.compile(
            r"\bcrosshair:\s*(?:on|off|enabled|analysis_kind|specs_complete|max_iterations|per_condition_timeout|per_path_timeout|max_uninteresting_iterations)\b",
            re.I,
        ),
    ),
)

_SUPPRESSION_ANALYZERS: dict[str, tuple[str, ...]] = {
    "ruff-noqa": ("ruff",),
    "ruff-control": ("ruff",),
    "ruff-isort": ("ruff",),
    "pylint": ("pylint",),
    "basedpyright": ("basedpyright",),
    "crosshair": ("contracts",),
    "type-ignore": ("basedpyright", "pylint"),
    "nosemgrep": ("semgrep", "semgrep-bugs"),
    "coverage": ("targeted-pytest-coverage",),
}


def _tokenize_comments(path: str, source: bytes) -> tuple[SuppressionOccurrence, ...]:
    occurrences: list[SuppressionOccurrence] = []
    for token in tokenize.tokenize(io.BytesIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        normalized = " ".join(token.string.strip().split())
        for family, kind, pattern in _DIRECTIVE_PATTERNS:
            if pattern.search(normalized):
                occurrences.append(SuppressionOccurrence(path, token.start[0], family, kind, normalized.lower()))
                break
    return tuple(occurrences)


def _suppression_key(
    occurrence: SuppressionOccurrence, *, reverse_renames: dict[str, str]
) -> tuple[str, int, str, str]:
    return (
        reverse_renames.get(occurrence.path, occurrence.path),
        occurrence.line,
        occurrence.family,
        occurrence.token,
    )


def _source_manifest_digest(sources: dict[str, bytes]) -> str:
    projection = {path: "sha256:" + hashlib.sha256(payload).hexdigest() for path, payload in sorted(sources.items())}
    return "sha256:" + hashlib.sha256(_canonical_bytes(projection)).hexdigest()


def _suppression_evidence(
    occurrence: SuppressionOccurrence,
    *,
    base_source: bytes | None,
    head_source: bytes | None,
    base_manifest_digest: str,
    head_manifest_digest: str,
) -> SuppressionEvidence:
    occurrence_projection = {
        "family": occurrence.family,
        "kind": occurrence.kind,
        "line": occurrence.line,
        "path": occurrence.path,
        "token": occurrence.token,
    }
    changed_hunk = (base_source or b"") + b"\0" + (head_source or b"")
    return SuppressionEvidence(
        changed_hunk_digest="sha256:" + hashlib.sha256(changed_hunk).hexdigest(),
        analyzers=_SUPPRESSION_ANALYZERS[occurrence.family],
        family=occurrence.family,
        base_blob_digest="sha256:" + hashlib.sha256(base_source).hexdigest() if base_source is not None else "",
        head_blob_digest="sha256:" + hashlib.sha256(head_source).hexdigest() if head_source is not None else "",
        occurrence_digest="sha256:" + hashlib.sha256(_canonical_bytes(occurrence_projection)).hexdigest(),
        base_manifest_digest=base_manifest_digest,
        head_manifest_digest=head_manifest_digest,
    )


def classify_suppression_delta(
    *,
    base_sources: dict[str, bytes],
    head_sources: dict[str, bytes],
    rename_facts: dict[str, str] | None = None,
    missing_base_findings: list[dict[str, Any]] | None = None,
    waiver: dict[str, Any] | None = None,
) -> SuppressionClassification:
    """Classify registered comment-token controls without accepting waivers."""

    if waiver is not None:
        raise UnsupportedWaiverInput("C14 has no authenticated waiver ingestion path")
    try:
        base_occurrences = _suppression_occurrences(base_sources)
        head_occurrences = _suppression_occurrences(head_sources)
    except (IndentationError, SyntaxError, UnicodeDecodeError, tokenize.TokenError) as exc:
        return SuppressionClassification("UNKNOWN", reason=f"suppression_manifest_error:{type(exc).__name__}")
    renames = rename_facts or {}
    base_by_key, head_by_key = _suppression_indexes(base_occurrences, head_occurrences, renames)
    unchanged_keys = sorted(set(base_by_key) & set(head_by_key))
    introduced_keys = sorted(set(head_by_key) - set(base_by_key))
    unchanged = tuple(head_by_key[key] for key in unchanged_keys)
    introduced = tuple(head_by_key[key] for key in introduced_keys)
    base_manifest_digest = _source_manifest_digest(base_sources)
    head_manifest_digest = _source_manifest_digest(head_sources)
    findings = _introduced_suppression_findings(
        introduced,
        head_sources,
        base_manifest_digest,
        head_manifest_digest,
    )
    quarantined = _append_quarantined_suppressions(
        findings,
        unchanged_keys,
        _SuppressionDeltaContext(
            base_by_key,
            head_by_key,
            base_sources,
            head_sources,
            renames,
            base_manifest_digest,
            head_manifest_digest,
        ),
    )
    missing_disposition = "unknown" if introduced and missing_base_findings else "ordinary"
    status = _suppression_status(quarantined=quarantined, introduced=bool(introduced))
    return SuppressionClassification(
        status,
        tuple(findings),
        introduced,
        unchanged,
        missing_disposition,
    )


def _suppression_occurrences(sources: dict[str, bytes]) -> tuple[SuppressionOccurrence, ...]:
    return tuple(
        occurrence for path, source in sorted(sources.items()) for occurrence in _tokenize_comments(path, source)
    )


def _suppression_indexes(
    base_occurrences: tuple[SuppressionOccurrence, ...],
    head_occurrences: tuple[SuppressionOccurrence, ...],
    renames: dict[str, str],
) -> tuple[
    dict[tuple[str, int, str, str], SuppressionOccurrence],
    dict[tuple[str, int, str, str], SuppressionOccurrence],
]:
    reverse_renames = {new: old for old, new in renames.items()}
    base_by_key = {_suppression_key(item, reverse_renames={}): item for item in base_occurrences}
    head_by_key = {_suppression_key(item, reverse_renames=reverse_renames): item for item in head_occurrences}
    return base_by_key, head_by_key


def _introduced_suppression_findings(
    introduced: tuple[SuppressionOccurrence, ...],
    head_sources: dict[str, bytes],
    base_manifest_digest: str,
    head_manifest_digest: str,
) -> list[SuppressionFinding]:
    return [
        SuppressionFinding(
            item.kind,
            item.path,
            item.line,
            True,
            _suppression_evidence(
                item,
                base_source=None,
                head_source=head_sources.get(item.path),
                base_manifest_digest=base_manifest_digest,
                head_manifest_digest=head_manifest_digest,
            ),
        )
        for item in introduced
    ]


def _append_quarantined_suppressions(
    findings: list[SuppressionFinding],
    unchanged_keys: list[tuple[str, int, str, str]],
    context: _SuppressionDeltaContext,
) -> bool:
    quarantined = False
    for key in unchanged_keys:
        base_item = context.base_by_key[key]
        head_item = context.head_by_key[key]
        base_source = context.base_sources[base_item.path]
        head_source = context.head_sources[head_item.path]
        pure_rename = context.renames.get(base_item.path) == head_item.path and base_source == head_source
        if base_source == head_source or pure_rename:
            continue
        findings.append(
            SuppressionFinding(
                "unchanged_suppression_on_changed_file",
                head_item.path,
                head_item.line,
                True,
                _suppression_evidence(
                    head_item,
                    base_source=base_source,
                    head_source=head_source,
                    base_manifest_digest=context.base_manifest_digest,
                    head_manifest_digest=context.head_manifest_digest,
                ),
            )
        )
        quarantined = True
    return quarantined


def _suppression_status(
    *,
    quarantined: bool,
    introduced: bool,
) -> Literal["PASS", "FAIL", "UNKNOWN"]:
    if quarantined:
        return "UNKNOWN"
    if introduced:
        return "FAIL"
    return "PASS"


def _canonical_bytes(document: object) -> bytes:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def load_suppression_catalog_and_checkpoint() -> tuple[SuppressionCatalogResource, C14Checkpoint]:
    """Load the signed catalog and its checkpoint binding from installed resources."""

    package = files("specfact_code_review")
    contracts = package.joinpath("resources", "contracts")
    resource_bytes = contracts.joinpath("pr-range-v1-suppression-catalog.json").read_bytes()
    matrix = json.loads(contracts.joinpath("review-report-schema-1.6-consumer-matrix.json").read_text(encoding="utf-8"))
    bindings = matrix["suppression_catalog_identity_bindings"]
    canonical_bytes = _canonical_bytes(json.loads(resource_bytes))
    resource = SuppressionCatalogResource("sha256:" + hashlib.sha256(resource_bytes).hexdigest(), resource_bytes)
    checkpoint = C14Checkpoint(SuppressionCatalogContract(str(bindings["checkpoint"]), canonical_bytes))
    return resource, checkpoint


def activate_suppression_catalog(
    *, checkpoint_digest: str, resource_digest: str, package_digest: str, profile_digest: str
) -> CatalogActivation:
    """Activate the profile only when every independently bound catalog digest agrees."""

    digests = {checkpoint_digest, resource_digest, package_digest, profile_digest}
    if len(digests) != 1:
        return CatalogActivation("UNKNOWN", False)
    return CatalogActivation("PASS", True)
