"""Structured review findings and report models."""

from __future__ import annotations

from datetime import UTC, datetime
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
)
VALID_SEVERITIES = ("error", "warning", "info")
PASS = "PASS"
PASS_WITH_ADVISORY = "PASS_WITH_ADVISORY"
FAIL = "FAIL"


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
    ] = Field(..., description="Governed code-review category.")
    severity: Literal["error", "warning", "info"] = Field(..., description="Finding severity.")
    tool: str = Field(..., description="Originating tool name.")
    rule: str = Field(..., description="Originating rule identifier.")
    file: str = Field(..., description="Repository-relative file path.")
    line: int = Field(..., ge=1, description="1-based source line number.")
    message: str = Field(..., description="User-facing finding message.")
    fixable: bool = Field(default=False, description="Whether the finding can be automatically fixed.")
    evidence_refs: list[EvidenceRef] | None = Field(
        default=None,
        description="Optional supplemental references with stable file paths, line ranges, or artifact identifiers.",
    )

    @field_validator("tool", "rule", "file", "message")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @beartype
    @ensure(lambda self, result: result == (self.severity == "error" and not self.fixable))
    def is_blocking(self) -> bool:
        """Return whether this finding blocks a passing review verdict."""
        return self.severity == "error" and not self.fixable


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
    score: int = Field(..., ge=0, le=120, description="Review score in the inclusive range 0..120.")
    reward_delta: int | None = Field(default=None, description="Reward delta derived from score - 80.")
    findings: list[ReviewFinding] = Field(default_factory=list, description="Structured review findings.")
    summary: str = Field(..., description="Human-readable review summary.")
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

    @model_validator(mode="after")
    def _derive_governance_fields(self) -> ReviewReport:
        blocking_error_present = any(finding.is_blocking() for finding in self.findings)
        self.reward_delta = self.score - 80
        if blocking_error_present:
            self.overall_verdict = FAIL
            self.ci_exit_code = 1
            return self
        if self.score >= 70:
            self.overall_verdict = PASS
            self.ci_exit_code = 0
            return self
        if self.score >= 50:
            self.overall_verdict = PASS_WITH_ADVISORY
            self.ci_exit_code = 0
            return self
        self.overall_verdict = FAIL
        self.ci_exit_code = 1
        return self

    @beartype
    @ensure(lambda result: isinstance(result, bool))
    def has_blocking_findings(self) -> bool:
        """Return whether the report contains any blocking findings."""
        return any(finding.is_blocking() for finding in self.findings)
