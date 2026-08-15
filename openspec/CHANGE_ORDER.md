# OpenSpec Change Order

This document is the modules-side source of truth for active OpenSpec work. It
must be read together with the core repo change order in `nold-ai/specfact-cli`.

## Status Snapshot

| Bucket | Count | Location |
|---|---:|---|
| **Active** | 15 | [`openspec/changes/`](changes/) |
| **Parked** | 16 | [`openspec/parking-lot/`](parking-lot/) |
| **Archived** | 43 | [`openspec/changes/archive/`](changes/archive/) |

`openspec list` reflects the active set only. Completed changes are archived
with date-prefixed folders. Parked changes are preserved for later customer pull
but are not implementation-ready.

## Product Thesis

The modules repo should make SpecFact feel like **the validation and AI-bloat
defense tool**. The flagship runtime path is `specfact code review run`,
AI-bloat detection, simplification guidance, cleanup forecasts, remediation
handoff, sidecar/codebase hardening, docs guardrails, and deterministic evidence.

Backlog, Scrum, Kanban, SAFe, ceremony, enterprise, FinOps, and knowledge work
stay parked unless they directly improve validation evidence for a real user.
Spec Kit, OpenSpec, backlog systems, ADRs, specs, contracts, tests, and code are
upstream inputs to validation, not workflows this repo should replace.

## Recently Archived Validation Work

The following active changes were already complete or tied to closed GitHub
issues and are now archived:

| Change | Archive status |
|---|---|
| `tester-module-cli-reliability` | archived 2026-06-06 |
| `project-runtime-01-safe-artifact-write-policy` | archived 2026-06-06 |
| `prompt-command-contract-validation` | archived 2026-06-06 |
| `project-02-plan-root-command-fix` | archived 2026-06-06 |
| `marketplace-07-pr-auto-sign-updates` | archived 2026-06-06 |
| `docs-15-code-review-validation-guardrails` | archived 2026-06-06 |
| `codebase-import-runtime-hardening` | archived 2026-06-06 |
| `code-review-ai-bloat-detection` | archived 2026-06-06 |
| `code-review-11-simplification-feedback-loop` | archived 2026-06-06 |
| `code-review-12-guided-simplification-enforcement` | archived 2026-06-06 |
| `code-review-13-cleanup-forecast-agent-handoff` | archived 2026-06-06 |

These archived specs are now the shipped basis for the flagship demo: run review,
produce JSON evidence, identify AI-bloat findings, hand remediation packets to an
AI IDE, rerun, and compare improved evidence.

## Immediate Corrective Track

