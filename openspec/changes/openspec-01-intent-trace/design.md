# Design: OpenSpec and Spec Kit Import Runtime for Requirement Evidence

## Context

The `specfact-requirements` module (`packages/specfact-requirements/`) already
wires `requirements import|validate|list|coverage` to core helpers via lazy
imports (`runtime.py` loads `specfact_cli.models.requirements` and
`specfact_cli.requirements.context`). Import currently accepts only
`--from-file`. The core counterpart change (nold-ai/specfact-cli#350) adds
OpenSpec and Spec Kit import normalizers and gate evaluation to core; this
change adds the command-surface runtime.

## Goals / Non-Goals

**Goals:**

- Add `--from-openspec [PATH]` and `--from-speckit [PATH]` to
  `requirements import`, delegating all parsing/normalization/hashing to core.
- Auto-detect conventional source layouts when the path is omitted.
- Surface core gate findings in `validate` output with non-zero exit when a
  profile treats a finding as an error; expose gate-relevant counts in
  `list`/`coverage`.

**Non-Goals:**

- Any parsing, hashing, or gate logic in the module (core-owned).
- Writes into upstream OpenSpec or Spec Kit directories.
- Backlog import (deprioritized `requirements-03-backlog-sync` scope).

## Decisions

### D1: Flags on `requirements import` vs a new subcommand

**Decision**: Extend the existing `import` command with mutually compatible
source flags (`--from-file`, `--from-openspec`, `--from-speckit`).
**Rationale**: One import surface, one sidecar persistence path, one merge
semantics (`merge_requirement_inputs`). A new subcommand would duplicate the
bundle/sidecar handling for no user benefit.

### D2: Lazy core-helper loading, same pattern as requirements-02

**Decision**: Load the new core import normalizers via the existing
`_load_requirements_module` lazy-import pattern and raise
`RequirementsCoreUnavailableError` with the paired core change named when the
helpers are missing.
**Rationale**: Keeps the module installable against older cores with a clear
error instead of an ImportError traceback.

### D3: Auto-detection stays conservative

**Decision**: When the source path is omitted, detect only conventional
layouts (`openspec/changes/` for OpenSpec; Spec Kit `specs/` feature folders)
relative to the current project root. Ambiguity or absence is a clear error
naming the expected layouts, never a guess.
**Rationale**: Deterministic behavior over convenience heuristics; misdetected
sources would poison evidence.

## Risks / Trade-offs

- **[Risk] Core/module version skew** — flags exist but core helpers are old.
  Mitigation: D2 error contract; documented minimum core version in
  `module-package.yaml` dependency metadata.
- **[Trade-off] Auto-detection scope** — monorepos with multiple Spec Kit
  roots need explicit paths. Accepted; explicit path flag covers it.

## Migration Plan

1. No data migration; sidecar format unchanged.
2. Docs update the requirements module page with import-first examples.

## Open Questions

- None currently blocking implementation.
