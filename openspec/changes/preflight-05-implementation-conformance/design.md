## Context

This paired modules change executes the released core implementation-assurance contracts throughout development and at final delivery. It keeps `specfact preflight run`, local checkpoints, and immutable-range conformance as distinct result lifecycles so approval identity, local feedback, and PR authority cannot be confused.

## Goals / Non-Goals

**Goals:**

- Catch seal/scope/test mismatches and known semantic boundary defects before a PR.
- Reuse Requirements exact selectors, C14 scope/capsule identities, and code-review JSON rather than duplicate analyzers.
- Return one compact remediation contract to the current coding agent with bounded reruns.
- Preserve explicit unknowns and distinct local versus range authority.

**Non-Goals:**

- Invoke an LLM or network from the deterministic CLI.
- Generate tests, edit implementation, or mutate/reseal the approved contract.
- Replace platform CI, protected PR review, security analysis, or architecture judgment.

## Decisions

### 1. Separate checkpoint and conformance commands

`specfact preflight checkpoint <change-id>` accepts `slice` with `worktree` or `index`, `commit` with `index` only, and `deep` with `worktree` or `index`. Any other scope/profile pair is rejected before extraction rather than silently overriding the requested scope. It returns the released core `DevelopmentCheckpointResult` with local authority. `specfact preflight conform <change-id>` discovers the policy-authorized canonical lineage tip, verifies that the selected seal digest/monotonic sequence and complete predecessor chain match that tip, and rejects ancestor, rolled-back, forked, missing, or ambiguous tip state. It requires its base commit/tree to equal the first seal's immutable implementation-lineage origin rather than a successor's later source snapshot, uses C14 to attest origin-to-head ancestry, and requires the head commit/tree to equal a separately policy-authorized current delivery target. Local runs resolve the current delivery ref/HEAD; protected PR/CI runs consume an authenticated target supplied by their orchestrator without adding network access to the CLI. It extracts the complete cumulative lineage-origin-to-current-delivery-head manifest and range-bound evidence, derives the exhaustive affected final-delivery obligation closure, and invokes the core comparator. It preserves `FAIL` and `UNKNOWN` rather than synthesizing success from immutable references, an ancestor seal, a current-seal or caller-selected shorter range, an older descendant head, or prior local evidence. An applicable `ci`-stage obligation can pass only with authenticated evidence from a seal/policy-authorized protected-CI producer bound to that exact range; otherwise conform remains `UNKNOWN`/deferred. Neither command changes the seal.

### 2. Three bounded checkpoint profiles

- `slice` verifies the seal, compares the complete changed-path/input manifest and snapshot-bound public-interface delta with sealed roles and influence mappings, runs affected exact Requirements cases, and imports changed-scope code-review evidence.
- `commit` requires the index snapshot, includes applicable `slice` checks, adds every affected component's bounded pytest targets, and is the pre-commit profile.
- `deep` includes all lower-profile checks applicable to its worktree or index snapshot, bounded bug-hunt analysis, and all locally executable `prepush` obligations. `ci` obligations are reported as deferred with identity and reason, never silently passed.

V1 invokes pytest through the active Python environment using repository-contained selectors. Other runners remain later adapters.

### 3. C14 provides scope and execution identity

Worktree and index extraction reuses C14 scope, sandbox, and toolchain primitives and implements the released core matrix exactly. Every snapshot base is the seal-bound implementation-lineage origin repository/base commit/base tree. A worktree snapshot additionally binds a worktree-manifest digest and includes staged, unstaged, and untracked state. An index snapshot additionally binds the exact index tree ID; untracked paths are absent unless staged as additions. A range snapshot binds full head commit/tree, separately authorized current delivery-target commit/tree, and origin-to-head ancestry; untracked paths are not representable. Every manifest retains additions, deletions, both rename endpoints, before/after modes, symlink target identity, and byte-preserving path identity. Rename classification is bound to producer, toolchain, and policy identity. For each affected source path that policy classifies as capable of defining a public interface, a policy-authorized extractor normalizes base/current public-interface observations into the released core snapshot records and binds extractor identity/version/configuration digest, toolchain/policy, path, and exact snapshot provenance. Changed interfaces are derived by deterministic record comparison; missing, incomplete, unsupported, stale, ambiguous, or wrong-snapshot extraction returns `UNKNOWN`, and a caller-supplied empty set is never authoritative. Index claims execute against the captured index capsule; a differing worktree cannot satisfy staged evidence.

### 4. Seal-bound semantic selection

Every changed non-excluded sealed role, derived public interface, or input—not only source paths—maps through approved ownership and influence relationships to existing Requirements verification cases, bounded component pytest targets, and review/evidence obligations. This includes `source`, `test`, `docs`, `generated`, and `evidence` paths plus seal-bound approval, test, dependency, policy, toolchain, and relevant configuration inputs. Approval-state discovery compares the authoritative base with the selected worktree/index snapshot; deletion, relocation, or replacement of the last seal or canonical lineage-tip artifact is therefore a governed transition that returns `UNKNOWN`, never evidence that the repository was never sealed. A checkpoint may select only the affected subset of requirement, scenario, verification-case, and exact pytest-selector identities already bound by the seal. An exact-input, exact-role no-impact disposition from the current valid canonical seal is a determinate empty semantic-selector result only when it has a non-empty rationale and retained identity/digest plus validation evidence; it does not bypass seal, scope, approval-state, or interface checks. Missing, stale, ambiguous, or mismatched no-impact evidence returns `UNKNOWN`. Otherwise, if an applicable changed path/interface/input or the obligations it influences cannot be derived deterministically, selection returns `UNKNOWN`; it never accepts an empty affected set by default. Final conformance has no discretionary subset: it deterministically closes over every changed governed path and interface plus every applicable component, acceptance criterion, risk row, Requirements case, component target, verification stage (including `ci`), exclusion, and no-impact disposition bound to the affected range. The closure and its digest are result-bound. An incomplete, empty-for-an-affected-range, duplicate, or ambiguous closure produces `UNKNOWN`; determinate unsatisfied obligations produce `FAIL`. Any addition, removal, replacement, or change of a seal-bound identity returns to preflight validation and reapproval. Missing ownership, stale plan identity, invalid/uncollected selectors, ambiguous scope, or unavailable required evidence produces `UNKNOWN`. Work outside sealed roles produces `FAIL` and routes intentional expansion to preflight reapproval.

