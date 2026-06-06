# Change: OpenSpec and Spec Kit Evidence Import Runtime

## Why

OpenSpec and Spec Kit already own upstream planning artifacts. The modules repo
should provide optional import runtime that maps those artifacts into SpecFact
validation evidence when useful, without requiring upstream tools to adopt a new
intent schema.

## Ownership Alignment (2026-06-06)

- Modules-owned scope retained here: bridge/import runtime, optional metadata
  parsing, source attribution, and generated evidence inputs.
- Core-owned scope remains optional adapter contracts and validation behavior.

## What Changes

- **NEW**: Optional import support for OpenSpec proposals and Spec Kit feature
  folders.
- **NEW**: Source-attributed mapping of tasks, spec deltas, acceptance checks,
  requirement references, and evidence links when present.
- **NEW**: Strict metadata validation only when optional metadata exists.
- **EXTEND**: Project sync/import commands avoid duplicate planning artifacts and
  instead feed validation evidence.

## Capabilities

### New Capabilities

- `openspec-speckit-evidence-import-runtime`: Optional runtime adapter for
  OpenSpec and Spec Kit artifacts consumed by validation.

### Modified Capabilities

- `openspec-bridge-adapter`: Extended to parse optional metadata and evidence
  links without requiring them.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #168
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/168>
- **Core Counterpart**: nold-ai/specfact-cli#350
- **Last Synced Status**: proposed
- **Sanitized**: false
