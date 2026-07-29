## ADDED Requirements

### Requirement: Deterministic Scenario Proof Plan

The Requirements module SHALL emit a deterministic, machine-readable proof
plan for selected requirement scenarios without executing tests. Each planned
scenario SHALL carry a stable requirement/scenario identity, source revision,
declared product touchpoints, and exact structured test selectors. A selector
SHALL identify a supported runner and repository-contained test case; it SHALL
NOT contain a shell command.

#### Scenario: Selected scenarios produce a stable plan

- **GIVEN** unchanged selected requirement sources, scenario mappings,
  touchpoints, and exact test selectors
- **WHEN** Requirements evidence planning runs repeatedly
- **THEN** it emits byte-stable ordered plan content with the same plan identity
- **AND** every scenario is marked only as declared or selected
- **AND** the report does not claim that a test executed or passed.

#### Scenario: Unsafe selector fails before consumer execution

- **GIVEN** a test selector that escapes the repository, begins with runner
  option syntax, contains control or shell syntax, uses an unsupported runner,
  or does not identify an exact test case
- **WHEN** Requirements evidence planning validates the mapping
- **THEN** it emits a bounded machine-readable invalid-selector finding
- **AND** the plan is non-executable under strict policy
- **AND** it emits no command string for a consumer to evaluate.

#### Scenario: Changed scenario lacks executable proof mapping

- **GIVEN** a selected requirement scenario with no valid exact test selector
- **WHEN** the resolved profile evaluates plan completeness
- **THEN** strict policy produces a failing scenario-unverified verdict
- **AND** advisory policy retains the same finding without claiming proof.

### Requirement: Current-Run JUnit Reconciliation

The Requirements module SHALL reconcile a previously emitted proof plan with
trusted JUnit XML without starting a test process. It SHALL mark a scenario as
executed or passed only when every required exact selector is matched
unambiguously to current-run test case results bound to that plan. For pytest,
the trusted result identity SHALL be a dedicated canonical selector property
containing the collected pytest node ID; the module SHALL NOT infer identity
from a JUnit display name or class name.

#### Scenario: Exact linked test executes and passes

- **GIVEN** a valid proof plan and trusted current-run JUnit results containing
  one passing test case for every required exact selector
- **WHEN** Requirements evidence reconciliation runs
- **THEN** the final report binds the plan identity, source revisions, and
  result-artifact digest
- **AND** it marks the matched scenarios executed and passed
- **AND** it emits a passing verdict when no other blocking finding exists.

#### Scenario: Declared test is absent from results

- **GIVEN** a valid plan whose required exact selector is not collected in the
  supplied JUnit results
- **WHEN** reconciliation runs
- **THEN** the scenario remains unproven with an uncollected-test finding
- **AND** strict policy returns a failing verdict after preserving diagnostics.

#### Scenario: Result cannot be trusted or matched

- **GIVEN** malformed JUnit, a missing canonical selector property, a
  mismatched plan identity or source revision, duplicate ambiguous test
  identities, or failed, errored, or skipped results
- **WHEN** reconciliation runs
- **THEN** it never upgrades the affected scenario to passed
- **AND** it emits deterministic findings that distinguish the failure class.

### Requirement: Requirements-Aware Review Context

The Code Review module SHALL optionally accept a finalized Requirements proof
report as validated, read-only context. It MAY emit deterministic findings for
reviewed product touchpoints with missing or red scenario proof, but SHALL NOT
rewrite the Requirements report or substitute a review verdict for the
Requirements verdict.

#### Scenario: Changed touchpoint has valid passing proof

- **GIVEN** Code Review receives a supported finalized Requirements report whose
  declared touchpoint matches a reviewed change and whose required scenarios
  have passed proof
- **WHEN** review runs
- **THEN** the review report records the Requirements context provenance
- **AND** it emits no missing-proof finding for that touchpoint.

#### Scenario: Changed touchpoint lacks passing proof

- **GIVEN** a reviewed change matches a declared touchpoint with absent,
  uncollected, failed, stale, or otherwise red scenario proof
- **WHEN** review runs with the finalized Requirements context
- **THEN** it emits a deterministic Requirements-coverage finding referencing
  the requirement/scenario and touchpoint identities
- **AND** it preserves the separate Requirements verdict unchanged.

#### Scenario: Review context is malformed or unsupported

- **GIVEN** Code Review receives malformed evidence or an unsupported future
  schema version
- **WHEN** context validation runs
- **THEN** it fails closed with bounded remediation
- **AND** it does not infer Requirements state from repository filenames.
