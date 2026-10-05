## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for <https://github.com/nold-ai/specfact-cli-modules/issues/481>.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## ADDED Requirements

### Requirement: Full Chain Evidence Serialization

Full-chain result summaries SHALL be representable in the governance envelope without redefining transition validation. The system SHALL represent `current_execution` independently from optional historical chronology. Current passing tests SHALL NOT establish historical failing-before evidence, full requirement coverage or protected CI authority. Missing requirement/architecture/spec mappings SHALL remain unassessed coverage or explicit findings under the selected graph policy, never fabricated completeness. Independent producer verdicts SHALL retain their original status and source reference. Ordinary current-run verification SHALL NOT require full-chain execution, chronology, transcripts, approval receipts or duplicate proof execution.

#### Scenario: Supplied full-chain results fit the envelope

- **GIVEN** a producer supplies full-chain result summaries
- **WHEN** the governance envelope serializes them
- **THEN** it retains schema version, timestamp, profile, policy mode, layer summaries and overall status
- **AND** missing mappings and optional chronology keep their own distinct status.

#### Scenario: Envelope contract exists before the full-chain producer

- **GIVEN** only current execution and independent policy/review results are available
- **WHEN** the envelope is validated
- **THEN** absence of the optional full-chain producer does not invalidate the current result
- **AND** the envelope does not claim full-chain execution or coverage.
