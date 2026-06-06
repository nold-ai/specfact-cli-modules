# Change: Artifact Evidence Index and Orphan Detection Runtime

## Why

Validation evidence needs a runtime index that can find stale links, missing
source references, orphaned implementation artifacts, and ambiguous mappings.
This is useful as a validation input, not as a ceremony dashboard or planning
system.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: runtime indexing, query/report commands, and
  generated `.specfact/` state.
- Core-owned scope remains artifact identity, linkage semantics, and orphan
  classification contracts.

## What Changes

- **NEW**: Runtime index over Spec Kit, OpenSpec, backlog, ADR, spec, contract,
  code, test, policy, and review artifacts.
- **NEW**: Orphan/drift detection for missing, stale, contradictory, or ambiguous
  evidence.
- **NEW**: Incremental update behavior where a changed file can refresh affected
  links without a full rebuild.
- **NEW**: JSON export consumed by validation-02 and governance-01.

## Capabilities

### New Capabilities

- `artifact-evidence-index-runtime`: Runtime index and orphan/drift detection for
  validation evidence.

### Modified Capabilities

(none)

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #170
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/170>
- **Core Counterpart**: nold-ai/specfact-cli#242
- **Last Synced Status**: proposed
- **Sanitized**: false
