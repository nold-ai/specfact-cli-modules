# SpecFact Backlog Command Gap Analysis

**Context:** User reported that `specfact backlog` shows only a subset of expected commands; e.g. `add` is missing. Analysis performed 2026-03-10.

## Root Cause

The **backlog-module-ownership-cleanup** (archived 2026-03-09) proposed making `nold-ai/specfact-backlog` the sole owner of backlog commands. The **OWNERSHIP_MATRIX** split ownership as:

| Owner | Commands |
|-------|----------|
| **backlog-core** (built-in, `modules/backlog-core`) | `add`, `analyze-deps`, `trace-impact`, `sync`, `diff`, `promote`, `verify-readiness`, `generate-release-notes`, `delta *` |
| **specfact-backlog** (bundle) | `daily`, `refine`, `init-config`, `map-fields`, ceremony aliases, auth |

The **backlog-core** module was removed or largely gutted during migration (only `modules/backlog-core/logs/` remains). The commands it owned were **never migrated** to specfact-backlog. Result: those commands are **missing** from the installed backlog surface.

## Documented vs Implemented

### Docs (agile-scrum-workflows.md, backlog guides)

| Command | Documented | Implemented in specfact-backlog |
|---------|------------|----------------------------------|
| `backlog add` | ✓ | ✗ (was backlog-core) |
| `backlog analyze-deps` | ✓ | ✗ |
| `backlog trace-impact` | ✓ | ✗ |
| `backlog verify-readiness` | ✓ | ✗ |
| `backlog diff` | ✓ | ✗ |
| `backlog sync` | ✓ | ✗ |
| `backlog promote` | ✓ | ✗ |
| `backlog generate-release-notes` | ✓ | ✗ |
| `backlog delta status\|impact\|cost-estimate\|rollback-analysis` | ✓ | ✗ |
| `backlog daily` | ✓ (ceremony standup) | ✓ |
| `backlog refine` | ✓ (ceremony refinement) | ✓ |
| `backlog ceremony standup` | ✓ | ✓ |
| `backlog ceremony refinement` | ✓ | ✓ |
| `backlog init-config` | ✓ | ✓ |
| `backlog map-fields` | ✓ | ✓ |
| `backlog auth` | ✓ | ✓ |

### Specfact-backlog actual commands (from `commands.py`)

- `daily` (@app.command)
- `refine` (@app.command)
- `init-config` (@app.command)
- `map-fields` (@app.command)
- `ceremony` (typer: standup, refinement, planning, flow, pi-summary)
- `auth` (typer)

## Recommendation

1. **Migrate missing commands** from backlog-core to specfact-backlog (or restore backlog-core as built-in if migration is not feasible). This aligns with **backlog-module-ownership-cleanup** and **module-migration-10-bundle-command-surface-alignment**.
2. **Or** update docs to remove references to `add`, `sync`, `delta`, etc. until they are re-implemented.
3. **Extend module-migration-10** to include backlog in the documented-vs-runtime audit and add backlog to the validation inventory.

## Related Changes

- `backlog-module-ownership-cleanup` (archived) – proposed full migration
- `module-migration-10-bundle-command-surface-alignment` – command surface audit (project, spec; backlog could be added)
- `cli-val-07-command-package-runtime-validation` (archived) – validated `backlog add`, `backlog refine`, `backlog map-fields` with backlog-core + specfact-backlog overlap
