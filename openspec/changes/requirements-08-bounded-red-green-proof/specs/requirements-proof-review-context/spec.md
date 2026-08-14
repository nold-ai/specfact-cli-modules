## MODIFIED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface MAY accept finalized Requirements evidence as an optional input. When that input uses the corrected schema, Code Review SHALL require and retain its path, content digest, mapping digest, plan digest, source identity, explicit `chronology_request`, `current_execution`, and `red_green_chronology` claim objects as provenance; only the R08 attestation inside that mandatory chronology claim object is optional. Truly legacy payloads SHALL be handled only by the explicit versioned compatibility path. Requirements status SHALL NOT calculate or rewrite review findings, score, verdict, or exit code.

#### Scenario: Unrequested chronology remains not evaluated

- **GIVEN** readable finalized corrected-schema Requirements evidence has `chronology_request: not_requested`, valid current execution, no capsule, and the canonical `red_green_chronology.status: not_evaluated` / `reason: capsule_not_supplied` claim
- **WHEN** Code Review receives it
- **THEN** review retains the path, content, mapping, plan, source, request state, current-execution, and chronology provenance
- **AND** it does not omit the chronology field or reinterpret the request
- **AND** the review verdict remains independent.

#### Scenario: Invalid top-level or non-final evidence is rejected

- **GIVEN** an unreadable, malformed, unsupported, non-final top-level Requirements envelope, or corrected-schema evidence missing either mandatory claim object or required provenance
- **WHEN** Code Review receives it
- **THEN** it rejects the invocation before review execution
- **AND** it emits no report that could be mistaken for a valid Requirements-aware review.

#### Scenario: Unknown chronology remains valid provenance

- **GIVEN** readable finalized corrected-schema Requirements evidence has `chronology_request: required`, valid `current_execution`, and `red_green_chronology.status: unknown` with deterministic diagnostics because the capsule is missing, invalid, or untrusted
- **WHEN** Code Review receives it
- **THEN** it accepts the top-level Requirements evidence and retains the required request state, both claim objects, and chronology diagnostics
- **AND** it does not label chronology pass or valid
- **AND** neither Requirements claim changes review findings, score, verdict, or exit code.

#### Scenario: Bounded chronology is visible but independent

- **GIVEN** readable finalized corrected-schema Requirements evidence contains a valid R08 chronology attestation
- **WHEN** Code Review consumes the evidence
- **THEN** the report retains the path, content, mapping, plan, source, current-execution, capsule digest, bounded claim, verifier epoch, evidence references, statuses, and limitations
- **AND** review policy remains derived only from review evidence.

