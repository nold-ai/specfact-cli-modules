# Change: Requirements Import and Validation Runtime

## Why

SpecFact needs module commands that import, normalize, validate, and inspect
upstream requirement context for evidence. It should not become the authoring
stack for requirements.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: grouped command runtime, adapters, and
  validation behavior for normalized requirement inputs.
- Core-owned scope remains the shared requirements input model and evidence
  contracts.
- Requirement authoring templates are no longer critical-path scope.

## What Changes

- **NEW**: Import commands for backlog items, OpenSpec proposals, Spec Kit feature
  folders, and local requirement records.
- **NEW**: Normalization into source-attributed records compatible with the core
  requirements input model.
- **NEW**: Validation and coverage inspection for evidence usefulness by profile.
- **NEW**: Adapter hooks return bounded records instead of free-form planning
  prose.
- **REMOVED FROM CRITICAL PATH**: Interactive requirement authoring and full
  requirement lifecycle management.

## Capabilities

### New Capabilities

- `requirements-validation-runtime`: Runtime commands for importing,
  normalizing, validating, and inspecting upstream requirement context.

### Modified Capabilities

- `module-io-contract`: Requirements implementation focuses on import and
  validation hooks for evidence.
- `backlog-adapter`: Backlog adapters can provide source-attributed requirement
  snippets.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #165
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/165>
- **Core Counterpart**: nold-ai/specfact-cli#239
- **Last Synced Status**: proposed
- **Sanitized**: false
