# Change: Runtime Evidence Output for CI and AI Handoff

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
