# Change: Separate Current-Run Scenario Evidence from Historical TDD Chronology

## Why

The Requirements module currently places current execution and historical failing-first proof on one maturity ladder. Final reconciliation consequently requires prior-red or legacy-ledger evidence even when the bounded question is only whether exact mapped selectors passed in the current run.

This conflation pushed core toward static inference of every pytest-determining input. The module contract must instead report current execution and historical chronology as independent claims.

## What Changes

- Preserve lifecycle planning, accepted mappings, deterministic exact selector plans, and current-run JUnit reconciliation.
- Advance only the finalized Requirements report from schema v2 to v3; mapping sidecars remain schema v2. Finalized-report v2 uses the legacy reader, while v3 requires both corrected claim objects.
- Add a first-class `current_execution` result that can be finalized from the current plan and JUnit without historical evidence.
- Stop deriving `passing-after-red` from current-run pass or generic maturity.
- Remove new use of the R07 legacy-ledger migration path; keep finalized-report v2 reading only for explicitly labelled compatibility and reject malformed v3 instead of treating it as legacy.
- Accept finalized current-run Requirements evidence as Code Review provenance without requiring a historical proof basis.
- Keep trusted historical chronology outside R07; no active change owns that capability after the R08 proposal was abandoned.

## Capabilities

### Modified Capabilities

- `requirements-scenario-runtime-proof`: Plan and reconcile exact current-run selector evidence independently from chronology.
- `requirements-proof-review-context`: Require both finalized-report schema-v3 claim objects, preserve the chronology placeholder as provenance, and prevent verdict fusion.

## Impact

- Planning artifacts only in this commit; no package source, tests, prompts, registry, version, signature, or generated docs change.
- A later implementation requires a signed Requirements module release before core adopts finalized report schema v3.
- Backward compatibility must preserve reading existing reports while making their historical basis explicit.
- Rollback is lossless: disable only new-field writing, preserve already-written `current_execution` and `red_green_chronology` objects, and require an old-reader fixture proving they remain opaque rather than being reinterpreted as legacy chronology. Do not relabel current-run results as historical proof.

## Explicit Non-Goals

- Execute tests or Git commands in the module.
- Infer pytest/Python imports, plugins, configuration, data reads, or dependency closure.
- Merge Requirements and Code Review verdicts.
- Claim complete intent, correctness, or code quality.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#368](https://github.com/nold-ai/specfact-cli-modules/issues/368)
- **Paired Core Issue**: [nold-ai/specfact-cli#662](https://github.com/nold-ai/specfact-cli/issues/662)
- **Follow-up**: none; the abandoned R08 replay proposal is historical only, and any replacement requires a separately approved change
- **Planning correction date**: 2026-08-13
