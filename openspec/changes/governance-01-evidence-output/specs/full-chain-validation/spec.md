## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for https://github.com/nold-ai/specfact-cli-modules/issues/481.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## MODIFIED Requirements

### Requirement: Full Chain Validation
Full-chain validation SHALL emit governance-ready evidence artifacts.

#### Scenario: Evidence artifact is written with stable schema envelope
- **GIVEN** full-chain validation executes with evidence output enabled
- **WHEN** command completes
- **THEN** evidence includes schema version, timestamp, profile, policy mode, layer summaries, and overall status
- **AND** artifact path is printed for CI ingestion.
