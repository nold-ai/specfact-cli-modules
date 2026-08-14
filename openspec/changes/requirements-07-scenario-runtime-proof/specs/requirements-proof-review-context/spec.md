## ADDED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface MAY accept finalized Requirements evidence as an optional input. When that input uses the corrected schema, Code Review SHALL require and retain its path, content digest, mapping digest, plan digest, source identity, `current_execution`, and `red_green_chronology` claim objects as provenance; only the chronology attestation inside that mandatory claim object is optional. Truly legacy payloads SHALL be handled only by the explicit versioned compatibility path. Requirements status SHALL NOT calculate or rewrite review findings, score, verdict, or exit code.

#### Scenario: Final current execution informs review without chronology

- **GIVEN** readable finalized Requirements evidence with a valid current-execution claim and no historical attestation
- **WHEN** Code Review receives it
- **THEN** review retains current-execution provenance
- **AND** it retains the canonical `red_green_chronology` claim object with `status: not_evaluated` and `reason: capsule_not_supplied` rather than omitting the field or rejecting the report
- **AND** the review verdict remains independent.

#### Scenario: Invalid top-level or non-final evidence is rejected

- **GIVEN** an unreadable, malformed, unsupported, non-final top-level Requirements envelope, or corrected-schema evidence missing a mandatory claim object or required provenance field
- **WHEN** Code Review receives it
- **THEN** it rejects the invocation before review execution
- **AND** it emits no report that could be mistaken for a valid Requirements-aware review.

#### Scenario: Unknown chronology remains valid provenance

- **GIVEN** readable finalized corrected-schema Requirements evidence has valid `current_execution` and `red_green_chronology.status: unknown` with deterministic diagnostics for a requested invalid or untrusted capsule
- **WHEN** Code Review receives it
- **THEN** it accepts the top-level Requirements evidence and retains both claim objects plus the chronology diagnostics
- **AND** it does not label chronology pass or valid
- **AND** neither Requirements claim changes review findings, score, verdict, or exit code.

#### Scenario: Historical chronology is retained without verdict fusion

- **GIVEN** finalized Requirements evidence contains a valid R08 chronology attestation
- **WHEN** Code Review receives it
- **THEN** it retains the attestation identity and bounded claim separately from current execution
- **AND** neither Requirements claim changes the review policy result.

