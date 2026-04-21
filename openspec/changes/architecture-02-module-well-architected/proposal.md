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

The normalized boundary between analyzers and the core review contract defines how architecture findings flow from packaged analyzers into the core ReviewFinding model:

**Mapping to ReviewFinding Fields:**

- **category**: Set to `"architecture"` for all architecture analyzer findings
- **tool**: Set to the analyzer name (e.g., `"pylint"` for the pylint-runner expectation, or other analyzer names for dependency-graph, ADR traceability, interface-diff)
- **rule**: Set to the violation rule identifier from the analyzer (e.g., rule IDs from pylint or custom rule identifiers for boundary violations)
- **file**: Set to the repository-relative file path where the violation occurs
- **line**: Set to the 1-based line number or line range start where the violation occurs
- **message**: Set to a human-readable description of the architecture violation
- **severity**: Set to `"error"`, `"warning"`, or `"info"` based on the violation severity
- **fixable**: Optional boolean indicating whether the finding can be auto-fixed (default: false)

**Supplemental Evidence:**

- `evidence_refs` may be retained as supplemental references for additional context (stable file paths, line ranges, artifact identifiers), but primary location data must use the canonical `file` and `line` fields

**Emission Semantics:**

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