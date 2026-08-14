## ADDED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface MAY accept finalized Requirements evidence as an optional input. When that input uses finalized report `schema_version: "3"`, Code Review SHALL require and retain its path, content digest, mapping digest, plan digest, source identity, top-level Requirements gate decision, `current_execution`, and `red_green_chronology` claim objects as provenance; the R07 chronology claim is the mandatory not-evaluated placeholder and contains no attestation. Finalized report schema v2 SHALL be handled only by the explicit legacy compatibility path and may omit v3 claim objects; the reader SHALL retain `source_schema_version: 2` and SHALL NOT reinterpret legacy proof as corrected current execution or chronology. A structurally complete final v2 packet with a passing Requirements gate SHALL be accepted only with `red-junit` proof basis or `legacy-tdd-ledger` proof basis whose ledger provenance matches its bound ledger, mapping, and plan digests. Missing, unrecognized, incomplete, or digest-mismatched v2 proof basis SHALL be rejected before review. Unsupported future versions SHALL be rejected. The retained Requirements gate decision and claim statuses SHALL NOT calculate or rewrite review findings, score, verdict, or exit code.

#### Scenario: Final current execution informs review without chronology

- **GIVEN** readable finalized schema-v3 Requirements evidence with a valid current-execution claim and no historical attestation
- **WHEN** Code Review receives it
- **THEN** review retains source and current-execution provenance plus the independent top-level Requirements gate decision
- **AND** it retains the canonical `red_green_chronology` claim object with `status: not_evaluated` and `reason: capsule_not_supplied` rather than omitting the field or rejecting the report
- **AND** the review verdict remains independent.

#### Scenario: Invalid top-level or non-final evidence is rejected

- **GIVEN** an unreadable, malformed, unsupported, non-final top-level Requirements envelope, or schema-v3 evidence missing a mandatory claim object or required provenance field
- **WHEN** Code Review receives it
- **THEN** it rejects the invocation before review execution
- **AND** it emits no report that could be mistaken for a valid Requirements-aware review.

#### Scenario: Passing legacy v2 proof retains its historical basis

- **GIVEN** a readable structurally complete finalized report v2 with a passing Requirements gate
- **WHEN** Code Review receives it
- **THEN** it records `source_schema_version: 2`
- **AND** it accepts only `red-junit` basis or `legacy-tdd-ledger` basis with matching bound ledger, mapping, and plan digests
- **AND** missing, unrecognized, incomplete, or digest-mismatched basis is rejected before review
- **AND** the legacy basis is not converted into v3 current execution or chronology.

