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

The Requirements module SHALL accept a versioned capsule from the trusted core replay boundary and validate its schema, canonical artifact hash links, full B/R/H/D commit and tree identities, B < R < H <= D ancestry facts, D equality with the delivered-head identity, all three transition manifests/digests and path-role sets, frozen mapping/plan/selectors/failing-before evidence at R, exact fail-at-R/pass-at-H/remain-pass-at-distinct-D outcomes, runner/toolchain/dependency/environment/plugin/network-policy identities, timestamps/resource bounds, signed module identity, policy identity, and verifier epoch. The module SHALL NOT execute Git, pytest, or subprocesses.

B..R SHALL contain only declared red-setup touchpoints, including the accepted proof mapping and failing-before TDD record. R..H SHALL contain only declared implementation touchpoints. H..D SHALL contain only exact declared delivery-evidence touchpoints for the governed change's `TDD_EVIDENCE.md` and `CHANGE_VALIDATION.md`.

#### Scenario: Valid capsule proves bounded chronology

- **GIVEN** a complete trusted capsule whose identical selectors failed as declared at R, passed at H, and remained passing at distinct D
- **AND** D equals the delivered head
- **AND** every transition classification satisfies its accepted closed path policy
- **WHEN** chronology reconciliation runs
- **THEN** chronology passes with the capsule digest and verifier epoch
- **AND** current execution retains its own status.

#### Scenario: Capsule identity, transition, or outcome is invalid

- **GIVEN** non-ancestral refs, a mismatched delivered head, mismatched trees/digests, changed frozen red inputs, an undeclared path/rename, a non-implementation R..H path, a non-evidence H..D path, selector/outcome mismatch, missing mandatory field, untrusted signed module, or untrusted epoch
- **WHEN** validation runs
- **THEN** chronology is failed or unknown according to the deterministic failure class
- **AND** strict policy does not pass.

### Requirement: Bounded Chronology Claim

A passing chronology SHALL state exactly: "These declared selectors failed at R, passed at H, and still passed at delivery head D; only declared implementation touchpoints changed from R to H and only declared delivery-evidence touchpoints changed from H to D." It SHALL also state that stakeholder-intent completeness, complete runtime dependency closure, code quality, correctness, and absence of defects were not proven.

#### Scenario: Runtime observation is attached as advisory context

- **GIVEN** the capsule includes a runtime observation manifest
- **WHEN** the report is built
- **THEN** the observation may be retained as a fact from those executions
- **AND** it is not labelled a complete possible dependency set.

### Requirement: Fail-Closed Untrusted Chronology

Missing, incomplete, unsupported, hash-mismatched, path-policy-invalid, outcome-invalid, delivery-mismatched, or untrusted capsules SHALL produce unknown/unproven chronology and a non-passing strict policy result. They SHALL NOT become pass, skip, no-impact, or current-execution failure.

#### Scenario: Mandatory capsule fact is unavailable

- **GIVEN** a mandatory identity, transition, selector, result, environment, network, signed-module, policy, artifact-link, or verifier fact is unavailable
- **WHEN** chronology is requested under strict policy
- **THEN** the report names the missing fact and remediation
- **AND** chronology is non-green
- **AND** current execution remains independently represented.
