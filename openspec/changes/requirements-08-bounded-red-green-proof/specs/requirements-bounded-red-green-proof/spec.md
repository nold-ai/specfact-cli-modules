## ADDED Requirements

### Requirement: Independent Current Execution and Chronology

The Requirements report SHALL represent `current_execution` and `tdd_chronology` as separate versioned claims with independent status, provenance, evidence references, and limitations. Neither claim SHALL silently imply, replace, downgrade, or upgrade the other.

#### Scenario: Current execution passes without chronology

- **GIVEN** finalized passing current-run evidence and no replay capsule
- **WHEN** the report is produced
- **THEN** current execution remains pass
- **AND** chronology is unproven or not evaluated
- **AND** no passing-after-red label is emitted.

### Requirement: Trusted Replay Capsule Validation

The Requirements module SHALL accept a versioned capsule from the trusted core replay boundary and validate its schema, artifact hash links, full B/R/H and tree identities, ancestry facts, transition manifests/digests, allowed implementation touchpoints, mapping/plan/selectors, exact red/final outcomes, runner/toolchain/environment/policy identities, and verifier epoch. The module SHALL NOT execute Git or tests.

#### Scenario: Valid capsule proves bounded chronology

- **GIVEN** a complete trusted capsule whose selectors failed as declared at R and all passed at H
- **AND** its transition classifications satisfy the accepted bounded path policy
- **WHEN** chronology reconciliation runs
- **THEN** chronology passes with the capsule digest and verifier epoch
- **AND** current execution retains its own status.

#### Scenario: Capsule identity or transition is invalid

- **GIVEN** non-ancestral refs, mismatched trees/digests, changed selector/plan, frozen harness change, undeclared path, outcome mismatch, or untrusted epoch
- **WHEN** validation runs
- **THEN** chronology is failed or unknown according to the deterministic failure class
- **AND** strict policy does not pass.

### Requirement: Bounded Chronology Claim

A passing chronology SHALL state exactly: "These declared selectors failed at R and passed at H while only declared implementation touchpoints changed." It SHALL also state that stakeholder-intent completeness, complete runtime dependency closure, code quality, correctness, and absence of defects were not proven.

#### Scenario: Runtime observation is attached as advisory context

- **GIVEN** the capsule includes a runtime observation manifest
- **WHEN** the report is built
- **THEN** the observation may be retained as a fact from those executions
- **AND** it is not labelled a complete possible dependency set.

### Requirement: Fail-Closed Untrusted Chronology

Missing, incomplete, unsupported, hash-mismatched, policy-invalid, or untrusted capsules SHALL produce unknown/unproven chronology and a non-passing strict policy result. They SHALL NOT become pass, skip, no-impact, or current-execution failure.

#### Scenario: Mandatory capsule fact is unavailable

- **GIVEN** a mandatory identity, transition, selector, result, environment, policy, or verifier fact is unavailable
- **WHEN** chronology is requested under strict policy
- **THEN** the report names the missing fact and remediation
- **AND** chronology is non-green
- **AND** current execution remains independently represented.

