## MODIFIED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface MAY accept finalized Requirements evidence as an optional input. When that input uses finalized report `schema_version: "4"`, Code Review SHALL require and retain its path, content digest, mapping digest, plan digest, source identity, top-level Requirements gate decision, explicit `chronology_request`, `current_execution`, and `red_green_chronology` claim objects as provenance; only the R08 attestation inside that mandatory chronology claim object is optional. Finalized report v2 SHALL use the legacy compatibility path. Finalized report v3 SHALL use the R07 compatibility path, retain both v3 claim objects, record `source_schema_version: 3`, and normalize the absent request only as compatibility `not_requested` because v3 cannot express chronology requests. Field omission SHALL NOT route a v4 payload to compatibility, and unsupported future versions SHALL be rejected. The retained Requirements gate decision and claim statuses SHALL NOT calculate or rewrite review findings, score, verdict, or exit code.

#### Scenario: Unrequested chronology remains not evaluated

- **GIVEN** readable finalized schema-v4 Requirements evidence has `chronology_request: not_requested`, valid current execution, no capsule, and the canonical `red_green_chronology.status: not_evaluated` / `reason: capsule_not_supplied` claim
- **WHEN** Code Review receives it
- **THEN** review retains the path, content, mapping, plan, source, top-level Requirements gate decision, request state, current-execution, and chronology provenance
- **AND** it does not omit the chronology field or reinterpret the request
- **AND** the review verdict remains independent.

#### Scenario: Invalid top-level or non-final evidence is rejected

- **GIVEN** an unreadable, malformed, unsupported, non-final top-level Requirements envelope, or schema-v4 evidence missing request state, either mandatory claim object, or required provenance
- **WHEN** Code Review receives it
- **THEN** it rejects the invocation before review execution
- **AND** it emits no report that could be mistaken for a valid Requirements-aware review.

#### Scenario: Unknown chronology remains valid provenance

- **GIVEN** readable finalized schema-v4 Requirements evidence has `chronology_request: required`, valid `current_execution`, and `red_green_chronology.status: unknown` with deterministic diagnostics because proof is missing, unavailable, unsupported, unverifiable, or untrusted
- **WHEN** Code Review receives it
- **THEN** it accepts the top-level Requirements evidence and retains the gate decision, required request state, both claim objects, and chronology diagnostics
- **AND** it does not label chronology pass or valid
- **AND** neither Requirements claim changes review findings, score, verdict, or exit code.

#### Scenario: Failed chronology remains valid provenance

- **GIVEN** readable finalized schema-v4 Requirements evidence has `chronology_request: required`, valid `current_execution`, and `red_green_chronology.status: fail` with a complete trusted contradiction
- **WHEN** Code Review receives it
- **THEN** it accepts the top-level Requirements evidence and retains the gate decision, request state, both claim objects, and exact contradiction
- **AND** it does not relabel failed chronology as unknown, valid, or pass
- **AND** neither Requirements claim changes review findings, score, verdict, or exit code.

#### Scenario: Bounded chronology is visible but independent

- **GIVEN** readable finalized schema-v4 Requirements evidence contains a valid R08 chronology attestation
- **WHEN** Code Review consumes the evidence
- **THEN** the report retains the path, content, mapping, plan, source, top-level Requirements gate decision, request state, current-execution, capsule digest, bounded claim, verifier epoch, evidence references, statuses, and limitations
- **AND** review policy remains derived only from review evidence.

