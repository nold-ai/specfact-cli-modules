# Change: Validation Evidence Graph Runtime

## Why

The modules repo owns the executable runtime for SpecFact validation. That runtime
should not implement a requirements-to-code product lifecycle. It should consume
existing artifacts from Spec Kit, OpenSpec, backlog systems, architecture notes,
contracts, specs, code, tests, policy, and code review, then emit deterministic
evidence about drift, gaps, orphans, and AI-bloat remediation status.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: executable validation graph runtime,
  command wiring, evidence aggregation, and module packaging.
- Core-owned scope remains the shared evidence graph contract, severity semantics,
  and governance envelope.
- Implementation MUST NOT ship upstream requirements/architecture authoring or
  lifecycle orchestration.

## What Changes

- **NEW**: Runtime graph builder over existing artifacts and adapter outputs.
- **NEW**: Graph validators for missing evidence, stale links, orphaned code,
  weak tests, uncovered contracts, and unresolved AI-bloat remediation.
- **NEW**: Evidence JSON emitted through governance-01 contracts.
- **EXTEND**: Existing validation commands MAY keep compatibility aliases, but
  user-facing docs and data contracts use validation evidence graph terminology.
- **EXTEND**: Code-review output can attach clean-code, cleanup forecast, and
  `ai_bloat` summaries as evidence graph inputs.

## Capabilities

### New Capabilities

- `validation-evidence-graph-runtime`: Executable validation graph runtime that
  consumes upstream artifacts and emits deterministic evidence.

### Modified Capabilities

- `sidecar-validation`: Extended to publish graph-compatible evidence.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #171
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/171>
- **Core Counterpart**: nold-ai/specfact-cli#241
- **Last Synced Status**: proposed
- **Sanitized**: false