### 5. Evidence aggregation and cache identity

The runtime supplies the upstream design contract, validation result, seal, policy, and current source identities to core verification before selecting implementation obligations. It imports current-run JUnit and `specfact code review run` JSON and delegates mutually exclusive finding classification, precedence, and status aggregation to released core interfaces. Cache reuse requires exact seal, snapshot, obligation-set, pytest-target, runner, policy, toolchain, relevant configuration, and execution-environment digests. The execution-environment digest attests the Python executable/version/ABI, environment-manager provenance, resolved installed-distribution or sealed lock/artifact identities, and policy-allowlisted relevant environment-variable names with hashed values; secret values are never persisted. Any identity change invalidates the cache. If this state cannot be attested, cache reuse is disabled and required checks rerun; unavailable required execution returns `UNKNOWN`.

### 6. Seal-aware pre-commit rollout

The pre-commit wrapper classifies every staged path against repository preflight-governance policy and sealed `source`, `test`, `docs`, `generated`, `evidence`, and `excluded` roles plus seal-bound approval, test, dependency, policy, toolchain, and relevant configuration inputs. It auto-selects only when exactly one policy-authorized canonical lineage tip covers every staged non-excluded governed path/input; historical predecessor seals in that verified chain do not count as competing tips. `NOT_APPLICABLE` is limited to an empty staged set, paths deterministically outside the configured preflight-governed universe and unrelated to every current or prior seal, or a repository whose authoritative base and selected snapshot both contain no approval state and whose staged transition changes no approval artifact. A base seal/tip deleted, relocated, or replaced in the index is governed missing approval state and returns `UNKNOWN`/exit one; index-only discovery cannot reinterpret it as a never-sealed repository. When seals exist, a governed path/input with no seal coverage is `unexpected`/`FAIL`; missing or ambiguous influence mapping under a covering seal is `UNKNOWN`. If any staged path associates with a seal but another non-excluded seal-relevant path is uncovered, the uncovered path is `unexpected`, the result is `FAIL`, and intentional expansion returns to preflight refinement with a successor seal that preserves the original implementation-lineage origin. Multiple applicable lineages/tips, stale/rolled-back/forked tip state, ambiguous Git state, missing ownership, or missing required evidence is `UNKNOWN` and exits one. Dogfood begins in shadow mode with negative defect fixtures and representative known-green controls for every enabled scope/profile pair. Blocking requires exact expected corpus results, zero false PASS, zero corpus false block, no destructive/ambiguous behavior, and at least 100 applicable known-good live shadow observations with a false-block rate no greater than 1%; policy may only make that threshold stricter.

### 7. Compact bounded agent handoff

Each finding packet contains a stable fingerprint, action class (`fix_implementation`, `fix_or_add_test`, `rerun`, `return_to_preflight`, or `human_decision`), contract/risk reference, implementation evidence, expected observable, recommended action, and validation selectors. The harness-neutral workflow may hand packets to the current coding agent for at most three fix/rerun cycles. It stops on a repeated consecutive fingerprint, scope expansion, `UNKNOWN`, contract/design judgment, or requested sealed-artifact change.

### 8. Post-merge publication precedes adapters

The implementation PR prepares the version, manifest bindings, and compatibility proof but produces no publishable feature-branch identity. After that implementation is merged to `dev`, only the canonical post-merge workflow may generate, sign, verify, and propose the immutable #434 module, registry, checksum, signature, and history artifacts. The signed manifest separately binds the existing preflight workflow identity/digest and the new implementation-check workflow identity/digest; the latter owns checkpoint, conform, and bounded remediation semantics. After the publication PR merges and official registry/install readback passes, #434 hands the exact module and workflow identities to core #251 only. Completed #251 then enables #253; only completed #251 and #253 enable modules #433. #434 does not package adapters or authorize parallel #433 consumption.

## Risks / Trade-offs

- **Incomplete risk matrix:** Preflight validators block missing dispositions and checkpoint preserves unknown evidence.
- **Slow component selection:** Use slice/commit/deep profiles and digest-bound cache; never fall back silently to a full repository suite.
- **Local/CI divergence:** Keep `ci` obligations deferred and retain protected PR/CI authority.
- **Looping token cost:** Cap workflow cycles at three and stop repeated fingerprints.
- **Duplicate ownership:** Import Requirements, C14, and code-review contracts instead of creating parallel schemas.

## Migration and Rollback

Dogfood is shadow-only until both negative and known-green controls plus the minimum live sample satisfy the promotion policy. Stable rollout blocks pre-commit only for repositories with an applicable valid seal. Rollback removes the hook/workflow checkpoint entry and published update; existing seals, Requirements evidence, code review, and final PR gates remain valid. Ephemeral checkpoint artifacts may be deleted without changing approval identity.

## Open Questions Deferred to Implementation

- Exact released core class/module names and canonical serialization library established by #682/#684 tests.
- Retention limit for explicitly persisted checkpoint history; ephemeral output remains the default.
