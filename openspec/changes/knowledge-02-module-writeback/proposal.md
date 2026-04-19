# Change: Knowledge Writeback Module

## Why

Distilled rules only create leverage if they are written back into the instruction surfaces that guide future AI and review workflows. A dedicated writeback bundle lets users opt into regenerating prompt files and drafting memory-sharing comments without forcing those behaviors into the base knowledge runtime.

## What Changes

- **NEW**: Add a `specfact-knowledge-writeback` bundle with commands that regenerate selected instruction surfaces from approved memory rules.
- **NEW**: Package adapters for `BUGBOT.md`, `.github/copilot-instructions.md`, and CodeRabbit memory-comment drafts as opt-in writeback targets.
- **NEW**: Require preview/dry-run output and explicit destination targeting so writeback remains reviewable and safe for repo owners.
- **NEW**: Normalize selected rule metadata into deterministic writeback manifests that can be audited later.
- **EXTEND**: Reserve manifest, registry, docs, and signing work for a first-party writeback bundle.

## Capabilities

### New Capabilities

- `knowledge-writeback`: Runtime bundle, previewable writeback targets, and deterministic output manifests for memory-driven instruction updates.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-knowledge-writeback/`, target adapters, and preview/output helpers.
- Affected docs: bundle overview and command-reference documentation for writeback commands.
- Dependencies: paired core change `knowledge-02-preflight-context-assembly`; module dependency `knowledge-01-module-memory-runtime`.
- Release impact: introduces a new signed official bundle and registry entry.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#221](https://github.com/nold-ai/specfact-cli-modules/issues/221)
- **GitHub Issue**: [#225](https://github.com/nold-ai/specfact-cli-modules/issues/225)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/225>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
