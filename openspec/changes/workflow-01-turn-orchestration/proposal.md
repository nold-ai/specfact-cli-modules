# Change: Module-Owned Bounded Turn Orchestration

## Owner-approved agentic SDLC amendment — 2026-10-04

Include optional decision-context drift and advisory external findings in #483 producer adapters and #742 adoption. Retain original producer identity, severity/rule, artifact digest, snapshot identity and verification basis. Producer trust and finding epistemic basis are separate fields: a trusted producer can emit heuristic advice. Present affected obligations, missing evidence, source/test/configuration changes and next actions. Context absence does not block ordinary verification. Use structured pytest runner identity first; certify its selected-suite/current-attempt semantics before additional runners. Deterministic verification precedes repair; one controller owns a shared elapsed/attempt budget across optional preflight and PR loops, with exhaustion, no-progress, oscillation and required-human-decision stops. An advisory converged result never overrides a failed or unavailable required producer.

This planning amendment supersedes conflicting scope and prerequisite wording below. It changes no runtime behavior and completes no implementation task. See [roadmap](../../AGENTIC_SDLC_ROADMAP.md).

## Why

Agents need a stable gate sequence, resumable local progress and a bounded review/fix loop. These capabilities must not create mandatory historical proof, obscure independent test/security/review outcomes or duplicate the optional preflight runtime.

## What Changes

- Add the module-owned `specfact workflow` group for pre-validate, implement state/checkpoints, verify, fix planning/recheck and opt-in local PR autofix.
- Preserve original producer artifacts and independent statuses; expose a normalized actionable findings view with producer references rather than extending Code Review schema 1.6 with ignored fields.
- Bind results to exact scoped content, configuration and tool identities. Separate run IDs from input digests; keep operational receipts local and resumable.
- Bound implementation repair to three iterations and PR repair to five rounds, with timeouts, no-progress stops, one controller, recovery and exact-head checks.
- Publish reusable prefixed workflow skills with the module; keep repository commands/settings and thin projection in the paired core adoption.

## Capabilities

### New Capabilities

- `turn-workflow-orchestration`: portable sequencing, producer adapters, current input identity and optional local progress.
- `bounded-pr-remediation`: local observation and explicitly authorized bounded PR repair with recoverable side effects.

### Modified Capabilities

None. Requirements, Code Review, governance envelopes, traceability and optional seal/conformance contracts remain owned by their existing changes.

## Impact

Planning only now. Later implementation adds `packages/specfact-workflow`, its manifest, registry entry, signed payload, tests and module command/usage documentation. Use existing core discovery/registration and public APIs with truthful core_compatibility; do not require an unreleased core consumer to publish the producer. Module skill content remains distinct from repository-owned wrapper projection and generic core #251 installation.

Requirements R09 remains pure reconciliation without Git, pytest or network calls. The new orchestration package is a separate executor/consumer. No new security taxonomy, evidence graph, seal service, hosted agent or model provider is required. Local validation works offline; selected GitHub governance and PR automation explicitly require live service access and cannot silently pass when unavailable.

## Dependencies and rollout

Modules #481 is the prerequisite for integrating its signed current-run Requirements contract. Standalone producer adapters can be developed independently, but publication with that integration waits for the compatible contract. The signed workflow publication blocks core #742 runtime adoption. The reverse core adoption is not a producer release prerequisite.

Related only: core #251/#253 skill distribution, core #740 policy cutover, core #247/modules #169 governance envelope, core #241/modules #171 graph, core #242/modules #170 traceability, parked core #522 findings taxonomy, and explicit optional preflight. These relationships do not create blanket runtime blockers. C15-specific review consumption waits for its own signed policy readiness; supported older producers retain their actual semantics without simulated C15 acceptance.

Deliver deterministic verification before local repair, and local repair before PR autofix. Publish through the canonical signed post-merge release path; candidate builds are test fixtures, not stable handoffs. Rollback disables the optional loop and restores the prior signed package/configuration without deleting original producer reports or relabeling old evidence.

