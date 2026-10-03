# Change: Architecture Boundary Validation Runtime

## Owner-approved agentic SDLC amendment — 2026-10-04

First import approved boundaries, ownership and ADR references as optional context with exact source identity. Structural readiness is not design-quality approval. Replace architecture derivation/authoring scenarios in this change with bounded import and evidence association. Missing traceability is missing association/evidence, not proof of absent behavior. Broader analyzer review remains after architecture input delivery and one complete real usage cycle. At that stage consume maintained Import Linter Python dependency-rule results, preserving rule/configuration/version/snapshot identity, declared boundary association and original artifacts; do not build a second import-graph engine. Plant a forbidden dependency in fixtures and require its reported violation; unavailable/incomplete extraction is UNKNOWN.

This planning amendment supersedes conflicting scope and prerequisite wording below. It changes no runtime behavior and completes no implementation task. See [roadmap](../../AGENTIC_SDLC_ROADMAP.md).

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

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.
