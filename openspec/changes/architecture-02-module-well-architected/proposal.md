# Change: Architecture Well-Architected Module

## Why

The core repo can define architecture review contracts, but the modules repo still needs a runtime bundle that inspects boundaries, ADR coverage, import hygiene, and interface drift across real codebases. Without that bundle, the architecture pillar cannot move from guidance to executable review.

## What Changes

- **NEW**: Add a `specfact-architecture` bundle with an `architecture` command for boundary, interface, and well-architected review.
- **NEW**: Package analyzers and rule resources for dependency-graph checks, ADR traceability, and interface-diff evaluation.
- **NEW**: Encode the `ALLOWED_IMPORTS.md` pattern into reusable review rules so the modules repo and user repositories can share the same boundary-checking approach.
- **Introduce** report surfaces that map architecture findings into the paired core review contract and optionally emit evidence for the knowledge runtime.
- **EXTEND**: Reserve manifest, registry, docs, and signing work for a new official architecture bundle.

### Adapter Contract

The normalized boundary between analyzers and the core review contract defines how architecture findings flow from packaged analyzers into the core review model:

- **Required Core Findings Schema Fields**: `id`, `type`, `severity`, `description`, `source`, `timestamp`, `evidence_refs`
- **Analyzer Output Mapping**: Outputs from packaged analyzers (dependency-graph, ADR traceability, interface-diff) map to normalized evidence references by populating `evidence_refs` with stable file paths, line ranges, and artifact identifiers
- **Emission Mode**: Synchronous emission (findings emitted immediately after analyzer completion)
- **Retry/Ordering Semantics**: Findings are emitted in deterministic analyzer execution order with no retry; failures in one analyzer do not block subsequent analyzers

## Capabilities

### New Capabilities

- `architecture-well-architected-module`: Runtime bundle, analyzers, and normalized reporting for architecture and well-architected review.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-architecture/`, dependency-graph adapters, and boundary-rule resources.
- Affected docs: bundle overview and command-reference documentation for `architecture`.
- Dependencies: paired core change `architecture-02-well-architected-review`; existing repo guidance from `ALLOWED_IMPORTS.md`.
- Release impact: introduces a new signed official bundle and registry entry.
- **Core Compatibility**: The reserved manifest `architecture-02-well-architected-review` specifies `core_compatibility: ">=1.0.0 <2.0.0"` in `module-package.yaml` registry metadata, declaring the required core version range for the paired architecture review contracts.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#219](https://github.com/nold-ai/specfact-cli-modules/issues/219)
- **GitHub Issue**: [#230](https://github.com/nold-ai/specfact-cli-modules/issues/230)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/230>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false