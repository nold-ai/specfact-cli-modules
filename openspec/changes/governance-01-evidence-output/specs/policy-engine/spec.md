## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for <https://github.com/nold-ai/specfact-cli-modules/issues/481>.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## ADDED Requirements

### Requirement: Policy Evidence Serialization

Policy evaluation outputs SHALL be serializable into governance evidence records without changing the producer policy, verdict or trusted-authority boundary. Current execution and optional chronology SHALL remain separate claims.

#### Scenario: Policy rule results include evidence-ready fields

- **GIVEN** policy validation completes
- **WHEN** evidence serialization runs
- **THEN** each rule result includes rule ID, severity, mode, outcome and producer reference
- **AND** serialization preserves an independent failure even when current tests pass
- **AND** serialization alone does not authenticate a local result as protected CI evidence.
