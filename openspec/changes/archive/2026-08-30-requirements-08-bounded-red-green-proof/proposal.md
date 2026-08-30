# Change: Validate Bounded Historical Replay Capsules

## Why

Current-run selector evidence and historical TDD chronology answer different questions. The earlier retained-red design tried to keep a historical artifact fresh by reconstructing pytest inputs statically. Core PRs #665–#671 demonstrated that this is not a bounded or portable module contract.

The Requirements module should validate a typed capsule produced by trusted core replay: exact selectors failed at red commit R, passed at green implementation checkpoint H, remained passing at delivered head D, and every Git transition satisfied its complete declared path policy.

## What Changes

- Advance finalized Requirements reports from R07 schema v3 to R08 schema v4 while leaving mapping sidecars at schema v2. Finalized report v2 is legacy-only; v3 is explicit R07 compatibility; v4 requires the request state, both claims, and R08 provenance.
- Add a versioned historical replay capsule binding B/R/H/D commits and trees, structural B < R < H <= D ancestry, and D equality with the delivery identity. A passing chronology additionally requires distinct H and D (`H < D`); `D = H` produces `status: unknown`; assurance remains unproven.
- Validate complete B..R, R..H, and H..D changed-path/rename manifests and digests against the accepted red-setup, implementation, and delivery-evidence declarations.
- Require the accepted proof mapping, failing-before `TDD_EVIDENCE.md` record, and governed `CHANGE_VALIDATION.md` pre-R readiness-validation record in B..R. Freeze mapping, plan, selectors, path sets, expected-failure identities, and the exact failing/readiness section bytes and digests at R; validate their byte-identical R/D preservation.
- Require only declared implementation touchpoints in R..H.
- Permit only the governed change's exact mapped `TDD_EVIDENCE.md` and `CHANGE_VALIDATION.md` delivery records in H..D.
- Validate identical exact selectors failed as declared at R, passed at H, and remained passing at distinct D.
- Validate artifact hashes, runner/toolchain/dependency/environment/plugin/network-policy identities, resource bounds, signed module identity, and verifier epoch without executing Git, pytest, or subprocesses.
- Reconcile `red_green_chronology` independently from `current_execution` using an explicit versioned `chronology_request: not_requested|required` input and CLI `--chronology-request not-requested|required`; never infer intent from capsule absence.
- With `chronology_request: required`, use `status: unknown` only for missing/unavailable/incomplete/unsupported/unverifiable facts, trust that cannot be established, verifier failure, and the explicit D = H insufficient-observation case. Use `status: fail` for a complete trusted verified contradiction of ancestry, identity/hash equality, attempt freshness, path, frozen evidence, selector/failure identity, or fail/pass/pass outcome policy. `not_requested` with no capsule remains `status: not_evaluated` / `reason: capsule_not_supplied`; `not_requested` plus a capsule is rejected.
- Keep legacy-ledger reading migration-only and prohibit new generation.

## Capabilities

### New Capabilities

- `requirements-bounded-red-green-proof`: Validate a trusted core B/R/H/D replay capsule and emit a bounded historical chronology claim.
- `requirements-proof-review-context`: Require the schema-v4 chronology claim object, retain its optional R08 attestation alongside current execution, and keep both provenance-only.

## Impact

- Planning artifacts only; no package, tests, registry, version, signature, prompts, or generated docs change in this commit.
- The paired core R08 implementation owns Git/worktree/test execution and must use a signed modules release.
- Backward-compatible report evolution is explicit: read finalized report v2 as legacy, v3 as R07 compatibility, and v4 as R08; never infer the version from missing fields.
- Later implementation changes package/docs/changelog metadata on its feature branch. After that PR merges to `dev`, the canonical `publish-modules.yml` workflow—not a local wrapper—generates signed manifest/registry/archive/checksum/sidecar changes in a separate auto-publish PR. The initial validator release makes no self-chronology claim.
- Rollback: disable chronology reconciliation while preserving corrected R07 current-run evidence and every already-written independent claim object as opaque provenance; no old reader may reinterpret corrected chronology as a legacy basis.

## Explicit Non-Goals

- Execute Git, pytest, or subprocesses in modules.
- Infer Python/pytest dependency closure or claim runtime-trace completeness.
- Prove intent completeness, correctness, code quality, or defect absence.
- Change generic Code Review scope/enforcement behavior.

## Source Tracking

- **GitHub Issue**: #414
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/414
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: closed-not-planned / archived without spec promotion / superseded
- **Parent Feature**: #161
- **Paired Core Issue**: nold-ai/specfact-cli#675
- **Paired Core PR**: nold-ai/specfact-cli#674
- **Related Code Review PR**: #413
- **Planning date**: 2026-08-13
