## Context

This change implements the module-owned runtime scope for
`requirements-02-module-commands` from the 2026-02-15 architecture-layer
integration plan. The paired core change `nold-ai/specfact-cli#239` supplies
shared requirement context helpers; this modules change supplies the grouped
runtime command surface.

## Goals / Non-Goals

**Goals:**
- Define an implementation approach that stays within the proposal scope.
- Keep compatibility with existing module registry, adapter bridge, and contract-first patterns.
- Preserve offline-first behavior and deterministic CLI execution.
- Provide `specfact requirements ...` command handlers that reuse core
  normalization, bundle extension IO, validation report, and coverage summary
  helpers.
- Emit JSON-friendly command output for validation evidence and AI handoff.

**Non-Goals:**
- No requirement authoring workflow.
- No bidirectional backlog sync or ceremony automation.
- No schema-breaking changes outside declared capabilities.
- No dependency expansion beyond the proposal and plan.

## Decisions

- Use module-oriented integration and registry lazy-loading patterns already used in SpecFact CLI.
- Keep all public APIs contract-first with `@icontract` and `@beartype`.
- Make all behavior extensions opt-in or backward-compatible by default.
- Add/modify OpenSpec deltas first so tests can be derived before implementation.
- Store normalized requirement context through the existing
  `requirements.inputs` extension from `requirements-01-data-model`.
- Keep command output bounded to core diagnostics, validation reports, and
  coverage summaries.
- Treat failed validation as a non-zero command result while keeping `warnings`
  visible as successful advisory evidence.

## Risks / Trade-offs

- [Dependency ordering drift] -> Mitigation: gate implementation tasks on declared prerequisites.
- [Capability overlap with adjacent changes] -> Mitigation: keep this change scoped to listed capabilities only.
- [Documentation drift] -> Mitigation: include explicit docs update tasks in apply phase.
- [Core helper drift] -> Mitigation: validate against the paired
  `specfact-cli-worktrees/feature/requirements-02-module-commands` checkout
  until core #239 merges.
- [Command ownership confusion] -> Mitigation: module ships runtime command
  handlers; core only provides helpers and missing-module diagnostics.

## Migration Plan

1. Implement this change only after listed dependencies are implemented or
   accepted as paired parallel work.
2. Add tests from spec scenarios and capture failing-first evidence.
3. Implement minimal production changes needed for passing scenarios.
4. Update public docs, command overview artifacts, issue body, and wiki mirror
   metadata.
5. Run quality gates and then open PR to `dev`.

## Open Questions

- Dependency summary: `requirements-01-data-model` and
  `arch-07-schema-extension-system` are implemented in core; core #239 is paired
  parallel work and must remain API-compatible with this module runtime.
- The connector does not expose GitHub project fields; local hierarchy cache and
  live issue state remain the available governance evidence.
