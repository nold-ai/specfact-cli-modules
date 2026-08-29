# OpenSpec Change Order

This document is the modules-side source of truth for active OpenSpec work. It
must be read together with the core repo change order in `nold-ai/specfact-cli`.

## Status Snapshot

| Bucket | Count | Location |
|---|---:|---|
| **Active** | 18 | [`openspec/changes/`](changes/) |
| **Parked** | 17 | [`openspec/parking-lot/`](parking-lot/) |
| **Archived** | 49 | [`openspec/changes/archive/`](changes/archive/) |

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
| 1 | `code-review-14-scope-truth-and-differential-enforcement` | [#416](https://github.com/nold-ai/specfact-cli-modules/issues/416) | Resolve worktree/index/range/full scope explicitly; compare pinned merge-base/head analyses; authenticate one target-tip project-runtime layer for both snapshots; fail closed on unknown scope, runtime provenance, or analyzer coverage | accepted planning PR [#413](https://github.com/nold-ai/specfact-cli-modules/pull/413); paired core adoption is downstream after the signed release |

The immutable C14 compatibility smoke establishes core 0.55.1 as the minimum: lightweight tag `v0.55.1`, full commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276`, and full tree `47984be5434d7ae65ed6908bf525a32053290337`. Runtime metadata therefore uses `>=0.55.1,<1.0.0`: the ceiling is required because recursive installation includes Codebase and Requirements modules whose current manifests reject core 1.x. Current paired-core validation exercises compatible versions above the minimum; a routine compatible core update within the dependency graph does not require a module metadata release. Remove the ceiling only after widening and validating the required dependency graph. This correction supersedes C14's exact-only admission wording without changing its frozen provenance identities or historical evidence.

C14 behavior was first delivered and published as module 0.49.46 by merged PRs
[#418](https://github.com/nold-ai/specfact-cli-modules/pull/418) and
[#419](https://github.com/nold-ai/specfact-cli-modules/pull/419). The bounded
compatibility correction was delivered and published as 0.49.61 by
[#444](https://github.com/nold-ai/specfact-cli-modules/pull/444) and
[#445](https://github.com/nold-ai/specfact-cli-modules/pull/445). Promotion
review remediation and its immutable publication then produced 0.49.75 through
[#448](https://github.com/nold-ai/specfact-cli-modules/pull/448) and
[#449](https://github.com/nold-ai/specfact-cli-modules/pull/449). These release
identities remain distinct historical evidence; later patches do not rewrite
the earlier artifacts or records. Issue
[#416](https://github.com/nold-ai/specfact-cli-modules/issues/416) remains open
and `In Progress`; this planning series records the merged delivery evidence but
does not close, reparent, relabel, reassign, or otherwise change that issue.

Implementation must stay independent from Requirements replay work. The two changes may share evidence vocabulary only through the future governance schema; neither may silently define the other's verdict.

## Recently Archived Release-Safety Work

This bounded corrective change is independent of C14 and merged to `dev` before
the C14 release promotion. Alert-specific evidence remains in private GitHub
Security records under the repository security policy.

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `archive/2026-08-23-ci-01-workflow-dispatch-core-ref-trust` | [#422](https://github.com/nold-ai/specfact-cli-modules/pull/422) | Shipped and archived: preserve paired feature-branch validation for non-manual events while restricting manual paired-core execution to literal `main` or `dev` refs | ancestry sync PR [#421](https://github.com/nold-ai/specfact-cli-modules/pull/421) |

## Active Tracks

### Track A - Validation Runtime Spine

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `policy-02-packs-and-modes` | [#158](https://github.com/nold-ai/specfact-cli-modules/issues/158) | Validation severity, rollout modes, and policy-pack execution | core profile/policy semantics |
| 2 | `governance-01-evidence-output` | [#169](https://github.com/nold-ai/specfact-cli-modules/issues/169) | Runtime evidence emitters for JSON/CI/AI handoff | core `governance-01` |
| 3 | `governance-02-exception-management` | [#167](https://github.com/nold-ai/specfact-cli-modules/issues/167) | Runtime exception handling and waiver evidence | governance-01, policy-02 |
| 4 | `traceability-01-index-and-orphans` | [#170](https://github.com/nold-ai/specfact-cli-modules/issues/170) | Artifact drift and orphan detection runtime | validation input contracts |
| 5 | `validation-02-full-chain-engine` | [#171](https://github.com/nold-ai/specfact-cli-modules/issues/171) | Validation evidence graph runtime, not lifecycle orchestration | governance-01, traceability-01 |

### Track A2 - Deterministic Pre-Implementation Assurance

This track consumes core-owned assurance interfaces and keeps executable
validators, CLI/workflow behavior, publication, and adapters in modules. The
canonical module skill is the single workflow source; generated instructions
and adapters reference it without duplicating Python checks.

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `preflight-02-assurance-runtime` | [#431](https://github.com/nold-ai/specfact-cli-modules/issues/431) | Unpublished runtime, Python validators, CLI/rendering/persistence, and canonical bundled `specfact-preflight` workflow | core contract [#682](https://github.com/nold-ai/specfact-cli/issues/682) |
| 2 | `preflight-03-dogfood-hardening-and-release` | [#432](https://github.com/nold-ai/specfact-cli-modules/issues/432) | Evidence-backed hardening, bounded compatibility proof, signing, and stable publication | modules #431; core C14 dogfood/readiness [#683](https://github.com/nold-ai/specfact-cli/issues/683) |
| 3 | `preflight-05-implementation-conformance` | [#434](https://github.com/nold-ai/specfact-cli-modules/issues/434) | Worktree/index checkpoints, final range conformance, C14/Requirements/review evidence reuse, seal-aware pre-commit, bounded agent handoff, and signed publication | modules #432; paired core implementation-assurance contract [#684](https://github.com/nold-ai/specfact-cli/issues/684) |
| 4 | `preflight-04-harness-adapters` | [#433](https://github.com/nold-ai/specfact-cli-modules/issues/433) | Later thin Codex plugin, ECC companion, and hatch3r pack; no duplicate validators | signed modules #434 identity; core generated instructions [#253](https://github.com/nold-ai/specfact-cli/issues/253) |

### Track B - Upstream Context Adapters

| Order | Change folder | GitHub # | Positioning | Blocked by |
|---:|---|---|---|---|
| 1 | `requirements-02-module-commands` | [#165](https://github.com/nold-ai/specfact-cli-modules/issues/165) | Import/normalize requirement context for evidence (shipped via PR #326, archived 2026-07-13) | core requirements input model |
| 2 | `openspec-01-intent-trace` | [#168](https://github.com/nold-ai/specfact-cli-modules/issues/168) | Import-first OpenSpec and Spec Kit requirement evidence runtime with gate surfacing (rescoped 2026-07-13) | requirements-02 runtime; core nold-ai/specfact-cli#350 contracts |
| 3 | `requirements-04-upstream-source-readiness` | [#346](https://github.com/nold-ai/specfact-cli-modules/issues/346) | Reject incomplete or policy-invalid native OpenSpec and Spec Kit sources before requirement evidence persistence | core [#648](https://github.com/nold-ai/specfact-cli/issues/648) |
| 4 | `requirements-05-dogfood-evidence-gate` | [#352](https://github.com/nold-ai/specfact-cli-modules/issues/352) | CI evidence adapter that reports green/red requirement-source validity and traceability evidence; not test-execution proof | requirements-04 shipped; existing Requirements runtime |
| 5 | `requirements-06-evidence-enforcement` | [#361](https://github.com/nold-ai/specfact-cli-modules/issues/361) | Reusable Requirements evidence command plus staged pre-commit enforcement and CI parity | [#352](https://github.com/nold-ai/specfact-cli-modules/issues/352); paired core [#657](https://github.com/nold-ai/specfact-cli/issues/657) |
| 6 | `requirements-07-scenario-runtime-proof` | [#368](https://github.com/nold-ai/specfact-cli-modules/issues/368) | Plan exact selectors and reconcile current-run JUnit independently from historical chronology | requirements-06; paired corrected core R07 |
| Parked | `requirements-08-bounded-red-green-proof` | [#414](https://github.com/nold-ai/specfact-cli-modules/issues/414) | Superseded by seal-bound risk/test intent plus implementation checkpoints; no B/R/H/D replay or capsule implementation planned | closed Not Planned; preserved under `openspec/parking-lot/` without archive/spec merge |
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

### Preflight Assurance Sequence - Mandatory Dependency Gate

1. Core contract [#682](https://github.com/nold-ai/specfact-cli/issues/682).
2. Unpublished modules runtime [#431](https://github.com/nold-ai/specfact-cli-modules/issues/431).
3. Core C14 adoption [#680](https://github.com/nold-ai/specfact-cli/issues/680).
4. Core C14 dogfood/readiness [#683](https://github.com/nold-ai/specfact-cli/issues/683).
5. Evidence-backed modules hardening and stable publication [#432](https://github.com/nold-ai/specfact-cli-modules/issues/432).
6. Core implementation-assurance contracts [#684](https://github.com/nold-ai/specfact-cli/issues/684).
7. Modules checkpoint/conformance runtime, dogfood, signing, and publication [#434](https://github.com/nold-ai/specfact-cli-modules/issues/434).
8. Shared skill installation #251 -> generated instructions #253 -> adapters #433. Modules C15 #417 -> core C15 #679 may proceed independently after stable #432.

Modules C15 #417 keeps its existing policy and exception blockers (#158,
core #248, and modules #167) plus the stable preflight release. Existing native
C14/history edges remain preserved. Every implementation change starts in a
dedicated issue-linked worktree and session.

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
- `requirements-08-bounded-red-green-proof` is parked and superseded; no replay implementation is planned
- `architecture-01-solution-layer`
- `sync-01-unified-kernel`
- `requirements-03-backlog-sync` (parked 2026-07-13)

### Wave 4 - Gated Extensions

- `docs-16-core-accountability-sync`
- `architecture-02-module-well-architected`
- `docs-14-module-release-history`
- `preflight-05-implementation-conformance` after stable #432 and core #684
- `preflight-04-harness-adapters` after signed #434, core #251, and core #253

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
