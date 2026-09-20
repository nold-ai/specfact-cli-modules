## ADDED Requirements

### Requirement: Current Execution Is the Lean Default

Requirements SHALL default to current reconciliation from supplied current plan and JUnit inputs without historical RED, frozen mapping approvals or seals. It SHALL report current execution and chronology as independent claims and SHALL NOT execute Git, pytest or network operations. Required selected acceptance cases SHALL pass ordinarily, with no expected-failure metadata: XFAIL and XPASS, including a passed outcome with an empty `wasxfail` marker, SHALL remain non-passing acceptance proof. The existing test invocation must preserve that distinction in its output; no second evidence-only test run is required.

#### Scenario: Fresh current results pass without history

- **GIVEN** every canonical selected acceptance test occurs exactly once and passes ordinarily without expected-failure metadata, and execution metadata matches the submitted current plan and source identities
- **WHEN** current reconciliation runs without historical artifacts
- **THEN** current execution passes and chronology remains not evaluated
- **AND** no full correctness or complete coverage claim is inferred.

#### Scenario: Required acceptance output is incomplete

- **GIVEN** required output is missing, malformed or empty, or a selected outcome is missing, duplicated, failed, errored or skipped
- **WHEN** current reconciliation runs
- **THEN** acceptance proof remains non-passing with actionable diagnostics
- **AND** parser and resource bounds remain enforced.

#### Scenario: Expected failure unexpectedly passes

- **GIVEN** a selected case reports XPASS or a passed outcome with `wasxfail`/xfail metadata, including an empty marker
- **WHEN** current reconciliation runs under either strict or non-strict expected-failure configuration
- **THEN** selected acceptance proof remains non-passing, even if the overall test command exits zero.

### Requirement: Passing Results Are Bound to the Current Request

Reconciliation SHALL compare supplied execution metadata against the submitted
current plan identity/digest, exact canonical selector set, source revision/tree
and execution environment identity. When scenario associations are supplied,
their mapping digest SHALL also match. JUnit cases SHALL carry the canonical
`specfact.selector` identity; display names or class names alone SHALL NOT prove
a selected result. Missing, ambiguous or mismatched required identity SHALL
remain non-passing even when the displayed tests pass. These are current-run
consistency checks, not frozen development mappings or history requirements.
Core SHALL remain responsible for authenticating protected execution provenance;
matching local metadata alone SHALL NOT grant CI authority.

#### Scenario: Passing selectors belong to another plan or source

- **GIVEN** passing JUnit selectors but a different plan digest, source revision/tree, environment or supplied mapping digest
- **WHEN** reconciliation compares execution metadata with the current request
- **THEN** current execution remains non-passing with the mismatched identity identified
- **AND** matching test names cannot substitute for the required binding.

#### Scenario: Canonical identity or binding is missing

- **GIVEN** passing outcomes without required execution metadata or canonical selector identity
- **WHEN** current reconciliation runs
- **THEN** observations may remain diagnostic context but cannot establish a passing current-execution claim.

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
