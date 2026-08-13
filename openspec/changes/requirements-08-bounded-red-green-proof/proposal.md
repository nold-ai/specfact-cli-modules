# Change: Validate Bounded Historical Replay Capsules

## Why

Current-run selector evidence and historical TDD chronology answer different questions. The earlier retained-red design tried to keep a historical artifact fresh by reconstructing pytest inputs statically. PRs #665–#671 demonstrated that this is not a bounded or portable module contract.

The Requirements module should validate a typed capsule produced by trusted core replay: exact selectors failed at R, passed at H, and only declared implementation touchpoints changed.

## What Changes

- Add a versioned historical replay capsule binding B/R/H Git and tree identities, transition manifests/digests, mapping/plan/selectors, red/final JUnit, runner/toolchain/environment/policy, and verifier epoch.
- Validate the capsule structurally and semantically without executing Git or tests in modules.
- Reconcile `tdd_chronology` independently from `current_execution`.
- Fail strict chronology policy as unknown/unproven for incomplete or untrusted capsules.
- Retain the exact bounded claim and explicit limitations in Requirements and Code Review context.
- Keep legacy-ledger reading migration-only and prohibit new generation.

## Capabilities

### New Capabilities

- `requirements-bounded-red-green-proof`: Validate a trusted core replay capsule and emit a bounded historical chronology claim.
- `requirements-proof-review-context`: Retain optional chronology provenance alongside current execution without verdict fusion.

## Impact

- Planning artifacts only; no package, tests, registry, version, signature, prompts, or generated docs change in this commit.
- The paired core R08 implementation owns Git/worktree/test execution and must use a signed modules release.
- Backward-compatible report evolution is required for existing R07 consumers.
- Rollback: disable chronology reconciliation while preserving corrected R07 current-run evidence.

## Explicit Non-Goals

- Execute Git or pytest in modules.
- Infer Python/pytest dependency closure or claim runtime-trace completeness.
- Prove intent completeness, correctness, code quality, or defect absence.
- Change generic Code Review scope/enforcement behavior.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Origin**: forensic review of core PRs #665–#671
- **Extends**: corrected `requirements-07-scenario-runtime-proof`
- **Paired Core Change**: `requirements-08-bounded-red-green-proof`
- **Planning date**: 2026-08-13

