## Context

Core is the trusted Git/execution boundary; Requirements modules are the semantic evidence boundary. The capsule connects them without making modules a Git/test orchestrator or making core reinterpret Requirements status.

B, R, and H are the three proof commits: merge base, red checkpoint, and green implementation checkpoint. D is the delivered-head binding required because repository policy commits passing-after evidence after H.

## Decisions

### Keep current execution and chronology independent

The report carries separate `current_execution` and `red_green_chronology` claims. Chronology may reference current execution but cannot replace, erase, inflate, or downgrade it. A valid current run with no capsule remains a valid current observation with unproven/not-evaluated chronology.

### Validate a content-addressed B/R/H/D capsule

The versioned capsule requires:

- B/R/H/D commit and tree identities, B < R < H <= D ancestry facts, and D equality with the delivery identity;
- derived protected signed R/H checkpoint tag names, tag-object identities, canonical annotations, signatures, approved issuer/trust identities, repository-ruleset identity, and checkpoint-policy epoch;
- B..R, R..H, and H..D changed-path and rename manifests plus canonical digests;
- exactly one frozen failing-before section and one frozen readiness section, their R/D bytes and digests, and equality results;
- accepted red-setup, implementation, and delivery-evidence touchpoint sets;
- mapping and plan digests, exact selectors, one stable opaque mapped `expected_failure_id` per selector, frozen failing-before evidence identity, and frozen pre-R readiness-validation evidence identity;
- red, green-checkpoint, and delivery JUnit digests plus exact selector outcomes, canonical observed red failure IDs, and their digest;
- runner, toolchain, dependency, environment, plugin-autoload, network-policy, policy, and verifier identities/results;
- verifier epoch, timestamps, timeouts/resource bounds, and retained artifact hash links;
- signed module repository, commit, tree, package version, manifest integrity, signer, and signature identities.

Core resolves and validates Git/checkpoint/execution facts under its pinned verifier. Modules validate the capsule's checkpoint object/signature/trust hash links, schema, canonical hashes, transition classifications, selector equality, exact mapped/observed red failure-identity equality, outcome rules, trusted module identity, and verifier/policy epoch. Modules do not recompute Git facts or run tests.

### Use three closed transition policies

B..R may contain only declared requirements/specifications/tests/test harness/configuration, the accepted proof mapping, the failing-before TDD evidence record, and the governed `CHANGE_VALIDATION.md` pre-R readiness section. It may not contain governed implementation, dependencies, workflows, runners, verifier/policy/schema changes, other generated artifacts, or unclassified paths. The mapping, plan, selectors, expected-failure identities, path sets, failing evidence, and readiness evidence are frozen at R. `CHANGE_VALIDATION.md` may be extended only in H..D under its separate delivery-evidence role.

R..H may change only declared implementation touchpoints. A selected test, helper, fixture, conftest, test configuration, dependency lock, proof runner, workflow, mapping, plan, evidence record, policy, schema, or unclassified path invalidates chronology and requires a new R.

When D differs from H, H..D may change only the governed change's exact mapped `TDD_EVIDENCE.md` and `CHANGE_VALIDATION.md` delivery records. Any behavior, test, configuration, mapping, runner, workflow, policy, schema, other documentation, generated runtime input, or unclassified change is invalid. The identical selectors must remain passing at D. The capsule must also prove that D contains exactly one byte-identical `specfact:frozen-failing` section and one byte-identical `specfact:frozen-readiness` section from R; append-only content may exist only outside those markers.

### State only the bounded claim

The chronology text is fixed:

> These declared selectors failed at R, passed at H, and still passed at delivery head D; only declared implementation touchpoints changed from R to H and only declared delivery-evidence touchpoints changed from H to D.

Limitations state that stakeholder-intent completeness, complete runtime dependencies, code quality, correctness, and absence of defects were not proven.

### Missing trust is unknown/unproven

An incomplete, mismatched, unsupported, untrusted, or checkpoint-authority-invalid capsule never produces pass/no-impact. Strict chronology policy fails after returning deterministic diagnostics. Runtime observations may be advisory facts but cannot claim complete dependency scope.

### Verifier epochs prevent self-authorization

The capsule identifies a previously promoted verifier/policy epoch. A candidate schema, verifier, workflow, fixture, or policy cannot establish its own trusted status; it remains shadow evidence until independently promoted.

## Implementation Boundary

Implementation is limited to the typed capsule validator in new `requirements/replay_proof.py`, narrow Requirements lifecycle/command/status integration, provenance-only Code Review adaptation, focused fixtures/tests, docs, and generated signed release outputs. Modules must not add Git worktrees, pytest execution, subprocesses, or static dependency inference.

## Rollout and Rollback

1. Verify issue #414 metadata and both paired contracts.
2. Add failing capsule/reconciliation tests.
3. Implement the typed schema and dual-write report fields.
4. Publish a signed release through existing registry/signing generators for core shadow adoption.
5. Promote the initial verifier epoch independently.
6. Enable strict chronology only after benchmark validation.
7. Roll back chronology enforcement without disabling current-run evidence.
