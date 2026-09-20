# Change: Minimal Current-Run Requirements Evidence

## Why

Useful current test results should not require immutable development history. The paired core proposal records the review and research motivating the correction. This change owns the module contract and signed release for #481; core #740 owns execution, CI trust and policy rollout.

## What Changes

- Make `current` reconciliation the default, using the current plan and JUnit without retained RED or approval receipts.
- Separate schema v3 `current_execution` and `red_green_chronology`; preserve explicit v2/legacy semantics.
- Keep scenario mapping optional for ordinary test-result context; unmapped requirements coverage remains not evaluated.
- Preserve canonical selected outcomes and current plan/source/environment bindings, resource/parser bounds, offline operation and independent Code Review verdicts. Optional mapping binds its digest only when supplied.
- Supersede the unimplemented R07 correction. Closed #368 remains history and R08 #414 remains abandoned.

## Capabilities

### New Capabilities

- `requirements-current-run-evidence`: lean current reconciliation, honest independent claims and legacy compatibility.

## Impact

Planning only. Later implementation changes Requirements report/reconciliation and Code Review context consumption, help and examples, compatibility metadata and signed publication. It does not execute Git, pytest or network calls, redefine core CI authority, or require optional preflight.

## Dependencies and rollout

Use existing shipped core interfaces; coordinate any necessary extension with #740 without a circular release dependency. Publish the signed module before core adopts it. Explicit legacy red/final callers retain their stricter contracts. Rollback restores a compatible signed module/core pair; current-only evidence can never become chronology by inference.

## Workflow consumer alignment

The downstream `workflow-01-turn-orchestration` consumes these current claims without requiring prior local receipts, changing producer verdicts or promoting local state to protected CI authority. Its separate executor does not widen this reconciler. Modules #481 blocks workflow modules #483; the workflow is not an upstream dependency of R09.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#481](https://github.com/nold-ai/specfact-cli-modules/issues/481)
- **Parent Feature**: #163
- **Paired Core Story**: [#740](https://github.com/nold-ai/specfact-cli/issues/740)
- **Last Synced Status**: proposed / Todo, 2026-09-20
