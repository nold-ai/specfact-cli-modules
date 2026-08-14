## MODIFIED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface MAY accept finalized Requirements evidence as an optional input. When that input uses the corrected schema, Code Review SHALL require and retain its path, content digest, mapping digest, plan digest, source identity, `current_execution`, and `red_green_chronology` claim objects as provenance; only the R08 attestation inside that mandatory chronology claim object is optional. Truly legacy payloads SHALL be handled only by the explicit versioned compatibility path. Requirements status SHALL NOT calculate or rewrite review findings, score, verdict, or exit code.

#### Scenario: Final current execution informs review without chronology

- **GIVEN** readable finalized corrected-schema Requirements evidence with a valid current-execution claim and no historical attestation
- **WHEN** Code Review receives it
- **THEN** review retains the path, content, mapping, plan, source, and current-execution provenance
- **AND** it retains the canonical `red_green_chronology` claim object with `status: not_evaluated` and `reason: capsule_not_supplied` rather than omitting the field or rejecting the report
- **AND** the review verdict remains independent.

#### Scenario: Malformed or non-final evidence is rejected

- **GIVEN** unreadable, malformed, unsupported, non-final, or corrected-schema Requirements evidence missing either mandatory claim object or required provenance
- **WHEN** Code Review receives it
- **THEN** it rejects the invocation before review execution
- **AND** it emits no report that could be mistaken for a valid Requirements-aware review.

#### Scenario: Bounded chronology is visible but independent

- **GIVEN** readable finalized corrected-schema Requirements evidence contains a valid R08 chronology attestation
- **WHEN** Code Review consumes the evidence
- **THEN** the report retains the path, content, mapping, plan, source, current-execution, capsule digest, bounded claim, verifier epoch, evidence references, statuses, and limitations
- **AND** review policy remains derived only from review evidence.

