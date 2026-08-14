## ADDED Requirements

### Requirement: Independent Current Execution and Chronology

The finalized Requirements report SHALL use `schema_version: "4"` and represent `current_execution` and `red_green_chronology` as separate versioned claims with independent status, provenance, evidence references, and limitations. Neither claim SHALL silently imply, replace, downgrade, or upgrade the other. Reconciliation SHALL accept an explicit versioned `chronology_request` input with exactly `not_requested` or `required`; the public CLI SHALL expose `--chronology-request not-requested|required` and default to `not-requested` only for backward-compatible current-execution calls. The chronology field SHALL always be present: `not_requested` with no capsule uses `status: not_evaluated` and `reason: capsule_not_supplied`; `required` with no capsule uses `status: unknown` with deterministic diagnostics and a non-passing strict result. A supplied capsule requires `chronology_request: required`; the contradictory `not_requested` plus capsule combination SHALL be rejected before reconciliation. Mapping sidecars remain schema v2. Finalized report v2 is legacy-only; finalized report v3 is the R07 compatibility format and may omit `chronology_request` but MUST contain both R07 claim objects; v4 MUST contain request state, both claim objects, and all R08 provenance. Field omission SHALL NOT downgrade a v4 payload.

#### Scenario: Current execution passes without chronology

- **GIVEN** finalized passing current-run evidence and no replay capsule
- **WHEN** the report is produced
- **THEN** current execution remains pass
- **AND** chronology uses `status: not_evaluated` with `reason: capsule_not_supplied`
- **AND** no passing-after-red label is emitted.

#### Scenario: Chronology is explicitly required but unavailable

- **GIVEN** `chronology_request: required` and no replay capsule
- **WHEN** reconciliation runs
- **THEN** current execution remains independently represented
- **AND** chronology uses `status: unknown` with deterministic missing-capsule diagnostics
- **AND** strict chronology policy does not pass.

#### Scenario: Request and capsule inputs contradict

- **GIVEN** `chronology_request: not_requested` and a replay capsule
- **WHEN** reconciliation input is validated
- **THEN** the invocation is rejected before reconciliation
- **AND** no Requirements report is emitted.

### Requirement: Trusted Replay Capsule Validation

The Requirements module SHALL accept a versioned capsule from the trusted core replay boundary and validate its schema, canonical artifact hash links, full B/R/H/D commit and tree identities, structural B < R < H <= D ancestry facts, D equality with the delivered-head identity, and distinct H/D identities for a passing chronology. If D = H, chronology SHALL report `status: unknown`; assurance SHALL remain unproven. The capsule SHALL bind derived protected signed R/H checkpoint tag names/objects/annotations/signatures, approved issuer/trust identities, repository-ruleset identity, checkpoint-policy epoch, an accepted positive fresh checkpoint-attempt identity, all three transition manifests/digests and path-role sets, exactly one frozen failing/readiness section with R/D bytes and digests plus equality results, frozen mapping/plan/selectors/expected-failure identities/failing-before/readiness-validation evidence at R, exact mapped expected-failure-ID-at-R/pass-at-H/remain-pass-at-distinct-D outcomes, canonical observed red failure IDs and their digest, runner/toolchain/dependency/environment/plugin/network-policy identities, timestamps/resource bounds, signed module identity, policy identity, and verifier epoch. The module SHALL validate checkpoint object/signature/trust hash links supplied by core but SHALL NOT resolve Git refs or execute Git, pytest, or subprocesses.

B..R SHALL contain only declared red-setup touchpoints, including the accepted proof mapping, failing-before TDD record, and governed `CHANGE_VALIDATION.md` pre-R readiness section. The marked readiness-section bytes SHALL remain frozen through D; the file MAY be extended only outside those markers in H..D under its separate delivery-evidence role. R..H SHALL contain only declared implementation touchpoints. H..D SHALL contain only exact declared delivery-evidence touchpoints for the governed change's `TDD_EVIDENCE.md` and `CHANGE_VALIDATION.md`. D SHALL retain exactly one byte-identical `specfact:frozen-failing` section and one byte-identical `specfact:frozen-readiness` section from R; appended delivery evidence SHALL be outside those markers.

