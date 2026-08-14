## ADDED Requirements

### Requirement: Lifecycle-Aware Requirements Readiness

The Requirements module SHALL distinguish proposal readiness from implementation proof. A proposal-only schema-v2 mapping sidecar SHALL be evaluated at `planned` maturity only when every selected requirement/scenario mapping contains stable identities, rationale, at least one declared touchpoint, at least one verification case with method and intent, and an observable. It SHALL NOT require a test selector at planned maturity or claim execution. The report SHALL expose requested maturity, observed maturity, gate decision, delivery status, and implementation-evidence status separately.

The corrected R07 finalized Requirements report SHALL use `schema_version: "3"` and SHALL always emit independent `current_execution` and `red_green_chronology` claim objects. R07 SHALL expose no chronology-request or capsule input; its chronology object is the mandatory `status: not_evaluated` / `reason: capsule_not_supplied` placeholder and cannot emit pass, fail, or unknown. Mapping sidecars remain schema v2. Finalized report v2 is legacy-only; a v3 report missing either mandatory claim object or required v3 provenance is malformed v3 and SHALL NOT be reinterpreted as legacy.

#### Scenario: Proposal mapping is complete but not executed

- **GIVEN** imported requirements and scenarios with a schema-v2 sidecar mapping every scenario to rationale, touchpoint, verification case with method and intent, and observable, but no exact selector
- **WHEN** evidence runs with required maturity `planned`
- **THEN** proposal readiness may pass
- **AND** requested and observed maturity remain explicit
- **AND** delivery status is proposal-only and implementation evidence is not-yet-available
- **AND** current execution and chronology remain not evaluated
- **AND** the report does not claim implementation or verification.

#### Scenario: Proposal mapping is incomplete

- **GIVEN** a selected requirement or scenario is missing a stable identity, rationale, touchpoint, verification case, verification method/intent, or observable
- **WHEN** evidence runs with required maturity `planned`
- **THEN** the gate is non-passing for incomplete planned maturity
- **AND** every missing requirement, scenario, or field is named
- **AND** no synthetic selector, execution, or implementation claim is created.

### Requirement: Mapping Acceptance Provenance

The Requirements module SHALL validate provider-neutral acceptance evidence against the canonical mapping digest before test-authored or stronger evidence satisfies strict policy. A complete acceptance record SHALL contain the matching mapping digest, an explicit decision, stable reviewer identity, reviewer role, timestamp, and immutable reference. Acceptance SHALL be a distinct maturity state and SHALL NOT be inferred from proposal readiness, test results, or implementation evidence.

#### Scenario: Accepted mapping enables test authoring

- **GIVEN** a complete planned mapping and an acceptance record with a matching mapping digest, accepted decision, stable reviewer identity, reviewer role, timestamp, and immutable reference
- **WHEN** evidence requires accepted maturity
- **THEN** it reports the mapping as accepted
- **AND** it may proceed to test-authored validation.

#### Scenario: Stale or unauditable acceptance remains blocking

- **GIVEN** acceptance is missing, rejected, incomplete, missing any required provenance field, or bound to another mapping digest
- **WHEN** accepted maturity or higher is required
- **THEN** the module emits a deterministic finding naming the invalid or missing field
- **AND** passing tests do not invent acceptance.

### Requirement: Deterministic Scenario Proof Plan

The Requirements module SHALL emit a deterministic machine-readable plan without executing tests. Every selected scenario SHALL carry stable requirement/scenario identity, declared product touchpoints, verification method, intent, observable, and—at test-authored maturity and above—an exact structured selector with supported runner and repository-contained test identity. The plan SHALL bind the selected source revisions and canonical mapping digest, and reconciliation SHALL bind to that exact emitted plan. The module SHALL emit no shell command.

#### Scenario: Stable inputs produce a stable plan

- **GIVEN** unchanged selected sources, mappings, touchpoints, methods, intents, observables, and exact selectors
- **WHEN** planning repeats
- **THEN** ordered plan content and plan identity are byte-stable
- **AND** every scenario is only declared or selected
- **AND** no execution or chronology claim is emitted.

