## Context

Knowledge distillation needs a module-side runtime that gives users a default, local-first place to store evidence, learnings, and rules. The paired core change defines the schema and protocol, but the modules repo owns the package, command surface, and filesystem behavior that make the feature usable without enterprise infrastructure or vector databases.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-knowledge`.
- Ship the markdown-graph backend as the default runtime implementation of the paired core `MemoryBackend` protocol.
- Define local filesystem layout and gitignore expectations for evidence, learnings, rules, and graph metadata.
- Keep optional vector-store or remote adapters out of the correctness-critical path.

**Non-Goals:**

- Replace the paired core knowledge schema or promotion policy.
- Require Chroma or any embedding/vector backend for the default workflow.
- Implement writeback into instruction surfaces; that belongs in `knowledge-02-module-writeback`.

## Decisions

### 1. Make markdown-graph the reference runtime

- **Decision**: `specfact-knowledge` ships the markdown-graph backend as the default implementation and first-class command surface.
- **Why**: The platform’s local-first posture requires a zero-config backend that works in git.
- **Alternative considered**: Make a vector database the default. Rejected because it adds operational complexity to the base workflow.

### 2. Separate memory storage from writeback automation

- **Decision**: This bundle owns storage, search, and distillation entrypoints, while writeback into prompts/docs remains a separate bundle.
- **Why**: The runtime should stay useful even when users do not want automation rewriting instruction surfaces.
- **Alternative considered**: Combine runtime and writeback in one bundle. Rejected because it couples storage to optional automation.

### 3. Treat `.specfact/memory/` as a structured contract

- **Decision**: The bundle defines deterministic subdirectories and file naming for evidence, learnings, rules, and graph metadata.
- **Why**: Repeatable distillation and review depend on predictable layout.
- **Alternative considered**: Allow arbitrary user-defined layouts in the initial release. Rejected because it weakens interoperability with the paired core tooling.

## Risks / Trade-offs

- **Risk**: Large repositories could generate a noisy local memory tree. → **Mitigation**: define gitignore defaults and command filters early.
- **Risk**: Search quality without embeddings may be limited. → **Mitigation**: keep tag/keyword search deterministic now and leave richer retrieval to future optional adapters.
- **Risk**: Users may expect automatic writeback after distillation. → **Mitigation**: document the split between runtime storage and the follow-on writeback bundle.

## Migration Plan

1. Confirm the paired core knowledge schema and protocol are stable enough for runtime integration.
2. Implement package structure, markdown-graph backend, and CLI entrypoints.
3. Publish docs, registry metadata, signatures, and compatibility range together.

## Open Questions

- Which graph metadata files belong under version control vs ignore defaults in the first release?
- Should search support only tags and keywords initially, or also relationship traversal commands?
