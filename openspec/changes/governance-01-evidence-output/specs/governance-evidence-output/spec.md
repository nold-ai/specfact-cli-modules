## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for <https://github.com/nold-ai/specfact-cli-modules/issues/481>.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## ADDED Requirements

### Requirement: Governance Evidence Output

The system SHALL produce machine-readable governance evidence suitable for CI and audit ingestion.

The system SHALL represent `current_execution` independently from optional historical chronology. Current passing tests SHALL NOT establish historical failing-before evidence, full requirement coverage or protected CI authority. Missing requirement/architecture/spec mappings SHALL remain unassessed coverage or explicit findings under the selected graph policy, never fabricated completeness. Independent producer verdicts SHALL retain their original status and source reference. Ordinary current-run verification SHALL NOT require full-chain execution, chronology, transcripts, approval receipts or duplicate proof execution.

#### Scenario: CI-consumable evidence includes policy and exception context

- **GIVEN** validation runs in CI mode
- **WHEN** evidence is generated
- **THEN** policy results and active exception references are included
- **AND** each exception includes identifier and expiration metadata.

#### Scenario: Evidence contains layer-level coverage metrics

- **GIVEN** full-chain validation has transition results
- **WHEN** governance evidence is emitted
- **THEN** each layer contains pass/fail/advisory counts and coverage percentages
- **AND** overall verdict is derivable from the evidence alone under the selected policy, without elevating unassessed coverage or optional chronology into a passing claim.

#### Scenario: Evidence carries clean-code results as a parallel quality dimension

- **GIVEN** a validation run includes `specfact review` clean-code output
- **WHEN** governance evidence is emitted
- **THEN** the envelope includes a top-level `code_quality` section with category counts and verdict
- **AND** clean-code data does not redefine or replace the traceability `validation_results.layers` structure

#### Scenario: Current tests pass while graph coverage is incomplete

- **GIVEN** ordinary current tests pass and required graph mappings are absent
- **WHEN** evidence is evaluated or serialized
- **THEN** `current_execution` remains separate from incomplete graph coverage
- **AND** missing mappings retain their own findings or unassessed status rather than becoming complete coverage
- **AND** no historical chronology or protected CI authority is inferred.

#### Scenario: Independent producer failure survives current test success

- **GIVEN** current tests pass but an independently required review or policy producer fails
- **WHEN** evidence is evaluated or serialized
- **THEN** both original verdicts and source references remain available
- **AND** the passing test result does not turn the failed required gate into acceptance.

#### Scenario: Current-only evidence has no historical receipt

- **GIVEN** a valid current-run result with no historical chronology or prior session receipt
- **WHEN** ordinary current-run verification consumes it
- **THEN** absence of optional history does not invalidate the current-execution claim
- **AND** no full-chain run, transcript, approval receipt or duplicate proof execution is required.

#### Scenario: Runtime emission exposes its artifact location

- **GIVEN** the owning command enables governance evidence output
- **WHEN** the runtime emitter completes
- **THEN** it writes the artifact and reports its path for CI ingestion
- **AND** it preserves the core envelope semantics and original producer outcomes.
