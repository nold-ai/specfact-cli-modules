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

`specfact preflight checkpoint <change-id>` accepts only `--scope worktree|index` and `--profile slice|commit|deep`. It returns the released core `DevelopmentCheckpointResult` with local authority. `specfact preflight conform <change-id>` requires explicit immutable base/head identities and returns `ImplementationConformanceResult`. Neither command changes the seal.

### 2. Three bounded checkpoint profiles

- `slice` verifies the seal, compares the complete changed-path manifest with sealed roles, runs affected exact Requirements cases, and imports changed-scope code-review evidence.
- `commit` requires the index snapshot, adds every affected component's bounded pytest targets, and is the pre-commit profile.
- `deep` adds bounded bug-hunt analysis and all locally executable `prepush` obligations. `ci` obligations are reported as deferred with identity and reason, never silently passed.

V1 invokes pytest through the active Python environment using repository-contained selectors. Other runners remain later adapters.

### 3. C14 provides scope and execution identity

Worktree and index extraction reuses C14 scope, sandbox, and toolchain primitives and implements the released core matrix exactly. A worktree snapshot binds repository identity, full base commit ID, and worktree-manifest digest and includes staged, unstaged, and untracked state. An index snapshot binds repository identity, full base commit ID, and exact index tree ID; untracked paths are absent unless staged as additions. A range snapshot binds repository identity, full base/head commit IDs, and base/head tree IDs; untracked paths are not representable. Every manifest retains additions, deletions, both rename endpoints, before/after modes, symlink target identity, and byte-preserving path identity. Rename classification is bound to producer, toolchain, and policy identity. Index claims execute against the captured index capsule; a differing worktree cannot satisfy staged evidence.

### 4. Seal-bound semantic selection

Changed source paths map through sealed component ownership to existing Requirements verification cases and bounded component pytest targets. Selection may use only requirement, scenario, verification-case, and exact pytest-selector identities already bound by the seal. Any addition, removal, replacement, or change of a bound identity returns to preflight validation and reapproval. Missing ownership, stale plan identity, invalid/uncollected selectors, ambiguous scope, or unavailable required evidence produces `UNKNOWN`. Work outside sealed roles produces `FAIL` and routes intentional expansion to preflight reapproval.

### 5. Evidence aggregation and cache identity

The runtime supplies the upstream design contract, validation result, seal, policy, and current source identities to core verification before selecting implementation obligations. It imports current-run JUnit and `specfact code review run` JSON and delegates mutually exclusive finding classification, precedence, and status aggregation to released core interfaces. Cache reuse requires exact seal, snapshot, obligation-set, pytest-target, runner, policy, toolchain, and relevant configuration digests. Any identity change invalidates the cache.

### 6. Seal-aware pre-commit rollout

The pre-commit wrapper auto-selects only when exactly one valid seal covers every staged production path. No staged production path, or no seal associated with any staged production path, is `NOT_APPLICABLE` and exits zero. If at least one staged path associates with a seal but that seal does not cover every staged production path, the uncovered paths are `unexpected`, the result is `FAIL`, and intentional expansion returns to preflight refinement. Multiple/stale matching seals, ambiguous Git state, missing ownership, or missing required evidence is `UNKNOWN` and exits one. Dogfood begins in shadow mode; blocking is enabled only after the accepted corpus shows no false PASS or destructive behavior.

### 7. Compact bounded agent handoff

Each finding packet contains a stable fingerprint, action class (`fix_implementation`, `fix_or_add_test`, `rerun`, `return_to_preflight`, or `human_decision`), contract/risk reference, implementation evidence, expected observable, recommended action, and validation selectors. The harness-neutral workflow may hand packets to the current coding agent for at most three fix/rerun cycles. It stops on a repeated consecutive fingerprint, scope expansion, `UNKNOWN`, contract/design judgment, or requested sealed-artifact change.

### 8. Publication precedes adapters

The implementation versions, signs, compatibility-tests, and publishes one immutable #434 module release. Its signed manifest separately binds the existing preflight workflow identity/digest and the new implementation-check workflow identity/digest; the latter owns checkpoint, conform, and bounded remediation semantics. Core #251/#253 and modules #433 consume the exact module identity plus both named workflow identities and digests. #434 does not need an existing adapter and packages none.

## Risks / Trade-offs

- **Incomplete risk matrix:** Preflight validators block missing dispositions and checkpoint preserves unknown evidence.
- **Slow component selection:** Use slice/commit/deep profiles and digest-bound cache; never fall back silently to a full repository suite.
- **Local/CI divergence:** Keep `ci` obligations deferred and retain protected PR/CI authority.
- **Looping token cost:** Cap workflow cycles at three and stop repeated fingerprints.
- **Duplicate ownership:** Import Requirements, C14, and code-review contracts instead of creating parallel schemas.

## Migration and Rollback

Dogfood is shadow-only. Stable rollout blocks pre-commit only for repositories with an applicable valid seal. Rollback removes the hook/workflow checkpoint entry and published update; existing seals, Requirements evidence, code review, and final PR gates remain valid. Ephemeral checkpoint artifacts may be deleted without changing approval identity.

## Open Questions Deferred to Implementation

- Exact released core class/module names and canonical serialization library established by #682/#684 tests.
- Retention limit for explicitly persisted checkpoint history; ephemeral output remains the default.
