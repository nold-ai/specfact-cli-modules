## Context

FinOps reporting depends on core-owned schemas and budget semantics, but the modules repo must package the runtime collectors and classifiers that convert actual session data into evidence. This bundle has to work for both networked provider APIs and local/offline workflows without turning the feature into a cloud-only surface.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-finops`.
- Collect provider token/cost metadata and normalize it into the paired core FinOps evidence contract.
- Classify outcomes using workflow signals that the rest of the ecosystem can consume deterministically.
- Keep offline and air-gapped workflows supported through explicit local fallback behavior.

**Non-Goals:**

- Implement org-level approval workflows; those extend through paired core enterprise changes.
- Replace the paired core telemetry schema or budget gate logic.
- Require every provider to expose identical billing APIs in the first release.

## Decisions

### 1. Make provider collectors pluggable behind one bundle

- **Decision**: Ship `specfact-finops` as one bundle with provider-specific collector adapters and a shared normalization layer.
- **Why**: Users need one command surface even when providers differ behind the scenes.
- **Alternative considered**: One bundle per provider. Rejected because it fragments the FinOps workflow and complicates outcome rollups.

### 2. Keep outcome classification explicit and deterministic

- **Decision**: The bundle derives outcomes from explicit workflow signals and shared enums rather than heuristic free-form summaries.
- **Why**: Distillation and budget analytics depend on stable outcome categories.
- **Alternative considered**: LLM-generated outcome labels. Rejected because it undermines determinism for the core evidence schema.

### 3. Support offline-safe collection paths

- **Decision**: When provider billing APIs are unavailable, the bundle can still emit evidence using local token accounting and explicit `source` metadata.
- **Why**: The platform’s local-first posture should not make FinOps unavailable to offline users.
- **Alternative considered**: Require remote billing APIs for every report. Rejected because it excludes local and air-gapped workflows.

## Risks / Trade-offs

- **Risk**: Billing APIs differ and may lag behind model usage events. → **Mitigation**: preserve source metadata and test adapters independently from normalization logic.
- **Risk**: Outcome classification may miss workflow nuance. → **Mitigation**: keep enums explicit and allow later paired-core extensions instead of overfitting this first change.
- **Risk**: Offline fallbacks may be mistaken for authoritative billed cost. → **Mitigation**: require evidence metadata to distinguish estimated vs provider-reported cost.

## Migration Plan

1. Confirm paired core telemetry/FinOps contracts are stable enough for integration.
2. Implement package structure, collectors, and classifier adapters with fixture-based tests.
3. Publish docs, registry metadata, signatures, and compatibility ranges together.

## Open Questions

- Which provider APIs should be first-class in the initial release?
- What is the minimum viable workflow signal set for reliable outcome classification on day one?
