# Change Validation Report: openspec-01-intent-trace

**Status**: VALIDATED — 2026-07-14 (Europe/Berlin)

## Scope and dependency check

- The modules change remains a thin command runtime: it delegates native
  OpenSpec and Spec Kit imports to core, and does not parse, hash, enrich, or
  write upstream artifacts.
- Core counterpart `nold-ai/specfact-cli#350` shipped in merged PR
  `nold-ai/specfact-cli#646` on 2026-07-13. Its exported helpers are
  `import_openspec_change`, `import_speckit_feature`, and
  `validate_requirement_context` with optional profile resolution.
- The module requires core `>=0.52.0,<1.0.0`; the validated local core is
  `0.52.2`.
- Core's `unsupported-source-schema` and `unsupported-profile-field` outcomes
  remain core-owned and are passed through by the module without fallback
  parsing, metadata enrichment, or partial persistence.

## Change validity evidence

`openspec validate openspec-01-intent-trace --strict` passed on 2026-07-14.

The active delta covers the command flags, conservative auto-detection,
sidecar merge behavior, profile delegation, core diagnostic pass-through, and
read-only upstream behavior. No scope change is required beyond the existing
delta updates that record the core compatibility outcomes.

## Implementation constraints

1. Add or update scenario-mapped tests before runtime code.
2. Record failing-before and passing-after evidence in `TDD_EVIDENCE.md`.
3. Bump the additive module release and align manifest compatibility metadata.
4. Re-sign the changed module manifest and run the full quality gate sequence.
