# Change: Knowledge Memory Runtime Module

## Why

The core repo can define knowledge schemas and memory protocols, but the modules repo needs a concrete runtime bundle that owns the filesystem layout, command surfaces, and default backend behavior. Without a bundle-side implementation, the distillation loop cannot actually collect evidence, search memory, or promote learnings in day-to-day workflows.

## What Changes

- **NEW**: Add a `specfact-knowledge` bundle with `memory` subcommands for logging, searching, promoting, and distilling.
- **NEW**: Package the markdown-graph backend as the default runtime implementation for evidence, learnings, and rules under `.specfact/memory/`.
- **NEW**: Define gitignore, repo-layout, and file-lifecycle expectations for evidence, learnings, rules, and generated graph metadata.
- **NEW**: Add search and status surfaces that expose the paired core `MemoryBackend` behavior without requiring a vector store.
- **EXTEND**: Reserve manifest, registry, docs, and signing work for a first-party knowledge bundle.

## Capabilities

### New Capabilities

- `knowledge-memory-runtime`: Runtime bundle, command surfaces, and default markdown-graph backend for SpecFact memory workflows.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-knowledge/`, filesystem backend helpers, and command resources.
- Affected docs: bundle overview and command-reference documentation for `memory`.
- Dependencies: paired core change `knowledge-01-distillation-engine`.
- Release impact: introduces a new signed official bundle and registry entry.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#221](https://github.com/nold-ai/specfact-cli-modules/issues/221)
- **GitHub Issue**: [#224](https://github.com/nold-ai/specfact-cli-modules/issues/224)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/224>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
