## Context

Core is the trusted Git/execution boundary; Requirements modules are the semantic evidence boundary. The capsule connects them without making modules a Git/test orchestrator or making core reinterpret Requirements status.

B, R, and H are the three proof commits: merge base, red checkpoint, and green implementation checkpoint. D is the delivered-head binding required because repository policy commits passing-after evidence after H. The capsule schema can represent structural `H <= D` ordering, but a passing chronology requires a distinct delivery observation (`H < D`); `D = H` produces `status: unknown`; assurance remains unproven because the fixed remain-pass-at-D claim was not observed at a distinct delivery commit.

## Decisions

### Advance the finalized report to schema v4

R08 increments the finalized Requirements report from R07 schema v3 to `schema_version: "4"` because it adds the explicit chronology request and capsule/attestation semantics. Mapping sidecars remain schema v2. Finalized report v2 remains legacy-only; v3 is the corrected R07 compatibility format with both claims and no chronology-request field; v4 requires `chronology_request`, both claims, and all R08 provenance. A v3 report is normalized as compatibility `not_requested` only because the immutable v3 contract cannot express a chronology request, and the source version remains visible. Field absence never downgrades v4 to v3 or v2.

### Keep current execution and chronology independent

The report carries separate `current_execution` and `red_green_chronology` claims. Chronology may reference current execution but cannot replace, erase, inflate, or downgrade it. A valid current run, when chronology was not requested and no capsule was supplied, remains a valid current observation; the mandatory chronology claim object uses `status: not_evaluated` with `reason: capsule_not_supplied`.

### Make chronology intent an explicit input

Finalized report schema v4 reconciliation accepts the versioned `chronology_request` enum `not_requested|required`; the CLI exposes `--chronology-request not-requested|required` and defaults to `not-requested` for backward-compatible current-only calls. `not_requested` plus no capsule emits the canonical not-evaluated claim. `required` plus no capsule emits unknown and fails strict chronology policy. A capsule is accepted only with `required`; `not_requested` plus a capsule is rejected as contradictory input. Absence of a capsule is never used to guess caller intent.

### Validate a content-addressed B/R/H/D capsule

The versioned capsule requires:

- B/R/H/D commit and tree identities, structural B < R < H <= D ancestry facts, D equality with the delivery identity, and distinct H/D identities (`H < D`) for a passing chronology;
- derived protected signed R/H checkpoint tag names, tag-object identities, canonical annotations, signatures, approved issuer/trust identities, repository-ruleset identity, checkpoint-policy epoch, and accepted positive checkpoint-attempt identity;
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

A passing chronology requires D to differ from H. Before H is designated, every implementation, test, documentation, package metadata, changelog, generated registry/archive/checksum/signature artifact, and fix-producing gate change must be complete. For later changes whose signed publication uses the post-merge `publish-modules.yml` workflow, H may be designated only at the merged `dev` commit after its auto-publish PR and final gates, only if protected R remains a strict ancestor and every pre-H publication path is an explicitly declared R..H implementation touchpoint. Squash/rewritten ancestry or an undeclared publish path leaves chronology unproven and requires a new R. H..D may then change only the governed change's exact mapped `TDD_EVIDENCE.md` and `CHANGE_VALIDATION.md` delivery records. Any behavior, test, configuration, mapping, runner, workflow, policy, schema, other documentation, generated runtime input, release artifact, or unclassified change is invalid. The identical selectors must remain passing at D. The capsule must also prove that D contains exactly one byte-identical `specfact:frozen-failing` section and one byte-identical `specfact:frozen-readiness` section from R; append-only content may exist only outside those markers.

### State only the bounded claim

The chronology text is fixed:

> These declared selectors failed at R, passed at H, and still passed at delivery head D; only declared implementation touchpoints changed from R to H and only declared delivery-evidence touchpoints changed from H to D.

Limitations state that stakeholder-intent completeness, complete runtime dependencies, code quality, correctness, and absence of defects were not proven.

### Missing trust produces unknown status and unproven assurance

An incomplete, mismatched, unsupported, untrusted, checkpoint-authority-invalid, or same-H-and-D capsule never produces pass/no-impact. `chronology_request: required` with no capsule produces canonical `status: unknown` plus deterministic diagnostics and strict policy failure. Any supplied unavailable or untrusted capsule facts produce the same result. `D = H` is an insufficient distinct-delivery observation and always remains `status: unknown` with unproven assurance under strict policy; it is explicitly not a complete trusted contradiction. Only after excluding missing, untrusted, structurally insufficient, and same-H/D cases may another complete trusted semantic contradiction produce `status: fail`. `chronology_request: not_requested` with no capsule instead produces `status: not_evaluated` with `reason: capsule_not_supplied`; supplying a capsule in that mode is rejected before reconciliation. Runtime observations may be advisory facts but cannot claim complete dependency scope.

### Verifier epochs prevent self-authorization

The capsule identifies a previously promoted verifier/policy epoch. A candidate schema, verifier, workflow, fixture, or policy cannot establish its own trusted status; it remains shadow evidence until independently promoted.

## Implementation Boundary

Implementation is limited to the typed capsule validator in new `requirements/replay_proof.py`, narrow Requirements lifecycle/command/status integration, provenance-only Code Review adaptation, focused fixtures/tests, docs, and signed release outputs generated only by the post-merge canonical publish workflow. Modules must not add Git worktrees, pytest execution, subprocesses, or static dependency inference.

## Rollout and Rollback

1. Verify issue #414 metadata and both paired contracts.
2. Add failing capsule/reconciliation tests.
3. Implement the typed schema and dual-write report fields on a feature branch; the candidate makes no self-chronology claim and designates no H/D.
4. Merge the green implementation to `dev`; let the canonical `publish-modules.yml` workflow use the signing secret and open its generated auto-publish PR.
5. Require signed-artifact and full-gate verification on that auto-publish PR, merge it to `dev`, and promote the resulting verifier epoch independently.
6. Enable strict chronology only after benchmark validation.
7. Roll back chronology enforcement without disabling current-run evidence.
