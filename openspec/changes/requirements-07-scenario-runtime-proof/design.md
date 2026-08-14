## Context

Modules own Requirements mappings, maturity, deterministic plans, JUnit reconciliation, and report semantics. Core owns Git snapshot selection, isolated execution, timeouts, environments, artifacts, and CI enforcement.

The previous schema used one linear maturity ladder where a final passing current run implied or required a historical red basis. The corrected model represents two independent claims.

## Goals and Non-Goals

### Goals

- Keep proposal/readiness/mapping/selector planning deterministic.
- Finalize current-run execution from exact canonical JUnit identities.
- Represent historical chronology separately and honestly.
- Preserve both claims as optional Code Review provenance without verdict fusion.
- Keep compatibility explicit and migration-only.

### Non-Goals

- Run pytest, inspect Git history, or create worktrees inside the module.
- Infer complete runtime input closure.
- Define the global governance evidence graph.
- Make Requirements evidence change Code Review scores or exits.

## Decisions

### Use two independent claim objects

`current_execution` records status, mapping/plan/source identities, exact selectors, result digest, collection counts, outcome counts, runner identity, and environment provenance supplied by core.

`red_green_chronology` records status and optional R08 attestation identity. Missing chronology is `unproven`/`not_evaluated` according to the versioned report contract and cannot erase or inflate current execution.

### Current reconciliation needs only current evidence

Final current-run reconciliation validates the original deterministic plan and trusted JUnit. Every exact selector must match one canonical result. Passing, failing, skipped, errored, missing, or ambiguous outcomes remain distinct.

A current execution pass must not be called `verified-red-green`, `passing-after-red`, or `change-proven` without an independently validated R08 capsule.

### Legacy history remains labelled compatibility

Existing `legacy-tdd-ledger` payloads may remain readable for old artifacts. The command cannot generate them for new changes, and they cannot silently satisfy the new R08 chronology claim.

### Review context is provenance-only

Code Review validates the finalized Requirements report and retains separate current-execution and chronology fields. Missing historical proof is not a malformed current-run report. Requirements status does not alter review findings, score, or exit code.

## Implementation Boundary

This planning commit touches OpenSpec only. Later implementation is limited to:

- Requirements lifecycle/report/reconciliation models;
- the public reconciliation command;
- the Code Review Requirements-context adapter;
- focused unit/contract fixtures and docs;
- bundle version/signature/registry updates only after behavior is ready.

Do not add Git orchestration, pytest execution, or static import/plugin/configuration analysis to modules.

## Rollout and Rollback

1. Add failing schema and reconciliation tests.
2. Dual-read old reports and dual-write the corrected fields during one compatibility release.
3. Publish a signed release for core adoption.
4. Remove generation of new legacy-ledger evidence after core migrates.
5. Roll back by keeping the old reader while disabling the new writer; never collapse the two claims again.

