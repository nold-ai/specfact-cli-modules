# Change: Architecture Boundary Validation Runtime

## Why

Architecture context is useful when it validates code reality: component
boundaries, ADR references, ownership, interface leaks, and contract mismatch.
SpecFact should not generate architecture or compete with planning tools.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: grouped architecture runtime commands,
  imports, validation hooks, and reports.
- Core-owned scope remains the architecture-boundary input model and shared
  validation contracts.
- Architecture derivation and authoring are no longer critical-path scope.

## What Changes

- **NEW**: Import/runtime handling for architecture-boundary records sourced from
  existing ADRs, docs, diagrams, Spec Kit plans, or OpenSpec designs.
- **NEW**: Validation for missing ADR links, interface leaks, component ownership
  gaps, and mismatched contract boundaries.
- **NEW**: Runtime output that can feed traceability-01 and validation-02.
- **REMOVED FROM CRITICAL PATH**: AI-assisted architecture generation and
  template-based architecture authoring.

## Capabilities

### New Capabilities

- `architecture-boundary-validation-runtime`: Runtime commands and reports for
  architecture-boundary evidence.

### Modified Capabilities

- `data-models`: Project bundle integration consumes the core architecture input
  namespace when present.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #164
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/164>
- **Core Counterpart**: nold-ai/specfact-cli#240
- **Last Synced Status**: proposed
- **Sanitized**: false
