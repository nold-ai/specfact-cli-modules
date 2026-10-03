## Owner-approved agentic SDLC amendment — 2026-10-04

Add a bounded optional export using in-toto Statement v1 and SCAI v0.3 to bind a digest-addressed evidence bundle and the original native reports. Preserve independent statuses, producer authority, uncertainty and limitations in authoritative native JSON; neither SARIF nor an attestation is a replacement report. Signing authenticates origin/integrity, not claim correctness. Reuse existing CI signing/verification infrastructure: no new signer, store or predicate-standardization dependency. Test tampered bundle, mismatched subject/digest and unauthorized signer rejection. Summary/SARIF interoperability may consume native producer reports without requiring the full envelope, #170/#171 graph/index or seals; export does not block #481/#740/#483.

This planning amendment supersedes conflicting scope and prerequisite wording below. It changes no runtime behavior and completes no implementation task. See [roadmap](../../AGENTIC_SDLC_ROADMAP.md).

## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for <https://github.com/nold-ai/specfact-cli-modules/issues/481>.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../requirements-09-minimal-evidence/proposal.md).

## Context

This change implements proposal scope for `governance-01-evidence-output` from the 2026-02-15 architecture-layer integration plan. It is proposal-stage only and defines implementation strategy without changing runtime code.

## Goals / Non-Goals

**Goals:**

- Define an implementation approach that stays within the proposal scope.
- Keep compatibility with existing module registry, adapter bridge, and contract-first patterns.
- Preserve offline-first behavior and deterministic CLI execution.

**Non-Goals:**

- No production code implementation in this stage.
- No schema-breaking changes outside declared capabilities.
- No dependency expansion beyond the proposal and plan.

## Decisions

- Use module-oriented integration and registry lazy-loading patterns already used in SpecFact CLI.
- Keep all public APIs contract-first with `@icontract` and `@beartype`.
- Make all behavior extensions opt-in or backward-compatible by default.
- Add/modify OpenSpec deltas first so tests can be derived before implementation.

## Risks / Trade-offs

- [Dependency ordering drift] -> Mitigation: gate implementation tasks on declared prerequisites.
- [Capability overlap with adjacent changes] -> Mitigation: keep this change scoped to listed capabilities only.
- [Documentation drift] -> Mitigation: include explicit docs update tasks in apply phase.

## Migration Plan

1. Implement this change only after listed dependencies are implemented.
2. Add tests from spec scenarios and capture failing-first evidence.
3. Implement minimal production changes needed for passing scenarios.
4. Run quality gates and then open PR to `dev`.

## Open Questions

- Dependency summary: Depends on validation-02-full-chain-engine and policy-02-packs-and-modes.
- Whether additional cross-change sequencing constraints should be hard-blocked in `openspec/CHANGE_ORDER.md`.

## Current contract and archival boundary — 2026-09-20

The core envelope contract can precede graph producers. Runtime emitters consume that contract; graph consumers may integrate later using the existing envelope. Serialization requirements are additive and do not replace the producer-owned Full Chain Validation or Policy Engine requirements during archival. Full-chain availability is required only for actual full-chain emission, not for delivering the envelope or serializing current-only results. R09 and workflow adoption remain independent of this broader emitter feature. Earlier wording that requires validation-02 before the whole envelope is historical.

## Deferred trace context

The [historical OSCAL trace draft](research/oscal-trace-notes.md) is non-normative research for later graph consumers. It is not a basic export prerequisite.