Documentation impact: module command/reference and workflow guides on modules.specfact.io, installation/compatibility and CLI help; link the core contributor adoption with verified permalinks. Update navigation only for pages added at implementation.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #483
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/483>
- **Repository**: `nold-ai/specfact-cli-modules`
- **Parent Feature**: #163
- **Paired Core Story**: <https://github.com/nold-ai/specfact-cli/issues/742>
- **Paired Core Proposal (public baseline)**: <https://github.com/nold-ai/specfact-cli/blob/codex/workflow-01-turn-orchestration/openspec/changes/workflow-01-turn-orchestration/proposal.md>; the risk-first amendment is prepared for a separate review PR.
- **Last Synced Status**: proposed / Todo, 2026-10-08 (live readback; planning creation complete, separate publication authorized)

## Signed Requirements compatibility gate

Before selecting or adopting workflow #483 for current-run Requirements integration, validate the exact immutable signed Requirements #481 publication and its schema-v3 `current_execution` contract against the actual core and workflow versions. Verify archive/manifest/payload signatures and identities, then exercise the exact installed pair with existing representative current-result fixtures. An absent, incompatible, unsigned or v2-only producer leaves runtime integration/adoption not ready; do not substitute a passing receipt or silently downgrade the contract. Repository skill projection remains independently deliverable, and core #740 retains policy cutover ownership.

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.

## Risk-first execution amendment — 2026-10-08

The owner selected a minimal adaptation within this existing paired change: discover invalid assumptions before dependent work and reduce avoidable correction overhead. Reuse `specfact-pre-validate`, `specfact-implement`, `specfact-verify`, `specfact-fix` and `specfact-autofix`; add no stage aliases or commands. This amendment preserves the 2026-10-04 decision, current assurance/review policy and signed release dependencies. It adds guidance and acceptance scenarios, not report schemas, receipt formats, producer verdicts or automatic collection.

- For nontrivial behavior changes, select one or two assumptions that could invalidate the approach and run the smallest relevant existing CLI/API/dependency probe before dependent implementation. Record the observed boundary, limitations and result in existing planning/evidence sections. Documentation-only work records applicability; a probe supplements required checks.
- Give the applicable existing review the assumptions, evidence references, affected obligations and exclusions. Triage findings against a violated requirement or concrete invariant, a reachable failure path and evidence. Preserve confirmed defects, disproved concerns, suggestions and unresolved claims as distinct dispositions; no disposition waives required findings.
- Keep one writer and batch compatible repairs. Handoffs carry the delta, affected assumptions, remaining findings and original evidence references. Boundary drift or uncertain impact broadens review and affected-gate rechecks; retain the shared controller and consumed budgets across handoffs.
- Reuse existing records for a bounded trial on the next subsequently authorized nontrivial change in each repository. Report early discoveries, later escapes, correction batches and overhead. Separate token categories, billed charges, elapsed time, active effort and waiting; unavailable values remain unknown. Operational observations do not prove causal or monetary savings.

Non-goals: full pstack installation, default Arena/reviewer panels, a new ledger, importing another project's capability, warning-policy calibration or minimal-evidence cutover. No runtime command becomes active because skills exist. Keep reusable modules content concise, reference existing rules, and let each repository supply its own commands/governance and core-owned wrappers/projection.

Deliver skills/projection -> deterministic verification -> bounded repair -> opt-in PR automation. Review the initial skills/projection slice after two engineer-days as an investment checkpoint, not an estimate for the full paired runtime. Added ceremony, weak probes and incorrect dismissals are mitigated by limiting assumptions, stating proof boundaries and preserving producer authority/current-input binding. Roll back new guidance/projection while retaining evidence and ordinary checks; runtime adoption retains coordinated configuration/module-pin rollback.

Public research context (accessed 2026-10-08): [Cursor pstack](https://github.com/cursor/plugins/tree/main/pstack) and [Flavio Copes' overview, updated 2026-09-29](https://flaviocopes.com/pstack/). These inform adapted practices, not a framework dependency or savings claim. Confidence: high in architectural fit; medium in reducing defects/overhead. Planning creation leaves runtime implementation and trials unchecked.
