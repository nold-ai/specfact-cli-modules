## Context

Core is the trusted execution boundary; Requirements modules are the semantic evidence boundary. The capsule connects them without making modules a Git/test orchestrator or making core reinterpret Requirements status.

## Decisions

### Keep current execution and chronology independent

The report carries separate `current_execution` and `tdd_chronology` claims. Chronology may reference current execution but cannot replace it. A valid current run with no capsule remains a valid current observation with unproven/not-evaluated chronology.

### Validate a content-addressed replay capsule

The versioned capsule includes B/R/H commits and trees; ancestry facts; B..R and R..H changed-path/rename manifests and digests; allowed implementation touchpoints; mapping/plan/selector identities; red/final JUnit digests and exact outcomes; runner/toolchain/environment/policy identities; verifier identity/epoch; resource limits; and hash links to retained artifacts.

Core asserts Git and execution facts under its pinned verifier. Modules validate schema, hash links, allowed transition classifications supplied by the accepted mapping/policy, selector equality, outcome rules, and trusted verifier/policy identities.

### Use a conservative transition contract

B..R may contain requirement/spec/test changes but no governed implementation touchpoint. R..H may change only declared implementation touchpoints. A selected test, helper, fixture, conftest, pytest configuration, dependency lock, proof runner, workflow, mapping, plan, policy, schema, or unclassified path after R invalidates chronology and requires a new R.

### State only the bounded claim

The chronology text is fixed: "These declared selectors failed at R and passed at H while only declared implementation touchpoints changed." Limitations state that intent completeness, complete runtime dependencies, code quality, and defect absence were not proven.

### Missing trust is unknown/unproven

An incomplete, mismatched, unsupported, or untrusted capsule never produces pass/no-impact. Strict chronology policy fails after returning deterministic diagnostics. Runtime observations may be advisory facts but cannot claim complete dependency scope.

### Verifier epochs prevent self-authorization

The capsule identifies a previously promoted verifier/policy epoch. A candidate schema, verifier, workflow, or policy cannot establish its own trusted status; it remains shadow evidence until independently promoted.

## Implementation Boundary

Later implementation is limited to typed capsule/report models, reconciliation, public input options, focused fixtures/tests, docs, and release metadata. Modules must not add Git worktrees, pytest execution, or static dependency inference.

## Rollout and Rollback

1. Add failing capsule/reconciliation tests.
2. Implement the typed schema and dual-write report fields.
3. Publish a signed release for core shadow adoption.
4. Promote the initial verifier epoch independently.
5. Enable strict chronology only after benchmark validation.
6. Roll back chronology enforcement without disabling current-run evidence.