#### Scenario: Valid capsule proves bounded chronology

- **GIVEN** a complete trusted capsule with valid protected signed R/H checkpoint bindings whose identical selectors each emitted exactly one canonical red marker matching the frozen mapped `expected_failure_id` at R, passed at H, and remained passing at distinct D
- **AND** D equals the delivered head
- **AND** every transition classification satisfies its accepted closed path policy
- **WHEN** chronology reconciliation runs
- **THEN** chronology passes with the capsule digest and verifier epoch
- **AND** current execution retains its own status.

#### Scenario: Capsule status class is deterministic

- **GIVEN** a required capsule has an invalid identity, transition, trust, or outcome condition
- **WHEN** validation runs
- **THEN** a missing, unreadable, incomplete, unsupported, or unverifiable mandatory fact; trust/signature/issuer/ruleset/epoch that cannot be established; verifier/tool failure; or identical H/D produces `status: unknown`
- **AND** a complete trusted verified contradiction of ancestry, delivered-head/tree/digest equality, checkpoint-attempt freshness/non-reuse, closed path policy, frozen-section equality, selector/failure identity, or fail-at-R/pass-at-H/pass-at-D outcome produces `status: fail`
- **AND** strict policy does not pass.

### Requirement: Bounded Chronology Claim

A passing chronology SHALL state exactly: "These declared selectors failed at R, passed at H, and still passed at delivery head D; only declared implementation touchpoints changed from R to H and only declared delivery-evidence touchpoints changed from H to D." It SHALL also state that stakeholder-intent completeness, complete runtime dependency closure, code quality, correctness, and absence of defects were not proven.

#### Scenario: Runtime observation is attached as advisory context

- **GIVEN** the capsule includes a runtime observation manifest
- **WHEN** the report is built
- **THEN** the observation may be retained as a fact from those executions
- **AND** it is not labelled a complete possible dependency set.

### Requirement: Fail-Closed Untrusted Chronology

`chronology_request: required` with a missing capsule, or a supplied capsule whose mandatory evidence is unavailable, unreadable, incomplete, unsupported, unverifiable, or cannot establish required trust, SHALL produce `status: unknown` with unproven assurance and a non-passing strict-policy result. `D = H` is the explicit complete-but-insufficient exception and also SHALL remain unknown. A complete trusted capsule whose verified facts contradict an ancestry, delivered-head/tree/digest equality, checkpoint-attempt freshness/non-reuse, closed path, frozen-section equality, selector/failure identity, or fail/pass/pass outcome requirement SHALL produce `status: fail`. `chronology_request: not_requested` with no capsule SHALL produce the mandatory `status: not_evaluated` / `reason: capsule_not_supplied` claim; `not_requested` with a capsule is an invalid invocation rejected before reconciliation. No non-green chronology state SHALL become pass, skip, no-impact, or current-execution failure.

#### Scenario: Mandatory capsule fact is unavailable

- **GIVEN** a mandatory identity, checkpoint tag/object/signature/issuer/trust/ruleset/epoch binding, positive fresh non-reused `checkpoint_attempt`, transition, selector, expected/observed red failure identity, result, environment, network, signed-module, policy, artifact-link, or verifier fact is unavailable
- **WHEN** chronology is requested under strict policy
- **THEN** the report names the missing fact and remediation
- **AND** chronology uses `status: unknown` with unproven assurance
- **AND** current execution remains independently represented.

#### Scenario: Complete trusted capsule contradicts policy

- **GIVEN** every mandatory fact and trust binding is available and verified, H and D are distinct, and at least one verified ancestry, identity/hash equality, checkpoint-attempt, closed-path, frozen-section, selector/failure-identity, or fail/pass/pass outcome requirement is false
- **WHEN** chronology is requested under strict policy
- **THEN** chronology uses `status: fail` with the exact contradiction
- **AND** current execution remains independently represented.
