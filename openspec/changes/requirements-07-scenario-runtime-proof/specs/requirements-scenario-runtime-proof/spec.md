## ADDED Requirements

### Requirement: Lifecycle-Aware Requirements Readiness

The Requirements module SHALL distinguish planned readiness, mapping acceptance, test-authored planning, current execution, and historical TDD chronology. Current execution and chronology SHALL be independent claims; neither may silently imply or overwrite the other. The corrected R07 report SHALL always emit a `red_green_chronology` placeholder claim object with `status: not_evaluated` and `reason: capsule_not_supplied`. R07 SHALL expose no chronology-request or capsule input and SHALL NOT emit chronology pass, fail, or unknown; R08 owns those later MODIFIED semantics.

#### Scenario: Proposal mapping is complete but not executed

- **GIVEN** complete planned mappings without exact selectors
- **WHEN** planned maturity is evaluated
- **THEN** proposal readiness may pass
- **AND** current execution and chronology remain not evaluated
- **AND** the report does not claim implementation.

### Requirement: Mapping Acceptance Provenance

The Requirements module SHALL validate provider-neutral acceptance against the canonical mapping digest before test-authored or stronger evidence satisfies strict policy.

#### Scenario: Stale acceptance remains blocking

- **GIVEN** acceptance is missing, rejected, incomplete, or bound to another mapping digest
- **WHEN** accepted maturity or higher is required
- **THEN** the module emits a deterministic finding
- **AND** passing tests do not invent acceptance.

### Requirement: Deterministic Scenario Proof Plan

The Requirements module SHALL emit a deterministic plan of stable requirement/scenario identities, declared touchpoints, intents, observables, and exact structured selectors without executing commands. Exact selectors are required only at test-authored maturity and above.

#### Scenario: Stable inputs produce a stable plan

- **GIVEN** unchanged mappings and selectors
- **WHEN** planning repeats
- **THEN** the ordered plan and plan identity are byte-stable
- **AND** the report makes no execution or chronology claim.

#### Scenario: Unsafe selector is rejected

- **GIVEN** a selector escapes the repository, starts with option syntax, contains control/shell/wildcard syntax, uses an unsupported runner, or is not an exact test identity
- **WHEN** planning validates it
- **THEN** the plan is non-executable under strict policy
- **AND** no command string is emitted.

### Requirement: Current-Run JUnit Reconciliation

The Requirements module SHALL reconcile a deterministic plan with trusted current-run JUnit without starting tests. `current_execution` SHALL bind the mapping, plan, source, selector set, JUnit digest, runner/environment provenance, collection counts, and exact outcomes. The supplied mapping digest, plan identity/digest, source revision/tree, and selector set SHALL exactly equal the accepted plan and execution inputs; any mismatch SHALL be non-passing with deterministic diagnostics. Current execution SHALL be final without requiring historical evidence.

#### Scenario: Every exact selector passes in the current run

- **GIVEN** one canonical passing result for every required exact selector
- **WHEN** final current-run reconciliation executes
- **THEN** `current_execution` is pass
- **AND** the mandatory R07 chronology placeholder remains `status: not_evaluated` with `reason: capsule_not_supplied`
- **AND** the report does not say passing-after-red or change-proven.

#### Scenario: JUnit plan or source identity does not match

- **GIVEN** otherwise passing JUnit is bound to a different mapping digest, plan identity/digest, source revision/tree, or selector set than the accepted execution plan
- **WHEN** final current-run reconciliation executes
- **THEN** `current_execution` does not pass
- **AND** the report names every mismatched identity
- **AND** chronology cannot replace the rejected current result.

#### Scenario: Current result is incomplete or failing

- **GIVEN** a selector is missing, duplicate, ambiguous, skipped, failed, errored, or lacks canonical identity
- **WHEN** reconciliation executes
- **THEN** current execution does not pass
- **AND** chronology cannot replace the current result.

### Requirement: Historical Chronology Is a Separate Claim

New historical red-to-green claims SHALL be accepted only through the R08 bounded replay contract. R07 SHALL NOT infer chronology from current maturity, current JUnit, static Python/pytest analysis, or a newly generated legacy ledger.

#### Scenario: No R08 capsule is supplied

- **GIVEN** corrected R07 current execution is final and R07 has no chronology-request or capsule input
- **WHEN** the report is finalized
- **THEN** current execution retains its exact status
- **AND** the R07 chronology placeholder uses `status: not_evaluated` with `reason: capsule_not_supplied`
- **AND** no broader proof label is emitted.

#### Scenario: Legacy artifact is read for compatibility

- **GIVEN** an old report contains an explicitly labelled legacy-ledger basis
- **WHEN** compatibility reading occurs
- **THEN** the historical label remains migration-only
- **AND** it is not converted into a new R08 attestation.
