## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for https://github.com/nold-ai/specfact-cli-modules/issues/481.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## ADDED Requirements

### Requirement: Governance Evidence Output
The system SHALL produce machine-readable governance evidence suitable for CI and audit ingestion.

#### Scenario: CI-consumable evidence includes policy and exception context
- **GIVEN** validation runs in CI mode
- **WHEN** evidence is generated
- **THEN** policy results and active exception references are included
- **AND** each exception includes identifier and expiration metadata.

#### Scenario: Evidence contains layer-level coverage metrics
- **GIVEN** full-chain validation has transition results
- **WHEN** governance evidence is emitted
- **THEN** each layer contains pass/fail/advisory counts and coverage percentages
- **AND** overall verdict is derivable from the evidence alone.

#### Scenario: Evidence carries clean-code results as a parallel quality dimension
- **GIVEN** a validation run includes `specfact review` clean-code output
- **WHEN** governance evidence is emitted
- **THEN** the envelope includes a top-level `code_quality` section with category counts and verdict
- **AND** clean-code data does not redefine or replace the traceability `validation_results.layers` structure
