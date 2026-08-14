# Change: Validate Bounded Historical Replay Capsules

## Why

Current-run selector evidence and historical TDD chronology answer different questions. The earlier retained-red design tried to keep a historical artifact fresh by reconstructing pytest inputs statically. Core PRs #665–#671 demonstrated that this is not a bounded or portable module contract.

The Requirements module should validate a typed capsule produced by trusted core replay: exact selectors failed at red commit R, passed at green implementation checkpoint H, remained passing at delivered head D, and every Git transition satisfied its complete declared path policy.

## What Changes

- Add a versioned historical replay capsule binding B/R/H/D commits and trees, B < R < H <= D ancestry, and D equality with the delivery identity.
- Validate complete B..R, R..H, and H..D changed-path/rename manifests and digests against the accepted red-setup, implementation, and delivery-evidence declarations.
- Require the accepted proof mapping and failing-before TDD record in B..R and freeze mapping, plan, selectors, path sets, and failing evidence at R.
- Require only declared implementation touchpoints in R..H.
- Permit only the governed change's exact mapped `TDD_EVIDENCE.md` and `CHANGE_VALIDATION.md` delivery records in H..D.
- Validate identical exact selectors failed as declared at R, passed at H, and remained passing at distinct D.
- Validate artifact hashes, runner/toolchain/dependency/environment/plugin/network-policy identities, resource bounds, signed module identity, and verifier epoch without executing Git, pytest, or subprocesses.
- Reconcile `red_green_chronology` independently from `current_execution`.
- Fail strict chronology policy as unknown/unproven for every incomplete, mismatched, policy-invalid, unsupported, or untrusted capsule.
- Keep legacy-ledger reading migration-only and prohibit new generation.

## Capabilities

### New Capabilities

- `requirements-bounded-red-green-proof`: Validate a trusted core B/R/H/D replay capsule and emit a bounded historical chronology claim.
- `requirements-proof-review-context`: Retain optional chronology provenance alongside current execution without verdict fusion.

## Impact

- Planning artifacts only; no package, tests, registry, version, signature, prompts, or generated docs change in this commit.
- The paired core R08 implementation owns Git/worktree/test execution and must use a signed modules release.
- Backward-compatible report evolution is required for existing R07 consumers.
- Later implementation changes `packages/specfact-requirements/module-package.yaml`, `docs/bundles/requirements/overview.md`, `CHANGELOG.md`, `registry/index.json`, generated archive/checksum/signature outputs, and Code Review metadata only if its serialized proof context changes.
- Rollback: disable chronology reconciliation while preserving corrected R07 current-run evidence.

## Explicit Non-Goals

- Execute Git, pytest, or subprocesses in modules.
- Infer Python/pytest dependency closure or claim runtime-trace completeness.
- Prove intent completeness, correctness, code quality, or defect absence.
- Change generic Code Review scope/enforcement behavior.

## Source Tracking

- **GitHub Issue**: #414
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/414
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: open
- **Parent Feature**: #161
- **Paired Core Issue**: nold-ai/specfact-cli#675
- **Paired Core PR**: nold-ai/specfact-cli#674
- **Related Code Review PR**: #413
- **Planning date**: 2026-08-13
