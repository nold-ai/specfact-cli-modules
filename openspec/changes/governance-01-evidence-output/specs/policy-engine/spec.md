## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for https://github.com/nold-ai/specfact-cli-modules/issues/481.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## MODIFIED Requirements

### Requirement: Policy Engine
Policy evaluation outputs SHALL be serializable into governance evidence records.

#### Scenario: Policy rule results include evidence-ready fields
- **GIVEN** policy validation completes
- **WHEN** evidence serialization runs
- **THEN** each rule result includes rule ID, severity, mode, and outcome
- **AND** output can be consumed by CI gates without additional transformation.
