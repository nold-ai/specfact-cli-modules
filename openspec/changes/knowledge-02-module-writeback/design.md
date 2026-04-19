## Context

The knowledge runtime stores and distills evidence, but teams also need a controlled way to project approved rules into repo-visible instruction surfaces. This change defines a separate bundle that keeps writeback opt-in, previewable, and traceable while depending on the core preflight/change-assembly work and the base knowledge runtime.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-knowledge-writeback`.
- Keep writeback targets explicit, previewable, and reversible at the file level.
- Reuse approved memory rules from the base knowledge runtime instead of duplicating storage logic.
- Record deterministic metadata describing which rules were projected into which targets.

**Non-Goals:**

- Replace the base memory runtime or distillation engine.
- Automatically mutate instruction surfaces without preview or user selection.
- Introduce repo-hosted secrets or external service dependencies as a requirement.

## Decisions

### 1. Separate writeback from storage/runtime

- **Decision**: Ship writeback automation as its own bundle, not inside `specfact-knowledge`.
- **Why**: Many users want memory storage without automatic prompt or docs regeneration.
- **Alternative considered**: Put writeback inside the base knowledge bundle. Rejected because it couples storage to optional automation.

### 2. Require previewable target adapters

- **Decision**: Every writeback target must support preview or draft generation before any file mutation or comment-post preparation.
- **Why**: Prompt and instruction surfaces are high-sensitivity files and need reviewable changes.
- **Alternative considered**: Direct in-place regeneration by default. Rejected because it violates the repo’s safety posture.

### 3. Track writeback through deterministic manifests

- **Decision**: The bundle emits metadata describing source rules, target type, target path, and generation timestamps for each writeback attempt.
- **Why**: Later drift analysis and review need to know how instruction surfaces were derived.
- **Alternative considered**: Rely only on git diffs. Rejected because it loses structured lineage data.

## Risks / Trade-offs

- **Risk**: Writeback templates may oversimplify nuanced rules. → **Mitigation**: preserve source rule references in output manifests and previews.
- **Risk**: File-target coverage could grow too broad too early. → **Mitigation**: start with named adapters and document that new targets require explicit approval.
- **Risk**: Users may assume writeback implies deployment or remote sync. → **Mitigation**: keep outputs local and draft-oriented in the initial release.

## Migration Plan

1. Confirm paired core and base knowledge runtime changes are stable enough for integration.
2. Implement package structure, target adapters, and preview/draft flows.
3. Publish docs, registry metadata, signatures, and compatibility range together.

## Open Questions

- Which writeback target should be considered the canonical first-class path in the initial release?
- Should CodeRabbit output stop at draft comment bodies, or also generate machine-readable metadata for later posting?
