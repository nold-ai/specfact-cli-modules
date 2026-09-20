## ADDED Requirements

### Requirement: Current Execution Is the Lean Default

Requirements SHALL default to current reconciliation from supplied current plan and JUnit inputs without historical RED, frozen mapping approvals or seals. It SHALL report current execution and chronology as independent claims and SHALL NOT execute Git, pytest or network operations.

#### Scenario: Fresh current results pass without history

- **GIVEN** every selected acceptance test occurs exactly once and passes at the supplied current source context
- **WHEN** current reconciliation runs without historical artifacts
- **THEN** current execution passes and chronology remains not evaluated
- **AND** no full correctness or complete coverage claim is inferred.

#### Scenario: Required acceptance output is incomplete

- **GIVEN** required output is missing, malformed or empty, or a selected outcome is missing, duplicated, failed, errored or skipped
- **WHEN** current reconciliation runs
- **THEN** acceptance proof remains non-passing with actionable diagnostics
- **AND** parser and resource bounds remain enforced.

### Requirement: Optional Associations Preserve Honest Coverage

Scenario associations SHALL be optional for ordinary test-result context. Supplied associations SHALL be validated exactly; absent associations SHALL report requirement coverage as not evaluated. Ordinary suite skips SHALL remain visible separately from required selected acceptance results.

#### Scenario: No scenario mapping is provided

- **GIVEN** valid current test output without scenario associations
- **WHEN** the report is generated
- **THEN** observed test outcomes remain available as context
- **AND** requirement coverage is not claimed complete or proven.

### Requirement: Versioned Claims Retain Legacy Meaning

Schema v3 SHALL separate `current_execution` from `red_green_chronology`. Explicit legacy v2 and red/final callers SHALL retain their original stricter meanings. Malformed v3 SHALL NOT fall back to legacy parsing.

#### Scenario: Explicit historical proof lacks required RED

- **GIVEN** an explicit legacy final-stage request without required historical evidence
- **WHEN** reconciliation runs
- **THEN** it remains non-passing rather than being accepted as current-only evidence.

#### Scenario: Invalid v3 is supplied

- **GIVEN** a v3 report with missing or invalid required fields
- **WHEN** a consumer validates the report
- **THEN** it rejects the report rather than interpreting it as v2.

### Requirement: Context Does Not Override Independent Authority

Reports SHALL retain supplied source and runner/environment context without making local declarations authoritative for protected CI. Code Review SHALL consume current-run context without rewriting its own verdict.

#### Scenario: Current tests pass but review fails

- **GIVEN** passing current execution and an independent failing Code Review outcome
- **WHEN** the report is consumed
- **THEN** Code Review retains its failing outcome
- **AND** the supplied source identity alone establishes no protected CI trust.
