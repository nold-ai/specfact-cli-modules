"""Cleanup preview and mutation evidence helpers for review runs."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import (
    EvidenceRef,
    RemediationPacket,
    ReviewFinding,
    ReviewReport,
    SignalTraceEntry,
)
from specfact_code_review.run.forecast import build_cleanup_forecast


ApplySimplificationFixes = Callable[[ReviewReport], list[ReviewFinding]]


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a review report")
def with_previewed_simplification_findings(
    report: ReviewReport,
    files: list[Path],
    apply_simplification_fixes: ApplySimplificationFixes,
) -> ReviewReport:
    previewed_findings = _preview_simplification_fixes(report, apply_simplification_fixes)
    if not previewed_findings:
        return with_refreshed_cleanup_forecast(report, files)
    replacements = {(finding.file, finding.line, finding.rule): finding for finding in previewed_findings}
    findings = [replacements.get((finding.file, finding.line, finding.rule), finding) for finding in report.findings]
    return with_refreshed_cleanup_forecast(report.model_copy(update={"findings": findings}), files)


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a review report")
def with_mutation_evidence(report: ReviewReport, files: list[Path]) -> ReviewReport:
    findings = [_with_mutation_signal(finding) for finding in report.findings]
    return with_refreshed_cleanup_forecast(report.model_copy(update={"findings": findings}), files)


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a review report")
def with_refreshed_cleanup_forecast(report: ReviewReport, files: list[Path]) -> ReviewReport:
    return report.model_copy(
        update={
            "cleanup_forecast": build_cleanup_forecast(report.findings, files),
            "schema_version": "1.3",
        }
    )


def _preview_simplification_fixes(
    report: ReviewReport,
    apply_simplification_fixes: ApplySimplificationFixes,
) -> list[ReviewFinding]:
    previewed: list[ReviewFinding] = []
    for finding in _fixable_simplifications_by_stable_line_order(report.findings):
        preview = _preview_single_simplification(finding, apply_simplification_fixes)
        if preview is not None:
            previewed.append(preview)
    return previewed


def _preview_single_simplification(
    finding: ReviewFinding,
    apply_simplification_fixes: ApplySimplificationFixes,
) -> ReviewFinding | None:
    source_path = Path(finding.file)
    try:
        before = source_path.read_text(encoding="utf-8")
    except OSError:
        return None
    with tempfile.TemporaryDirectory(prefix="specfact-review-preview-") as tmpdir:
        preview_path = Path(tmpdir) / source_path.name
        if not _write_preview_source(preview_path, before):
            return None
        preview_finding = finding.model_copy(update={"file": str(preview_path)})
        if not apply_simplification_fixes(_report_for_preview(preview_finding)):
            return None
        try:
            after = preview_path.read_text(encoding="utf-8")
        except OSError:
            return None
    added, removed = _line_delta(before, after)
    return _with_patch_preview(finding, added=added, removed=removed)


def _fixable_simplifications_by_stable_line_order(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return sorted(
        [finding for finding in findings if finding.is_safe_mechanical_simplification()],
        key=lambda finding: (finding.file, -finding.line, finding.rule),
    )


def _write_preview_source(path: Path, source: str) -> bool:
    try:
        path.write_text(source, encoding="utf-8")
    except OSError:
        return False
    return True


def _report_for_preview(finding: ReviewFinding) -> ReviewReport:
    return ReviewReport(
        run_id="preview",
        score=85,
        findings=[finding],
        summary="Preview simplification fix.",
    )


def _line_delta(before: str, after: str) -> tuple[int, int]:
    before_count = len(before.splitlines())
    after_count = len(after.splitlines())
    return max(0, after_count - before_count), max(0, before_count - after_count)


def _with_patch_preview(finding: ReviewFinding, *, added: int, removed: int) -> ReviewFinding:
    patch_ref = f"preview:{finding.file}:{finding.line}"
    signal_trace = [
        *(finding.signal_trace or []),
        SignalTraceEntry(
            tool="specfact",
            source="preview_fixes",
            fired=True,
            score=1.0,
            value=f"added={added}; removed={removed}; net={added - removed}",
            evidence_refs=[EvidenceRef(path=finding.file, start_line=finding.line)],
            explanation="Non-mutating preview computed a safe-mechanical patch forecast.",
        ),
    ]
    packet = _packet_with_patch_ref(finding, patch_ref)
    return ReviewFinding(**{**finding.model_dump(), "signal_trace": signal_trace, "remediation_packet": packet})


def _packet_with_patch_ref(finding: ReviewFinding, patch_ref: str) -> RemediationPacket:
    if finding.remediation_packet is None:
        return RemediationPacket(
            issue=finding.message,
            recommended_action=finding.recommended_action or "inspect",
            possible_keep_reason=finding.preserve_reason,
            safety_checks=finding.safety_checks or ["inspect the surrounding behavior before editing"],
            validation_plan=["run targeted tests", "rerun simplify review"],
            safe_to_autofix=finding.is_safe_mechanical_simplification() and finding.fixable,
            patch_forecast_refs=[patch_ref],
        )
    refs = list(finding.remediation_packet.patch_forecast_refs or [])
    if patch_ref not in refs:
        refs.append(patch_ref)
    return finding.remediation_packet.model_copy(update={"patch_forecast_refs": refs})


def _with_mutation_signal(finding: ReviewFinding) -> ReviewFinding:
    if not finding.is_safe_mechanical_simplification():
        return finding
    value = "inconclusive: mutation scaffolding only"
    explanation = "Mutation tooling was available, but candidate-scoped execution is not configured yet."
    if not _mutation_tool_available():
        value = "inconclusive: mutmut unavailable"
        explanation = "Mutation proof was requested, but mutmut is not installed."
    signal_trace = [
        *(finding.signal_trace or []),
        SignalTraceEntry(
            tool="mutmut",
            source="mutation",
            fired=False,
            value=value,
            evidence_refs=[EvidenceRef(path=finding.file, start_line=finding.line)],
            explanation=explanation,
        ),
    ]
    return ReviewFinding(**{**finding.model_dump(), "signal_trace": signal_trace})


def _mutation_tool_available() -> bool:
    return shutil.which("mutmut") is not None
