## ADDED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface SHALL accept optional finalized Requirements evidence, validate its schema, and retain its path, content digest, mapping digest, plan digest, source identity, `current_execution`, and optional `red_green_chronology` as provenance. Requirements status SHALL NOT calculate or rewrite review findings, score, verdict, or exit code.

#### Scenario: Final current execution informs review without chronology

- **GIVEN** readable finalized Requirements evidence with a valid current-execution claim and no historical attestation
- **WHEN** Code Review receives it
- **THEN** review retains current-execution provenance
- **AND** it retains the canonical `red_green_chronology` claim object with `status: not_evaluated` and `reason: capsule_not_supplied` rather than omitting the field or rejecting the report
- **AND** the review verdict remains independent.

#### Scenario: Malformed or non-final evidence is rejected

- **GIVEN** unreadable, malformed, unsupported, or non-final Requirements evidence
- **WHEN** Code Review receives it
- **THEN** it rejects the invocation before review execution
- **AND** it emits no report that could be mistaken for a valid Requirements-aware review.

#### Scenario: Historical chronology is retained without verdict fusion

- **GIVEN** finalized Requirements evidence contains a valid R08 chronology attestation
- **WHEN** Code Review receives it
- **THEN** it retains the attestation identity and bounded claim separately from current execution
- **AND** neither Requirements claim changes the review policy result.