#### Scenario: Unsafe selector is rejected

- **GIVEN** a selector escapes the repository, starts with option syntax, contains control/shell/wildcard syntax, uses an unsupported runner, or is not an exact test identity
- **WHEN** planning validates it
- **THEN** the plan is non-executable under strict policy
- **AND** a bounded invalid-selector finding is emitted
- **AND** no command string is emitted.

#### Scenario: Selected scenario lacks executable proof mapping

- **GIVEN** a selected scenario at test-authored or stronger maturity has no valid exact selector
- **WHEN** plan completeness is evaluated
- **THEN** strict policy is non-passing with a scenario-unverified finding
- **AND** advisory policy retains the same finding without claiming proof.

### Requirement: Current-Run JUnit Reconciliation

The Requirements module SHALL reconcile a previously emitted deterministic plan with trusted current-run JUnit without starting tests. For pytest, every trusted result identity SHALL be the exact collected node ID in the dedicated canonical `specfact.selector` JUnit property; display name, class name, or approximate path/name matching SHALL NOT establish identity. Every required selector SHALL match exactly one result.

`current_execution` SHALL bind the accepted mapping digest, plan identity/digest, selected source revisions/trees, exact selector set, JUnit digest, runner/environment provenance, collection counts, and exact outcomes. Each supplied identity SHALL exactly equal its counterpart in the accepted emitted plan and execution request; any mismatch is non-passing. Current execution SHALL finalize independently from historical evidence.

#### Scenario: Every exact selector passes in the current run

- **GIVEN** trusted JUnit contains exactly one canonical `specfact.selector` property and one passing result for every exact selector in the accepted plan, with matching mapping/plan/source identities
- **WHEN** final current-run reconciliation executes
- **THEN** `current_execution` is pass and binds all current-run provenance
- **AND** the mandatory R07 chronology placeholder remains `status: not_evaluated` with `reason: capsule_not_supplied`
- **AND** the report does not say passing-after-red or change-proven.

#### Scenario: JUnit plan or source identity does not match

- **GIVEN** otherwise passing JUnit is bound to a different mapping digest, plan identity/digest, source revision/tree, or selector set than the accepted execution plan
- **WHEN** final current-run reconciliation executes
- **THEN** `current_execution` does not pass
- **AND** every mismatched identity is named
- **AND** chronology cannot replace the rejected current result.

#### Scenario: Declared test is absent from results

- **GIVEN** an accepted plan whose required exact selector is not collected
- **WHEN** reconciliation runs
- **THEN** current execution remains non-passing with an uncollected-test finding
- **AND** diagnostics are preserved under strict policy.

#### Scenario: Result cannot be trusted or matched

- **GIVEN** malformed JUnit, a missing or mismatched `specfact.selector` property, display/class-name-only identity, duplicate or ambiguous selector identity, or failed, errored, or skipped result
- **WHEN** reconciliation runs
- **THEN** it never upgrades the affected selector or scenario to passed
- **AND** deterministic findings distinguish every failure class
- **AND** chronology cannot substitute for the current result.

### Requirement: Historical Chronology Is a Separate Claim

New historical red-to-green claims SHALL be accepted only through the later R08 bounded replay contract. R07 SHALL NOT infer chronology from current maturity, current JUnit, static Python/pytest analysis, or a newly generated legacy ledger.

#### Scenario: R07 finalizes without chronology input

- **GIVEN** corrected R07 current execution is final and R07 has no chronology-request or capsule input
- **WHEN** the schema-v3 report is finalized
- **THEN** current execution retains its exact status
- **AND** the R07 chronology placeholder uses `status: not_evaluated` with `reason: capsule_not_supplied`
- **AND** no broader proof label is emitted.

#### Scenario: Legacy artifact is read for compatibility

- **GIVEN** a finalized report v2 contains an explicitly labelled legacy-ledger basis
- **WHEN** compatibility reading occurs
- **THEN** the historical label remains migration-only with `source_schema_version: 2`
- **AND** it is not converted into a v3 claim, new R08 attestation, or chronology pass.
