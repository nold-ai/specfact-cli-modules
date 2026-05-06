# Parking Lot (modules side)

These module-runtime change proposals are **paused, not abandoned**, because
their core-side counterparts in `nold-ai/specfact-cli` have been parked. A
module runtime cannot land before the core contracts it implements, so these
nine proposals are pinned to whatever signal un-parks the core side.

For background and the parent triage rationale, see:

- Core PR: <https://github.com/nold-ai/specfact-cli/pull/551>
- Core parking-lot README: <https://github.com/nold-ai/specfact-cli/blob/ba944021c0b186698658cdde6ed9a7776eff05a0/openspec/parking-lot/README.md>

## Restoration policy

A modules-side proposal can be returned to `openspec/changes/` only after:

1. The core counterpart has itself been un-parked (i.e. moved back into
   `nold-ai/specfact-cli/openspec/changes/`).
2. The current core API surface has been re-validated against this module's
   proposal — six months of drift may have invalidated assumptions.
3. The directory is moved back under `openspec/changes/` here, and
   `openspec validate <change-id>` passes.

## Contents and un-park triggers

| Modules change | Paired core change | GH issue | Un-park trigger |
|---|---|---|---|
| `enterprise-01-module-policy-client` | `enterprise-01-policy-resolution-extension` | [#231](https://github.com/nold-ai/specfact-cli-modules/issues/231) | Core enterprise-01 un-parked |
| `enterprise-02-module-audit-client` | `enterprise-02-rbac-and-audit-trail` | [#232](https://github.com/nold-ai/specfact-cli-modules/issues/232) | Core enterprise-02 un-parked |
| `finops-01-module-cost-outcome` | `finops-01-telemetry-and-outcomes` | [#223](https://github.com/nold-ai/specfact-cli-modules/issues/223) | Core finops-01 un-parked |
| `knowledge-01-module-memory-runtime` | `knowledge-01-distillation-engine` | [#224](https://github.com/nold-ai/specfact-cli-modules/issues/224) | Core knowledge-01 un-parked |
| `knowledge-02-module-writeback` | `knowledge-02-preflight-context-assembly` | [#225](https://github.com/nold-ai/specfact-cli-modules/issues/225) | Core knowledge-02 un-parked |
| `review-resiliency-01-module` | `review-resiliency-01-contracts` | [#226](https://github.com/nold-ai/specfact-cli-modules/issues/226) | Core review-resiliency-01 un-parked |
| `security-01-module-sast-sca-secret` | `security-01-unified-findings-model` | [#227](https://github.com/nold-ai/specfact-cli-modules/issues/227) | Core security-01 un-parked |
| `security-02-module-license-compliance` | `security-02-eu-gdpr-baseline` (license aspect) | [#228](https://github.com/nold-ai/specfact-cli-modules/issues/228) | Core security-02 un-parked |
| `security-03-module-pii-gdpr-eu` | `security-02-eu-gdpr-baseline` (GDPR aspect) | [#229](https://github.com/nold-ai/specfact-cli-modules/issues/229) | Core security-02 un-parked |

## Not parked here (still active)

The following modules-side proposals remain in `openspec/changes/` because
their core counterparts are still active or in the core repo's modify queue:

- `architecture-01-solution-layer` *(paired core: active)*
- `architecture-02-module-well-architected` *(paired core: gated, not parked)*
- `requirements-02-module-commands`, `requirements-03-backlog-sync`
- `traceability-01-index-and-orphans`, `validation-02-full-chain-engine`
- `governance-01-evidence-output`, `governance-02-exception-management`
- `policy-02-packs-and-modes`, `sync-01-unified-kernel`,
  `ceremony-02-requirements-aware-output`
- `openspec-01-intent-trace` *(paired core: in modify queue, will be trimmed)*
- All `backlog-*` and `docs-*` changes
- `codebase-import-runtime-hardening`, `project-runtime-01-safe-artifact-write-policy`

## Completed / awaiting archive

- `marketplace-07-pr-auto-sign-updates`

The core marketplace-06 work (`marketplace-06-ci-module-signing`) was already
archived here on 2026-04-16 — no parking action needed.
