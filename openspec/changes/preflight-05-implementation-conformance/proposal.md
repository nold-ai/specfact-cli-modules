# Change: Seal-Bound Development Checkpoint and Conformance Runtime

## Why

Preflight approval records what was reviewed, but defects and mismatches can still accumulate while code is being written. SpecFact needs a cheap local checkpoint that maps the current implementation back to the sealed scope, risk, and test intent, returns compact remediation evidence to the coding agent before a PR, and preserves a distinct immutable-range conformance authority for delivery.

## What Changes

- **NEW**: `specfact preflight checkpoint <change-id> --scope worktree|index --profile slice|commit|deep` using the released core snapshot and checkpoint-result contracts.
- **NEW**: Complete Git path extraction by reusing C14 worktree/index/range scope and capsule primitives, plus policy-authorized snapshot-bound public-interface extraction using the released core records; missing or ambiguous interface discovery fails closed instead of accepting a caller-supplied empty set.
- **NEW**: Seal-bound selection of Requirements cases through the existing planned-to-test-authored maturity lifecycle, exact pytest selectors when test-authored, bounded affected-component pytest targets, and verified exact-input no-impact dispositions as explicit determinate empty selections; no second selector schema or implicit empty-set fallback.
- **NEW**: Import of current-run JUnit and `specfact code review run` evidence with cache identity bound to the seal, snapshot, selected obligations/targets, runner, policy, and configuration.
- **NEW**: `specfact preflight conform <change-id>` selects only the policy-authorized canonical latest seal and performs explicit cumulative implementation-lineage-origin-to-authoritative-current-delivery-head comparison across successor seals, with a separate final conformance result.
- **NEW**: Human/JSON parity, compact remediation packets, a harness-neutral implementation-check workflow with at most three fix/rerun cycles, and optional atomic persistence.
- **NEW**: Seal-aware staged pre-commit integration that validates canonical approval/Git identity before coverage, evaluates sealed approval state, tests, configuration, and evidence as well as source; distinguishes a never-sealed repository from staged removal of its last seal/tip by comparing authoritative base and index state; is non-applicable only for paths unrelated to every current or prior seal; fails closed for ambiguous applicable evidence; and requires both defect and known-green shadow controls plus pairwise and aggregate bounded live false-block rates bound to the exact promotion candidate before blocking rollout.
- **NEW**: After the implementation merges, use the canonical post-merge publication workflow to generate/version, sign, verify, compatibility-test, and propose one #434 module release identity that separately binds the existing preflight workflow identity/digest and the new implementation-check workflow identity/digest and raises matching bundle-manifest and registry `core_compatibility` lower bounds to the first released core containing #684. The identity becomes published only after the publication PR merges and official registry/install readback passes; only then enforce #434 -> #251 -> #253 -> #433.
- **CLARIFY**: The deterministic CLI never invokes an LLM, edits implementation, mutates/reseals a contract, or promotes local evidence to protected PR authority.

## Capabilities

### New Capabilities

- `preflight-implementation-conformance-runtime`: Worktree/index checkpoints, immutable range conformance, evidence selection/execution/import, rendering, persistence, pre-commit integration, and bounded agent handoff.

### Modified Capabilities

(none)

## Impact

- Planning artifacts only in this phase. No production code, tests, package, manifest, signature, version, workflow asset, hook, generated snapshot/result, adapter, or dependency is created.
- Implementation begins only after the stable #432 preflight handoff and released core #684 contracts.
- External Codex/ECC/hatch3r packaging remains in #433, which consumes the signed module identity and both separately named workflow identities/digests published here.

## Dependencies

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Blocked by the stable modules release [#432](https://github.com/nold-ai/specfact-cli-modules/issues/432) and paired core implementation-assurance contracts [#684](https://github.com/nold-ai/specfact-cli/issues/684).
- Blocks core skill installation [#251](https://github.com/nold-ai/specfact-cli/issues/251), then #253 and modules adapters #433.
- Runs independently of C15; neither change may silently redefine the other's policy or evidence semantics.

## Explicit Non-Goals

- No pre-implementation readiness, approval, or sealing behavior.
- No direct LLM/network invocation, automatic contract mutation, implementation edits, or test generation in the deterministic CLI.
- No universal semantic correctness, platform correctness, security, or completeness claim.
- No Codex/ECC/hatch3r adapter packaging.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #434
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/434>
- **Cross-Repository Counterpart**: <https://github.com/nold-ai/specfact-cli/issues/684>
- **Last Synced Status**: proposed
- **Sanitized**: true
