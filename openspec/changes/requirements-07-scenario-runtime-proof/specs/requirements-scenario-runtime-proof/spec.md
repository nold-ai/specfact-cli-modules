## ADDED Requirements

### Requirement: Lifecycle-Aware Requirements Readiness

The Requirements module SHALL distinguish proposal readiness from implementation
proof. A proposal-only source SHALL be evaluated at `planned` maturity from
stable requirement/scenario mappings, rationale, touchpoints, verification
cases, and observables without requiring a test path or claiming execution.
The report SHALL expose the requested and observed maturity separately from its
gate verdict and SHALL label implementation evidence as not-yet-available.

#### Scenario: Proposal mapping is complete but not executed

- **GIVEN** imported requirements and scenarios with a schema-v2 sidecar that
  maps each scenario to a rationale, touchpoint, verification case, and
  observable, but has no test selector
- **WHEN** evidence runs with required maturity `planned`
- **THEN** it returns a passing proposal-readiness verdict
- **AND** it reports `delivery_status: proposal-only`
- **AND** it reports `implementation_evidence: not-yet-available`
- **AND** it does not report the requirement as implemented or verified.

#### Scenario: Proposal mapping is incomplete

- **GIVEN** an imported requirement or scenario without a required schema-v2
  mapping field
- **WHEN** evidence runs with required maturity `planned`
- **THEN** it returns a failing incomplete maturity result
- **AND** each missing requirement, scenario, or field is reported
- **AND** no synthetic test link is created.

### Requirement: Mapping Acceptance Provenance

The Requirements module SHALL validate provider-neutral acceptance evidence
against the canonical mapping digest. Acceptance SHALL be a distinct maturity
state; it SHALL not be inferred from a passing proposal-readiness verdict.

#### Scenario: Accepted mapping enables test authoring

- **GIVEN** a complete planned mapping and an acceptance record with a matching
  mapping digest, decision, reviewer identity, role, timestamp, and immutable
  reference
- **WHEN** evidence requires `accepted` maturity
- **THEN** it reports the mapping as accepted
- **AND** it may proceed to test-authored validation.

#### Scenario: Stale or rejected acceptance remains blocking

- **GIVEN** an acceptance record with a rejected decision, missing provenance,
  or a digest different from the current mapping
- **WHEN** evidence requires `accepted` maturity or higher
- **THEN** it returns a deterministic acceptance finding
- **AND** it does not permit test or implementation proof to satisfy the gate.

### Requirement: Deterministic Scenario Proof Plan

The Requirements module SHALL emit a deterministic, machine-readable proof
plan for selected requirement scenarios without executing tests. Each planned
scenario SHALL carry a stable requirement/scenario identity, declared product
touchpoints, verification method, intent, and observable. Reconciliation SHALL
bind the plan to the supplied execution source revision.
Exact structured test selectors are required only at `test-authored` maturity
and above. A selector SHALL identify a supported runner and
repository-contained test case; it SHALL NOT contain a shell command.

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

### Requirement: Auditable Legacy TDD Ledger Migration

The Requirements module SHALL support an explicit, opt-in migration record for
legacy changes that captured failing-first evidence in an immutable TDD ledger
before this runtime-proof contract existed. The migration record SHALL bind the
ledger digest, current mapping digest, and current plan digest; it SHALL be
accepted only during final reconciliation. A valid migration record SHALL not
be represented as red JUnit proof, and the final report SHALL identify its
implementation evidence as `passing-after-legacy-tdd-ledger`.

#### Scenario: Immutable legacy ledger permits a transparent final transition

- **GIVEN** current-run passing JUnit results and an explicit legacy migration
  record whose ledger, mapping, and plan digests match the final plan
- **WHEN** final Requirements evidence reconciliation runs with that record
- **THEN** it returns a passing verified result when no other finding blocks it
- **AND** it records the migration basis and ledger provenance
- **AND** it labels the implementation evidence
  `passing-after-legacy-tdd-ledger`, not `passing-after-red-proven`.

#### Scenario: Missing, stale, or misplaced legacy record remains blocking

- **GIVEN** a missing, malformed, digest-mismatched, or red-stage legacy
  migration record
- **WHEN** Requirements evidence reconciliation runs
- **THEN** it does not waive the required red proof
- **AND** it emits a deterministic legacy-migration finding.
