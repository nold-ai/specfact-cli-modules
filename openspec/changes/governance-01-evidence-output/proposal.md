# Change: Runtime Evidence Output for CI and AI Handoff

## Owner-approved agentic SDLC amendment — 2026-10-04

Add a bounded optional export using in-toto Statement v1 and SCAI v0.3 to bind a digest-addressed evidence bundle and the original native reports. Preserve independent statuses, producer authority, uncertainty and limitations in authoritative native JSON; neither SARIF nor an attestation is a replacement report. Signing authenticates origin/integrity, not claim correctness. Reuse existing CI signing/verification infrastructure: no new signer, store or predicate-standardization dependency. Test tampered bundle, mismatched subject/digest and unauthorized signer rejection. Summary/SARIF interoperability may consume native producer reports without requiring the full envelope, #170/#171 graph/index or seals; export does not block #481/#740/#483.

This planning amendment supersedes conflicting scope and prerequisite wording below. It changes no runtime behavior and completes no implementation task. See [roadmap](../../AGENTIC_SDLC_ROADMAP.md).

## Scope rescope — 2026-09-20

Emit lean current-run results and references to existing CI artifacts. Historical chronology is optional and separately labeled; no transcripts, approval receipts, or duplicate proof execution by default. This broader emitter feature is not a blocker for https://github.com/nold-ai/specfact-cli-modules/issues/481.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../requirements-09-minimal-evidence/proposal.md).

## Why

SpecFact needs machine-readable evidence that validation ran, policies were
enforced, drift and AI-bloat findings were classified, and exceptions were
tracked. The modules repo owns the runtime emitters that write those artifacts
for CI, docs, and AI IDE remediation loops.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: runtime emitter flags, file writing, command
  integration, and module packaging.
- Core-owned scope remains the evidence envelope schema and CI contract.

## What Changes

- **NEW**: Runtime evidence writer for validation and code-review runs.
- **NEW**: `--evidence-dir .specfact/evidence/` persistence behavior where the
  owning command supports evidence output.
- **NEW**: CI mode exit-code handling based on profile/policy mode.
- **NEW**: Evidence artifact naming and terminal summaries.
- **EXTEND**: Validation graph, policy, exception, code quality, cleanup forecast,
  and `ai_bloat` results are emitted through the shared evidence envelope.

## Capabilities

### New Capabilities

- `runtime-governance-evidence-output`: Runtime evidence writers for CI gates and
  AI remediation handoff.

### Modified Capabilities

- `validation-evidence-graph-runtime`: Extended with evidence persistence.
- `policy-engine`: Results formatted as evidence-compatible structures.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #169
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/169>
- **Core Counterpart**: nold-ai/specfact-cli#247
- **Last Synced Status**: proposed
- **Sanitized**: false

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.