This track is first because no changed-scope assurance claim is trustworthy until its Git boundary and unknown states are explicit.

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `code-review-14-scope-truth-and-differential-enforcement` | [#413](https://github.com/nold-ai/specfact-cli-modules/pull/413) | Resolve worktree/index/range/full scope explicitly; compare pinned merge-base/head analyses; authenticate one target-tip project-runtime layer for both snapshots; fail closed on unknown scope, runtime provenance, or analyzer coverage | acceptance of this OpenSpec plan; paired core adoption is downstream after the signed release |

Implementation must stay independent from Requirements replay work. The two changes may share evidence vocabulary only through the future governance schema; neither may silently define the other's verdict.

## Active Tracks

### Track A - Validation Runtime Spine

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `policy-02-packs-and-modes` | [#158](https://github.com/nold-ai/specfact-cli-modules/issues/158) | Validation severity, rollout modes, and policy-pack execution | core profile/policy semantics |
| 2 | `governance-01-evidence-output` | [#169](https://github.com/nold-ai/specfact-cli-modules/issues/169) | Runtime evidence emitters for JSON/CI/AI handoff | core `governance-01` |
| 3 | `governance-02-exception-management` | [#167](https://github.com/nold-ai/specfact-cli-modules/issues/167) | Runtime exception handling and waiver evidence | governance-01, policy-02 |
| 4 | `traceability-01-index-and-orphans` | [#170](https://github.com/nold-ai/specfact-cli-modules/issues/170) | Artifact drift and orphan detection runtime | validation input contracts |
| 5 | `validation-02-full-chain-engine` | [#171](https://github.com/nold-ai/specfact-cli-modules/issues/171) | Validation evidence graph runtime, not lifecycle orchestration | governance-01, traceability-01 |

### Track B - Upstream Context Adapters

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `requirements-02-module-commands` | [#165](https://github.com/nold-ai/specfact-cli-modules/issues/165) | Import/normalize requirement context for evidence (shipped via PR #326, archived 2026-07-13) | core requirements input model |
| 2 | `openspec-01-intent-trace` | [#168](https://github.com/nold-ai/specfact-cli-modules/issues/168) | Import-first OpenSpec and Spec Kit requirement evidence runtime with gate surfacing (rescoped 2026-07-13) | requirements-02 runtime; core nold-ai/specfact-cli#350 contracts |
| 3 | `requirements-04-upstream-source-readiness` | [#346](https://github.com/nold-ai/specfact-cli-modules/issues/346) | Reject incomplete or policy-invalid native OpenSpec and Spec Kit sources before requirement evidence persistence | core [#648](https://github.com/nold-ai/specfact-cli/issues/648) |
| 4 | `requirements-05-dogfood-evidence-gate` | [#352](https://github.com/nold-ai/specfact-cli-modules/issues/352) | CI evidence adapter that reports green/red requirement-source validity and traceability evidence; not test-execution proof | requirements-04 shipped; existing Requirements runtime |
| 5 | `requirements-06-evidence-enforcement` | [#361](https://github.com/nold-ai/specfact-cli-modules/issues/361) | Reusable Requirements evidence command plus staged pre-commit enforcement and CI parity | [#352](https://github.com/nold-ai/specfact-cli-modules/issues/352); paired core [#657](https://github.com/nold-ai/specfact-cli/issues/657) |
| 6 | `requirements-07-scenario-runtime-proof` | [#368](https://github.com/nold-ai/specfact-cli-modules/issues/368) | Plan exact selectors and reconcile current-run JUnit independently from historical chronology | requirements-06; paired corrected core R07 |
| 7 | `requirements-08-bounded-red-green-proof` | [#414](https://github.com/nold-ai/specfact-cli-modules/issues/414) | Validate a core-emitted structural B < R < H <= D replay capsule as an independent chronology claim; pass requires distinct H/D (`H < D`) | corrected R07; paired core [#675](https://github.com/nold-ai/specfact-cli/issues/675) |
| 8 | `architecture-01-solution-layer` | [#164](https://github.com/nold-ai/specfact-cli-modules/issues/164) | Architecture-boundary validation input | core architecture-boundary contracts |
| 9 | `sync-01-unified-kernel` | [#157](https://github.com/nold-ai/specfact-cli-modules/issues/157) | Preview/apply safety only where validation adapters need it | project/runtime safety specs |
| Parked | `requirements-03-backlog-sync` | [#166](https://github.com/nold-ai/specfact-cli-modules/issues/166) | Read-first backlog drift evidence; no write-back critical path. Deprioritized 2026-07-13 behind openspec-01 | requirements-02, sync-01 |
| Gated | `architecture-02-module-well-architected` | [#230](https://github.com/nold-ai/specfact-cli-modules/issues/230) | Architecture-boundary review findings | architecture-01 shipped plus one usage cycle |

### Track C - Supporting Docs

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `docs-16-core-accountability-sync` | [#339](https://github.com/nold-ai/specfact-cli-modules/issues/339) | Fail-closed reciprocal core-documentation accountability and generated module-command freshness | core #643 shipped |
| 2 | `docs-14-module-release-history` | [#124](https://github.com/nold-ai/specfact-cli-modules/issues/124) | Release-history documentation for shipped modules | docs-13, publish workflow |

## Modify Queue Before Implementation

| Change | Required adjustment |
|---|---|
| `validation-02-full-chain-engine` | Rewrite runtime language around validation evidence graph outputs. Do not implement upstream requirements-to-code lifecycle orchestration. |
| `traceability-01-index-and-orphans` | Keep artifact drift, orphan, and linkage evidence. Drop ceremony/dashboard positioning. |
| `requirements-02-module-commands` | Drop requirement authoring as a flagship workflow. Keep import, normalization, validation, and coverage inspection. |
| `requirements-03-backlog-sync` | Keep read-first drift evidence. Write-back remains preview-only and outside the validation critical path. |
| `requirements-04-upstream-source-readiness` | Keep source readiness core-owned; reject incomplete native sources atomically and do not require the OpenSpec CLI outside explicit or strict/enterprise policy. |
| `architecture-01-solution-layer` | Keep architecture-boundary input and validation hooks. Drop architecture generation. |
| `openspec-01-intent-trace` | Done 2026-07-13: rescoped to import-first runtime for native OpenSpec/Spec Kit artifacts with deterministic gate surfacing. |
| `architecture-02-module-well-architected` | Keep gated until architecture-01 ships and is used for one complete cycle. |
| `sync-01-unified-kernel` | Keep only as safety infrastructure for validation/context adapters. |

## Parked By This Repositioning

Moved to [`openspec/parking-lot/`](parking-lot/) because they expand upstream
ceremony rather than validation evidence:

- `backlog-scrum-02-sprint-planning`
- `backlog-scrum-03-story-complexity`
- `backlog-scrum-04-definition-of-done`
- `backlog-kanban-01-flow-metrics`
- `backlog-safe-01-pi-planning`
- `backlog-safe-02-risk-rollups`
- `ceremony-02-requirements-aware-output`

## Implementation Waves

### Wave 1 - Cleanup and Scope Alignment

- Accept and implement `code-review-14-scope-truth-and-differential-enforcement` before making changed-range assurance claims.
- Archive completed/closed changes.
- Park upstream ceremony expansions.
- Update active proposals and wiki mirrors to validation positioning.
- Recheck GitHub Project metadata with a token that has project-field access.
- Required blocking gate: review all paired public change artifacts in
  `nold-ai/specfact-cli` before scoped implementation or shared
  workflow-semantic changes proceed.

### Wave 2 - Validation Evidence Runtime

- `policy-02-packs-and-modes`
- `governance-01-evidence-output`
- `governance-02-exception-management`
- `traceability-01-index-and-orphans`
- `validation-02-full-chain-engine`

### Wave 3 - Context Adapters

- `requirements-02-module-commands`
- `openspec-01-intent-trace` (pulled forward 2026-07-13, import-first rescope)
- `requirements-04-upstream-source-readiness` (blocked on paired core source-readiness contract)
- `requirements-05-dogfood-evidence-gate`
- `requirements-06-evidence-enforcement` (after requirements-05 archival/release evidence)
- `requirements-07-scenario-runtime-proof` (current-run reconciliation correction after requirements-06)
- `requirements-08-bounded-red-green-proof` (paired with core bounded replay after corrected R07)
- `architecture-01-solution-layer`
- `sync-01-unified-kernel`
- `requirements-03-backlog-sync` (parked 2026-07-13)

### Wave 4 - Gated Extensions

- `docs-16-core-accountability-sync`
- `architecture-02-module-well-architected`
- `docs-14-module-release-history`

## Parent Issues And Epic Framing

| Issue | Desired framing |
|---|---|
| [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162) | Flagship specfact code / AI-bloat defense epic |
| [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163) | Validation evidence and governance runtime |
| [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161) | Context adapters for validation evidence |

Project-board metadata was not available with the current token in the core
review, so final issue governance must recheck project fields before scoped
implementation starts.

## Archive Policy

After a change ships and merges, run `openspec archive <change-id>` from the repo
root. Do not manually move completed changes into `openspec/changes/archive/`.
Parking-lot moves are allowed for paused proposals that are explicitly not active
scope.
