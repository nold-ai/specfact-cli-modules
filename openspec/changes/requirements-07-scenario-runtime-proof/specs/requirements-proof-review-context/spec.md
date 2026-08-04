## ADDED Requirements

### Requirement: Finalized Requirements Evidence Review Context

The Code Review public interface SHALL accept an optional finalized
Requirements proof as context. It SHALL validate the structured proof before
review begins, preserve its immutable path, content digest, mapping digest,
plan digest, source reference, and Requirements gate decision in the review
report, and SHALL NOT use that gate decision to calculate the review verdict
or exit code.

#### Scenario: Finalized proof informs review without verdict fusion

- **GIVEN** a readable schema-v2 Requirements proof whose execution stage is
  `final`
- **WHEN** `specfact code review run` receives it through its public context
  option
- **THEN** the resulting review JSON retains the Requirements provenance
- **AND** the review verdict and exit code remain derived only from review
  findings.

#### Scenario: Non-final or malformed evidence is rejected

- **GIVEN** an unreadable, malformed, incomplete, or non-final Requirements
  proof
- **WHEN** Code Review receives it through the public context option
- **THEN** it rejects the invocation before review execution
- **AND** it does not emit a review report that could be mistaken for a
  Requirements-aware review.

#### Scenario: Passing evidence retains its historical proof basis

- **GIVEN** a structurally complete final Requirements proof with a passing
  gate decision
- **WHEN** Code Review receives it through the public context option
- **THEN** it accepts only the `red-junit` proof basis or a
  `legacy-tdd-ledger` basis with matching digest-bound ledger provenance
- **AND** it rejects a missing or unrecognized proof basis before review
  execution.
