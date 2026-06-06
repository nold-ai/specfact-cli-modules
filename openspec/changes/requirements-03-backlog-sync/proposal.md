# Change: Backlog Requirement Drift Runtime

## Why

Backlog items and local validation inputs drift. The useful SpecFact runtime
value is read-first import, conflict preview, and drift evidence before code
merges, not bidirectional product-management sync.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: backlog adapter runtime, read-first drift
  detection, preview safety, and evidence emission.
- Core-owned scope remains drift evidence contracts and duplicate-creation
  safeguards.
- Write-back remains preview-only and outside the validation critical path.

## What Changes

- **NEW**: Read-first import from backlog systems into normalized validation
  inputs.
- **NEW**: Drift categories for missing acceptance criteria, stale local records,
  changed issue status, missing source links, and ambiguous mappings.
- **NEW**: Preview-only write-back MAY exist later behind explicit confirmation.
- **EXTEND**: Spec Kit backlog-extension awareness prevents duplicate issue
  creation when upstream artifacts already contain tracker mappings.

## Capabilities

### New Capabilities

- `backlog-requirement-drift-runtime`: Runtime detection of drift between backlog
  items and normalized validation inputs.

### Modified Capabilities

- `backlog-adapter`: Extended with source-attributed import and drift hooks.
- `requirements-validation-runtime`: Extended with backlog drift evidence.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #166
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/166>
- **Core Counterpart**: nold-ai/specfact-cli#244
- **Last Synced Status**: proposed
- **Sanitized**: false
