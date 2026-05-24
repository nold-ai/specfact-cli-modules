"""Cleanup forecast metrics for simplify-focused review reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import (
    AiBloatIndex,
    CleanupForecast,
    DeletionEstimate,
    GuidanceKindForecast,
    ReviewedLoc,
    ReviewFinding,
)


_CLEANUP_FORECAST_WEIGHTS = {
    "safe_mechanical": 1.0,
    "needs_tests": 0.6,
    "design_judgment": 0.25,
    "preserve": 0.0,
}


@dataclass
class _CleanupForecastTotals:
    by_guidance_kind: dict[str, GuidanceKindForecast]
    by_action_status: dict[str, int]
    low: int = 0
    expected: float = 0.0
    high: int = 0
    weighted_points: float = 0.0


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda findings: isinstance(findings, list), "findings must be a list")
@ensure(lambda result: isinstance(result, CleanupForecast), "result must be a cleanup forecast")
def build_cleanup_forecast(findings: list[ReviewFinding], files: list[Path]) -> CleanupForecast:
    reviewed_loc = _reviewed_loc_for_files(files)
    guided = [finding for finding in findings if finding.guidance_kind is not None]
    totals = _cleanup_forecast_totals(guided)
    kloc = max(reviewed_loc.total / 1000.0, 0.001)
    expected_lines = round(totals.expected)
    return CleanupForecast(
        reviewed_loc=reviewed_loc,
        estimated_deletion_lines=DeletionEstimate(low=totals.low, expected=expected_lines, high=totals.high),
        ai_bloat_index=AiBloatIndex(
            findings_per_kloc=round(len(guided) / kloc, 3),
            weighted_bloat_points_per_kloc=round(totals.weighted_points / kloc, 3),
            cleanup_yield_loc_per_kloc=round(expected_lines / kloc, 3),
        ),
        by_guidance_kind=totals.by_guidance_kind,
        by_action_status=totals.by_action_status,
        preview_evidence_count=sum(
            1
            for finding in guided
            if finding.remediation_packet is not None and finding.remediation_packet.patch_forecast_refs
        ),
        mutation_evidence_count=sum(
            1
            for finding in guided
            if finding.signal_trace is not None and any(signal.source == "mutation" for signal in finding.signal_trace)
        ),
    )


def _reviewed_loc_for_files(files: list[Path]) -> ReviewedLoc:
    production = 0
    tests = 0
    for file_path in files:
        if file_path.suffix not in {".py", ".pyi"}:
            continue
        try:
            loc = _count_python_loc(file_path)
        except (OSError, UnicodeDecodeError):
            continue
        if "tests" in file_path.parts:
            tests += loc
        else:
            production += loc
    return ReviewedLoc(production=production, tests=tests, total=production + tests)


def _count_python_loc(file_path: Path) -> int:
    return sum(
        1
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _cleanup_forecast_totals(guided: list[ReviewFinding]) -> _CleanupForecastTotals:
    totals = _CleanupForecastTotals(by_guidance_kind={}, by_action_status={})
    for finding in guided:
        _add_cleanup_forecast_finding(totals, finding)
    return totals


def _add_cleanup_forecast_finding(totals: _CleanupForecastTotals, finding: ReviewFinding) -> None:
    guidance_kind = finding.guidance_kind or "design_judgment"
    deletion_lines = finding.estimated_deletion_lines or 0
    current = totals.by_guidance_kind.get(guidance_kind, GuidanceKindForecast(count=0, estimated_deletion_lines=0))
    totals.by_guidance_kind[guidance_kind] = GuidanceKindForecast(
        count=current.count + 1,
        estimated_deletion_lines=current.estimated_deletion_lines + deletion_lines,
    )
    if finding.action_status is not None:
        totals.by_action_status[finding.action_status] = totals.by_action_status.get(finding.action_status, 0) + 1
    if guidance_kind == "safe_mechanical":
        totals.low += deletion_lines
    if guidance_kind != "preserve":
        totals.high += deletion_lines
    weight = _CLEANUP_FORECAST_WEIGHTS.get(guidance_kind, 0.0)
    totals.expected += deletion_lines * weight
    totals.weighted_points += weight
