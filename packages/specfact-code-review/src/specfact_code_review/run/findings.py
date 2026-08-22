"""Structured review findings and report models."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import ensure
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_CATEGORIES = (
    "clean_code",
    "security",
    "type_safety",
    "contracts",
    "testing",
    "style",
    "architecture",
    "tool_error",
    "naming",
    "kiss",
    "yagni",
    "dry",
    "solid",
    "ai_bloat",
)
VALID_SEVERITIES = ("error", "warning", "info")
GUIDANCE_KINDS = ("safe_mechanical", "needs_tests", "design_judgment", "preserve")
ACTION_STATUSES = ("recommended", "applied", "kept", "skipped", "failed")
PRESERVE_REASONS = (
    "contract_lambda",
    "protocol_member",
    "public_api",
    "compat_shim",
    "cli_callback",
    "domain_wrapper",
    "spec_linked",
    "load_bearing",
)
PASS = "PASS"
PASS_WITH_ADVISORY = "PASS_WITH_ADVISORY"
FAIL = "FAIL"
AssuranceStatus = Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]


class EvidenceRef(BaseModel):
    """Structured representation of supplemental evidence reference."""

    path: str | None = Field(default=None, description="Stable file path reference.")
    start_line: int | None = Field(default=None, ge=1, description="Start line number (1-based).")
    end_line: int | None = Field(default=None, ge=1, description="End line number (1-based).")
    artifact_id: str | None = Field(default=None, description="Artifact identifier.")
    description: str | None = Field(default=None, description="Description of the evidence.")

    @field_validator("path", "artifact_id", "description")
    @classmethod
    def _validate_non_empty_if_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be empty if provided")
        return value

    @model_validator(mode="after")
    def _validate_invariants(self) -> EvidenceRef:
        # At least one locator must be present
        if self.path is None and self.artifact_id is None and self.start_line is None:
            raise ValueError("at least one locator (path, artifact_id, or start_line) must be provided")

        # If end_line is provided, start_line must be provided
        if self.end_line is not None and self.start_line is None:
            raise ValueError("start_line must be provided if end_line is present")

        # If both start_line and end_line are provided, end_line >= start_line
        if self.start_line is not None and self.end_line is not None and self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")

        return self


class SignalTraceEntry(BaseModel):
    """Deterministic source signal that contributed to a cleanup finding."""

    tool: str = Field(..., description="Tool or analysis layer that produced the signal.")
    source: str = Field(..., description="Stable signal or rule source identifier.")
    fired: bool = Field(..., description="Whether the signal fired for this finding.")
    score: float | None = Field(default=None, description="Optional normalized signal score.")
    value: str | int | float | bool | None = Field(default=None, description="Optional raw signal value.")
    evidence_refs: list[EvidenceRef] | None = Field(default=None, description="Evidence backing the signal.")
    explanation: str = Field(..., description="Short explanation of the signal.")

    @field_validator("tool", "source", "explanation")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class PreserveReasonEvidence(BaseModel):
    """Closed-taxonomy reason that prevents automatic cleanup."""

    reason: Literal[
        "contract_lambda",
        "protocol_member",
        "public_api",
        "compat_shim",
        "cli_callback",
        "domain_wrapper",
        "spec_linked",
        "load_bearing",
    ] = Field(..., description="Closed preserve-reason taxonomy value.")
    evidence_refs: list[EvidenceRef] = Field(..., min_length=1, description="Evidence for the preserve reason.")
    explanation: str = Field(..., description="Why this context must be preserved.")

    @field_validator("explanation")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class RemediationPacket(BaseModel):
    """Portable AI IDE handoff contract for one cleanup finding."""

    issue: str = Field(..., description="Plain-language issue description.")
    recommended_action: str = Field(..., description="Recommended cleanup action.")
    possible_keep_reason: str | None = Field(default=None, description="Why the code might need to stay.")
    safety_checks: list[str] = Field(..., min_length=1, description="Checks required before editing.")
    validation_plan: list[str] = Field(..., min_length=1, description="Validation steps after editing.")
    safe_to_autofix: bool = Field(..., description="Whether an agent may apply this automatically.")
    patch_forecast_refs: list[str] | None = Field(default=None, description="Patch preview references when present.")

    @field_validator("issue", "recommended_action", "possible_keep_reason")
    @classmethod
    def _validate_non_empty_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("safety_checks", "validation_plan", "patch_forecast_refs")
    @classmethod
    def _validate_non_empty_entries(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and any(not item.strip() for item in value):
            raise ValueError("entries must not be empty")
        return value


class ReviewedLoc(BaseModel):
    """Reviewed Python LOC split by production and tests."""

    production: int = Field(..., ge=0)
    tests: int = Field(..., ge=0)
    total: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _validate_total_matches_parts(self) -> ReviewedLoc:
        if self.total != self.production + self.tests:
            raise ValueError("reviewed_loc.total must equal production + tests")
        return self


class DeletionEstimate(BaseModel):
    """Non-binding deletion-line range."""

    low: int = Field(..., ge=0)
    expected: int = Field(..., ge=0)
    high: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _validate_ordering(self) -> DeletionEstimate:
        if not self.low <= self.expected <= self.high:
            raise ValueError("estimated_deletion_lines must satisfy low <= expected <= high")
        return self


class AiBloatIndex(BaseModel):
    """Normalized cleanup metrics per KLOC."""

    findings_per_kloc: float = Field(..., ge=0.0)
    weighted_bloat_points_per_kloc: float = Field(..., ge=0.0)
    cleanup_yield_loc_per_kloc: float = Field(..., ge=0.0)


class GuidanceKindForecast(BaseModel):
    """Forecast aggregate for one guidance kind."""

    count: int = Field(..., ge=0)
    estimated_deletion_lines: int = Field(..., ge=0)
    weight: float = Field(default=0.0, ge=0.0)


class CleanupForecast(BaseModel):
    """Aggregate cleanup impact forecast for simplify-focused reviews."""

    reviewed_loc: ReviewedLoc
    estimated_deletion_lines: DeletionEstimate
    ai_bloat_index: AiBloatIndex
    by_guidance_kind: dict[str, GuidanceKindForecast] = Field(default_factory=dict)
    by_action_status: dict[str, int] = Field(default_factory=dict)
    preview_evidence_count: int = Field(default=0, ge=0)
    mutation_evidence_count: int = Field(default=0, ge=0)


class ReviewFinding(BaseModel):
    """Structured representation of a code-review finding."""

    category: Literal[
        "clean_code",
        "security",
        "type_safety",
        "contracts",
        "testing",
        "style",
        "architecture",
        "tool_error",
        "naming",
        "kiss",
        "yagni",
        "dry",
        "solid",
        "ai_bloat",
    ] = Field(..., description="Governed code-review category.")
    severity: Literal["error", "warning", "info"] = Field(..., description="Finding severity.")
    tool: str = Field(..., description="Originating tool name.")
    rule: str = Field(..., description="Originating rule identifier.")
    file: str = Field(..., description="Repository-relative file path.")
    line: int = Field(..., ge=1, description="1-based source line number.")
    message: str = Field(..., description="User-facing finding message.")
    fixable: bool = Field(default=False, description="Whether the finding can be automatically fixed.")
    status: Literal["open", "fixed", "waived-by-reference"] = Field(
        default="open",
        description="Finding lifecycle, independent from severity and remediation availability.",
    )
    differential_state: Literal["introduced", "fixed", "unchanged", "unknown"] | None = Field(
        default=None,
        description="Range classification, independent from finding lifecycle.",
    )
    autofix_available: bool | None = Field(
        default=None,
        description="Whether a remediation mechanism exists; this never resolves a finding.",
    )
    blocking: bool | None = Field(
        default=None,
        description="Blocking decision derived from severity and lifecycle policy.",
    )
    waiver_reference: None = Field(
        default=None,
        description="Reserved for a future authenticated exception contract; always null in C14.",
    )
    execution_state: Literal["ran", "error", "not_applicable"] | None = Field(
        default=None,
        description="Authoritative analyzer execution state when this record carries profile evidence.",
    )
    evidence_outcome: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"] | None = Field(
        default=None,
        description="Authoritative semantic evidence outcome when this record carries profile evidence.",
    )
    evidence_refs: list[EvidenceRef] | None = Field(
        default=None,
        description="Optional supplemental references with stable file paths, line ranges, or artifact identifiers.",
    )
    confidence: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Optional deterministic simplification confidence bucket.",
    )
    rewrite_hint: str | None = Field(default=None, description="Optional concise simplification guidance.")
    canonical_pattern: str | None = Field(default=None, description="Optional normalized simplification pattern label.")
    intent_key: str | None = Field(default=None, description="Optional stable duplicate-intent grouping key.")
    estimated_deletion_lines: int | None = Field(
        default=None,
        ge=0,
        description="Optional non-binding deletion estimate for simplification triage.",
    )
    related_locations: list[EvidenceRef] | None = Field(
        default=None,
        description="Optional related source locations for grouped simplification candidates.",
    )
    guidance_kind: Literal["safe_mechanical", "needs_tests", "design_judgment", "preserve"] | None = Field(
        default=None,
        description="Guided simplification action class.",
    )
    recommended_action: (
        Literal[
            "remove",
            "inline",
            "collapse",
            "deduplicate",
            "make_required",
            "keep",
            "inspect",
        ]
        | None
    ) = Field(default=None, description="Recommended simplification action.")
    clean_code_principle: (
        Literal[
            "kiss",
            "dry",
            "yagni",
            "contracts",
            "api_stability",
            "readability",
        ]
        | None
    ) = Field(default=None, description="Primary clean-code principle behind the recommendation.")
    rationale: str | None = Field(default=None, description="Why the recommendation is meaningful.")
    safety_checks: list[str] | None = Field(
        default=None,
        description="Concrete checks an agent or developer must satisfy before applying the change.",
    )
    preserve_reason: str | None = Field(
        default=None,
        description="Why a preserve recommendation should be kept despite apparent bloat.",
    )
    action_status: Literal["recommended", "applied", "kept", "skipped", "failed"] | None = Field(
        default=None,
        description="Lifecycle status for recommended simplification work.",
    )
    before_ref: EvidenceRef | None = Field(default=None, description="Evidence reference before an applied action.")
    after_ref: EvidenceRef | None = Field(default=None, description="Evidence reference after an applied action.")
    improvement: str | None = Field(default=None, description="Evidence-backed improvement summary.")
    signal_trace: list[SignalTraceEntry] | None = Field(
        default=None,
        description="Optional deterministic signal trace for cleanup findings.",
    )
    preserve_reasons: list[PreserveReasonEvidence] | None = Field(
        default=None,
        description="Optional closed-taxonomy preserve reasons that block automatic cleanup.",
    )
    remediation_packet: RemediationPacket | None = Field(
        default=None,
        description="Optional portable cleanup handoff packet for AI IDEs.",
    )

    @field_validator(
        "tool",
        "rule",
        "file",
        "message",
        "rewrite_hint",
        "canonical_pattern",
        "intent_key",
        "rationale",
        "preserve_reason",
        "improvement",
    )
    @classmethod
    def _validate_non_empty_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("safety_checks")
    @classmethod
    def _validate_safety_checks(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("safety_checks must not be empty when provided")
        if any(not item.strip() for item in value):
            raise ValueError("safety_checks entries must not be empty")
        return value

    @field_validator("signal_trace", "preserve_reasons")
    @classmethod
    def _validate_non_empty_evidence_list(cls, value: list[object] | None) -> list[object] | None:
        if value is not None and not value:
            raise ValueError("evidence lists must not be empty when provided")
        return value

    @model_validator(mode="after")
    def _validate_guided_metadata(self) -> ReviewFinding:
        guided_fields = (
            self.recommended_action,
            self.clean_code_principle,
            self.rationale,
            self.safety_checks,
            self.action_status,
            self.preserve_reason,
            self.before_ref,
            self.after_ref,
            self.improvement,
        )
        if self.guidance_kind is None:
            if any(value is not None for value in guided_fields):
                raise ValueError("guidance_kind is required when guided metadata fields are present")
            return self
        if self.recommended_action is None:
            raise ValueError("recommended_action is required when guidance_kind is present")
        if self.clean_code_principle is None:
            raise ValueError("clean_code_principle is required when guidance_kind is present")
        if self.rationale is None:
            raise ValueError("rationale is required when guidance_kind is present")
        if self.safety_checks is None:
            raise ValueError("safety_checks is required when guidance_kind is present")
        if self.guidance_kind == "preserve" and self.preserve_reason is None:
            raise ValueError("preserve_reason is required for preserve guidance")
        return self

    @model_validator(mode="after")
    def _derive_c14_lifecycle_fields(self) -> ReviewFinding:
        if self.autofix_available is not None and self.autofix_available != self.fixable:
            raise ValueError("autofix_available must preserve the legacy fixable value")
        self.autofix_available = self.fixable
        expected_blocking = self.severity == "error" and self.status == "open"
        if self.blocking is not None and self.blocking != expected_blocking:
            raise ValueError("blocking must be derived from severity and lifecycle status")
        self.blocking = expected_blocking
        return self

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def has_simplification_metadata(self) -> bool:
        """Return whether this finding carries additive simplification metadata."""
        return any(
            value is not None
            for value in (
                self.confidence,
                self.rewrite_hint,
                self.canonical_pattern,
                self.intent_key,
                self.estimated_deletion_lines,
                self.related_locations,
                self.guidance_kind,
                self.recommended_action,
                self.clean_code_principle,
                self.rationale,
                self.safety_checks,
                self.preserve_reason,
                self.action_status,
                self.before_ref,
                self.after_ref,
                self.improvement,
                self.signal_trace,
                self.preserve_reasons,
                self.remediation_packet,
            )
        )

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def has_guided_simplification_metadata(self) -> bool:
        """Return whether this finding carries agent-action simplification metadata."""
        return self.guidance_kind is not None

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def is_safe_mechanical_simplification(self) -> bool:
        """Return whether the finding is an unresolved safe mechanical simplification."""
        return (
            self.guidance_kind == "safe_mechanical"
            and self.action_status in {None, "recommended", "failed"}
            and not self.preserve_reasons
        )

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def has_cleanup_handoff_metadata(self) -> bool:
        """Return whether this finding carries cleanup forecast or handoff metadata."""
        return self.signal_trace is not None or self.preserve_reasons is not None or self.remediation_packet is not None

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def simplification_metadata_is_deterministic(self) -> bool:
        """Return whether simplification metadata is concrete enough for queued rewrites."""
        return all(
            value is not None
            for value in (
                self.rewrite_hint,
                self.canonical_pattern,
                self.intent_key,
            )
        )

    @beartype
    @ensure(lambda self, result: result is self.blocking)
    def is_blocking(self) -> bool:
        """Return whether this finding blocks a passing review verdict."""
        return bool(self.blocking)


class SimplificationSummary(BaseModel):
    """Aggregate evidence for guided simplification review runs."""

    by_guidance_kind: dict[str, int] = Field(default_factory=dict)
    by_action_status: dict[str, int] = Field(default_factory=dict)
    blocking_simplification_count: int = Field(default=0, ge=0)
    applied_count: int = Field(default=0, ge=0)
    kept_count: int = Field(default=0, ge=0)


class RequirementsEvidenceContext(BaseModel):
    """Immutable provenance from a finalized Requirements proof packet."""

    path: str = Field(..., min_length=1)
    content_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    mapping_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    plan_digest: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    source_ref: str = Field(..., pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    gate_decision: Literal["pass", "fail"]


class ReviewReport(BaseModel):
    """Governance-aligned evidence envelope for code review results."""

    schema_version: str = Field(default="1.0", description="Evidence schema version.")
    run_id: str = Field(..., description="Stable review run identifier.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="UTC timestamp for the run.")
    overall_verdict: Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"] | None = Field(
        default=None,
        description="Governance-aligned overall verdict.",
    )
    ci_exit_code: Literal[0, 1] | None = Field(default=None, description="Exit code suitable for CI enforcement.")
    assurance_status: AssuranceStatus | None = Field(
        default=None,
        description="Authoritative schema 1.6 aggregate assurance status.",
    )
    has_unknown_required_evidence: bool | None = Field(
        default=None,
        description="Whether any required schema 1.6 evidence remains unknown.",
    )
    scope_evidence: dict[str, object] | None = Field(default=None, description="Canonical scope evidence.")
    analyzer_evidence: list[dict[str, object]] | None = Field(
        default=None,
        description="Canonical analyzer-member evidence.",
    )
    suppression_catalog_digest: str | None = Field(
        default=None,
        description="Authenticated suppression-directive catalog identity.",
    )
    score: int = Field(..., ge=0, le=120, description="Review score in the inclusive range 0..120.")
    reward_delta: int | None = Field(default=None, description="Reward delta derived from score - 80.")
    findings: list[ReviewFinding] = Field(default_factory=list, description="Structured review findings.")
    summary: str = Field(..., description="Human-readable review summary.")
    simplification_summary: SimplificationSummary | None = Field(
        default=None,
        description="Aggregate simplification guidance and action-status evidence.",
    )
    cleanup_forecast: CleanupForecast | None = Field(
        default=None,
        description="Aggregate cleanup forecast for simplify-focused review runs.",
    )
    enforcement_mode: Literal["full", "changed", "shadow"] | None = Field(
        default=None,
        description="Review enforcement mode applied to the CI exit code.",
    )
    enforcement_summary: str | None = Field(
        default=None,
        description="Human-readable explanation of enforcement mode and blocking evidence.",
    )
    requirements_evidence: RequirementsEvidenceContext | None = Field(
        default=None,
        description="Finalized Requirements proof provenance; it does not affect the review verdict.",
    )
    house_rules_updates: list[str] = Field(default_factory=list, description="Suggested house-rules updates.")

    @field_validator("schema_version", "run_id", "summary")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("timestamp")
    @classmethod
    def _normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _schema_version(self) -> str:
        """Return the evidence schema version required by the present report fields."""
        if schema_version_at_least(self.schema_version, 6):
            return self.schema_version
        if self.requirements_evidence is not None:
            return "1.5"
        if self.enforcement_mode is not None:
            return "1.4"
        if self.cleanup_forecast is not None or any(
            finding.has_cleanup_handoff_metadata() for finding in self.findings
        ):
            return "1.3"
        if self.simplification_summary is not None:
            return "1.2"
        if any(finding.has_simplification_metadata() for finding in self.findings):
            return "1.1"
        return self.schema_version

    @model_validator(mode="after")
    def _derive_governance_fields(self) -> ReviewReport:
        if self.simplification_summary is None:
            self.simplification_summary = _build_simplification_summary(self.findings)
        self.schema_version = self._schema_version()
        self.reward_delta = self.score - 80
        if self._derive_authoritative_governance():
            return self
        if self._has_explicit_legacy_governance():
            return self
        self._derive_score_governance()
        return self

    def _derive_authoritative_governance(self) -> bool:
        if not schema_version_at_least(self.schema_version, 6) or self.assurance_status is None:
            return False
        self.has_unknown_required_evidence = bool(
            self.has_unknown_required_evidence
            or self.assurance_status == "UNKNOWN"
            or any(item.get("evidence_outcome") == "UNKNOWN" for item in self.analyzer_evidence or [])
        )
        if self.has_unknown_required_evidence and self.assurance_status in {"PASS", "NOT_APPLICABLE"}:
            self.assurance_status = "UNKNOWN"
        verdicts = {
            "PASS": PASS,
            "NOT_APPLICABLE": PASS_WITH_ADVISORY,
            "FAIL": FAIL,
            "UNKNOWN": FAIL,
        }
        self.overall_verdict = verdicts[self.assurance_status]
        accepted = self.assurance_status in {"PASS", "NOT_APPLICABLE"}
        self.ci_exit_code = 0 if self.enforcement_mode == "shadow" or accepted else 1
        return True

    def _has_explicit_legacy_governance(self) -> bool:
        return self.enforcement_mode is not None and self.overall_verdict is not None and self.ci_exit_code is not None

    def _derive_score_governance(self) -> None:
        blocking_error_present = any(finding.is_blocking() for finding in self.findings)
        if blocking_error_present:
            self.overall_verdict = FAIL
            self.ci_exit_code = 1
            return
        if self.score >= 70:
            self.overall_verdict = PASS
            self.ci_exit_code = 0
            return
        if self.score >= 50:
            self.overall_verdict = PASS_WITH_ADVISORY
            self.ci_exit_code = 0
            return
        self.overall_verdict = FAIL
        self.ci_exit_code = 1

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def has_blocking_findings(self) -> bool:
        """Return whether the report contains any blocking findings."""
        return any(finding.is_blocking() for finding in self.findings)


class AssuranceProjection(BaseModel):
    """Schema 1.6 authoritative status projected to legacy fields and exit policy."""

    assurance_status: AssuranceStatus
    overall_verdict: Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"]
    ci_exit_code: Literal[0, 1]
    enforcement_mode: Literal["full", "shadow"]


class AssuranceMemberEvidence(BaseModel):
    """Closed fields used by aggregate assurance derivation tests and consumers."""

    id: str
    outcome: AssuranceStatus | None = None
    diagnostic: str | None = None
    base: AssuranceStatus | None = None
    head: AssuranceStatus | None = None
    disposition: Literal["fixed", "introduced", "unchanged", "unknown"] | None = None


class AssuranceReport(BaseModel):
    """Minimal canonical schema 1.6 assurance envelope."""

    schema_version: Literal["1.6"] = "1.6"
    assurance_status: AssuranceStatus
    has_unknown_required_evidence: bool
    overall_verdict: Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"]
    ci_exit_code: Literal[0, 1]
    enforcement_mode: Literal["full", "shadow"]
    member_evidence: tuple[AssuranceMemberEvidence, ...]
    aggregate_blockers: tuple[dict[str, str], ...]
    summary: str
    suppression_catalog_digest: str | None = None


class ReviewReportReadResult(BaseModel):
    """Conservative authoritative read result for one serialized review report."""

    status: AssuranceStatus
    ci_exit_code: Literal[0, 1]


class ConsumerMatrixValidation(BaseModel):
    """Validation result for the closed schema 1.6 consumer fixture matrix."""

    status: Literal["PASS", "UNKNOWN"]
    exercised_statuses: tuple[str, ...] = ()
    reason: str = ""


def project_assurance_status(*, status: str, enforcement: str) -> AssuranceProjection:
    """Derive the compatibility verdict and non-shadow CI exit from authoritative status."""

    if status not in {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}:
        raise ValueError(f"Unsupported assurance status: {status}")
    if enforcement not in {"full", "shadow"}:
        raise ValueError(f"Unsupported schema 1.6 enforcement mode: {enforcement}")
    typed_status: AssuranceStatus = status  # type: ignore[assignment]
    typed_enforcement: Literal["full", "shadow"] = enforcement  # type: ignore[assignment]
    legacy: Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"]
    if typed_status == "PASS":
        legacy = "PASS"
    elif typed_status == "NOT_APPLICABLE":
        legacy = "PASS_WITH_ADVISORY"
    else:
        legacy = "FAIL"
    exit_code: Literal[0, 1] = 0 if typed_enforcement == "shadow" or typed_status in {"PASS", "NOT_APPLICABLE"} else 1
    return AssuranceProjection(
        assurance_status=typed_status,
        overall_verdict=legacy,
        ci_exit_code=exit_code,
        enforcement_mode=typed_enforcement,
    )


def build_assurance_report(
    *,
    status: str | None,
    enforcement: str,
    member_evidence: tuple[dict[str, str], ...],
    valid_blockers: tuple[dict[str, str], ...],
    suppression_catalog_digest: str | None = None,
) -> AssuranceReport:
    """Derive aggregate status after lifecycle classification, with FAIL before UNKNOWN."""

    members = tuple(AssuranceMemberEvidence.model_validate(item) for item in member_evidence)
    has_unknown = any(member.outcome == "UNKNOWN" or member.disposition == "unknown" for member in members)
    blockers = tuple(item for item in valid_blockers if item.get("status") == "open")
    if status is None:
        if blockers:
            derived = "FAIL"
        elif has_unknown:
            derived = "UNKNOWN"
        else:
            derived = "PASS"
    else:
        derived = status
    projection = project_assurance_status(status=derived, enforcement=enforcement)
    if derived == "PASS":
        summary = "All required validations passed."
    elif derived == "FAIL":
        summary = "Open blocking findings remain."
        if has_unknown:
            summary += " Required evidence also remains unknown."
    elif derived == "NOT_APPLICABLE":
        summary = "No governed impact is applicable to this review."
    else:
        summary = "Required validation evidence remains unknown."
    return AssuranceReport(
        assurance_status=projection.assurance_status,
        has_unknown_required_evidence=has_unknown,
        overall_verdict=projection.overall_verdict,
        ci_exit_code=projection.ci_exit_code,
        enforcement_mode=projection.enforcement_mode,
        member_evidence=members,
        aggregate_blockers=blockers,
        summary=summary,
        suppression_catalog_digest=suppression_catalog_digest,
    )


def read_review_report(payload: dict[str, object]) -> ReviewReportReadResult:
    """Read schema 1.6 conservatively; missing authoritative status is UNKNOWN."""

    schema_version = str(payload.get("schema_version", ""))
    raw_status = payload.get("assurance_status")
    if schema_version_at_least(schema_version, 6) and raw_status not in {
        "PASS",
        "FAIL",
        "UNKNOWN",
        "NOT_APPLICABLE",
    }:
        status: AssuranceStatus = "UNKNOWN"
    elif raw_status in {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}:
        status = raw_status  # type: ignore[assignment]
    else:
        legacy = payload.get("overall_verdict")
        status = "PASS" if legacy in {"PASS", "PASS_WITH_ADVISORY"} else "FAIL"
    enforcement = str(payload.get("enforcement_mode", "full"))
    if enforcement not in {"full", "shadow"}:
        enforcement = "full"
    projection = project_assurance_status(status=status, enforcement=enforcement)
    return ReviewReportReadResult(status=status, ci_exit_code=projection.ci_exit_code)


def _packaged_suppression_catalog_digest() -> str | None:
    path = Path(__file__).resolve().parent.parent / "resources/contracts/pr-range-v1-suppression-catalog.json"
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def schema_version_at_least(value: str, required_minor: int) -> bool:
    try:
        major_text, minor_text, *_ = value.split(".")
        major = int(major_text)
        minor = int(minor_text)
    except (ValueError, TypeError):
        return False
    return major > 1 or (major == 1 and minor >= required_minor)


def _unknown_matrix(reason: str) -> ConsumerMatrixValidation:
    return ConsumerMatrixValidation(status="UNKNOWN", reason=reason)


def _validate_matrix_catalog_identity(matrix: dict[str, object], expected_digest: str) -> str | None:
    envelope = matrix.get("accepted_pr_range_envelope")
    if not isinstance(envelope, dict) or envelope.get("suppression_catalog_digest") != expected_digest:
        return "suppression_catalog_identity_mismatch"
    bindings = matrix.get("suppression_catalog_identity_bindings")
    required = {"checkpoint", "resource", "package", "profile", "report", "static_envelope"}
    if not isinstance(bindings, dict) or set(bindings) != required:
        return "consumer_matrix_identity_bindings_invalid"
    if any(bindings[name] != expected_digest for name in required):
        return "suppression_catalog_identity_mismatch"
    return None


def _validated_matrix_statuses(matrix: dict[str, object], expected_digest: str) -> tuple[set[str], str | None]:
    reports = matrix.get("canonical_status_reports")
    if not isinstance(reports, list):
        return set(), "consumer_matrix_status_reports_invalid"
    statuses: set[str] = set()
    for report in reports:
        status, reason = _validated_matrix_status(report, expected_digest)
        if reason is not None:
            return set(), reason
        statuses.add(status)
    if statuses != {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}:
        return set(), "consumer_matrix_status_set_invalid"
    return statuses, None


def _validated_matrix_status(report: object, expected_digest: str) -> tuple[str, str | None]:
    if not isinstance(report, dict) or not isinstance(report.get("assurance_status"), str):
        return "", "consumer_matrix_status_reports_invalid"
    status = str(report["assurance_status"])
    try:
        projection = project_assurance_status(status=status, enforcement="full")
    except ValueError:
        return "", "consumer_matrix_status_reports_invalid"
    expected = (projection.overall_verdict, projection.ci_exit_code, expected_digest)
    actual = (report.get("overall_verdict"), report.get("ci_exit_code"), report.get("suppression_catalog_digest"))
    if actual != expected:
        return "", "consumer_matrix_status_projection_mismatch"
    return status, None


def _matrix_case_values(matrix: dict[str, object], key: str, value_key: str) -> set[object] | None:
    cases = matrix.get(key)
    if not isinstance(cases, list):
        return None
    return {case.get(value_key) for case in cases if isinstance(case, dict)}


def validate_consumer_matrix(matrix: object) -> ConsumerMatrixValidation:
    """Validate the closed status matrix and every suppression-catalog identity binding."""

    if not isinstance(matrix, dict):
        return _unknown_matrix("consumer_matrix_invalid")
    expected_catalog_digest = _packaged_suppression_catalog_digest()
    if expected_catalog_digest is None:
        return _unknown_matrix("suppression_catalog_resource_unavailable")
    identity_reason = _validate_matrix_catalog_identity(matrix, expected_catalog_digest)
    if identity_reason is not None:
        return _unknown_matrix(identity_reason)
    statuses, status_reason = _validated_matrix_statuses(matrix, expected_catalog_digest)
    if status_reason is not None:
        return _unknown_matrix(status_reason)
    if _matrix_case_values(matrix, "finding_multiset_cases", "disposition") != {
        "fixed",
        "introduced",
        "unchanged",
        "unknown",
    }:
        return _unknown_matrix("consumer_matrix_finding_multiset_invalid")
    if _matrix_case_values(matrix, "project_runtime_cases", "expected_status") != {"PASS", "UNKNOWN"}:
        return _unknown_matrix("consumer_matrix_project_runtime_invalid")
    expected_boundaries = {
        "accepted",
        "analyzer_profile",
        "merge_base",
        "producer_identity",
        "project_runtime",
        "schema",
        "suppression_catalog",
    }
    if _matrix_case_values(matrix, "pr_range_boundary_cases", "dimension") != expected_boundaries:
        return _unknown_matrix("consumer_matrix_pr_range_boundaries_invalid")
    return ConsumerMatrixValidation(status="PASS", exercised_statuses=tuple(sorted(statuses)))


def _build_simplification_summary(findings: list[ReviewFinding]) -> SimplificationSummary | None:
    guided = [finding for finding in findings if finding.has_guided_simplification_metadata()]
    if not guided:
        return None
    by_guidance_kind: dict[str, int] = {}
    by_action_status: dict[str, int] = {}
    for finding in guided:
        if finding.guidance_kind is not None:
            by_guidance_kind[finding.guidance_kind] = by_guidance_kind.get(finding.guidance_kind, 0) + 1
        if finding.action_status is not None:
            by_action_status[finding.action_status] = by_action_status.get(finding.action_status, 0) + 1
    return SimplificationSummary(
        by_guidance_kind=by_guidance_kind,
        by_action_status=by_action_status,
        blocking_simplification_count=sum(finding.is_safe_mechanical_simplification() for finding in guided),
        applied_count=by_action_status.get("applied", 0),
        kept_count=by_action_status.get("kept", 0),
    )
