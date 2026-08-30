## Context

Modules own Requirements mappings, maturity, deterministic plans, JUnit reconciliation, and report semantics. Core owns Git snapshot selection, isolated execution, timeouts, environments, artifacts, and CI enforcement.

The previous schema used one linear maturity ladder where a final passing current run implied or required a historical red basis. The corrected model represents two independent claims.

## Goals and Non-Goals

### Goals

- Keep proposal/readiness/mapping/selector planning deterministic.
- Finalize current-run execution from exact canonical JUnit identities.
- Represent historical chronology separately and honestly.
- Preserve both mandatory schema-v3 claim objects as Code Review provenance without verdict fusion.
- Keep compatibility explicit and migration-only.

### Non-Goals

- Run pytest, inspect Git history, or create worktrees inside the module.
- Infer complete runtime input closure.
- Define the global governance evidence graph.
- Make Requirements evidence change Code Review scores or exits.

## Decisions

### Version the corrected finalized report explicitly

The mapping sidecar remains `schema_version: "2"`; this change does not alter mapping schema. The finalized Requirements report increments from `schema_version: "2"` to `schema_version: "3"`. A v2 finalized report is routed only through the legacy compatibility reader, retains `source_schema_version: 2`, may omit the new claim objects, and preserves the shipped rule that a passing gate requires `red-junit` or matching digest-bound `legacy-tdd-ledger` proof basis. A v3 report MUST contain both claim objects and all v3 provenance; missing fields are malformed v3, never reinterpreted as legacy. Unsupported future versions remain rejected.

### Use two independent claim objects

`current_execution` records status, mapping/plan/source identities, exact selectors, result digest, collection counts, outcome counts, runner identity, and environment provenance supplied by core.

`red_green_chronology` is a mandatory placeholder claim object in the corrected R07 report. R07 has no chronology-request or capsule input and always emits `status: not_evaluated` with `reason: capsule_not_supplied`; it cannot emit chronology pass, fail, or unknown. No active change currently extends this claim. Any future chronology input, validation, or non-not-evaluated status requires a separately approved contract. The placeholder cannot erase or inflate current execution.

### Current reconciliation needs only current evidence

Final current-run reconciliation validates the original deterministic plan and trusted JUnit. Every exact selector must match one canonical result. Passing, failing, skipped, errored, missing, or ambiguous outcomes remain distinct.

A current execution pass must not be called `verified-red-green`, `passing-after-red`, or `change-proven` without independently validated chronology evidence from a separately approved contract.

### Legacy history remains labelled compatibility

Existing `legacy-tdd-ledger` payloads may remain readable for old artifacts. The command cannot generate them for new changes, and they cannot silently satisfy a new chronology claim.

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
2. Dual-read finalized report schema v2 and v3 during one compatibility release; write only schema v3 for corrected R07 output while leaving mapping sidecars at schema v2.
3. Publish a signed release for core adoption.
4. Remove generation of new legacy-ledger evidence after core migrates.
5. Roll back by disabling the new writer while preserving every already-written `current_execution` and `red_green_chronology` object byte-for-byte. The old reader must treat unknown corrected fields as opaque provenance and must never reinterpret them as legacy chronology.
6. After the implementation and signed handoff merge, finalize the shipped change from the repository root with `openspec archive requirements-07-scenario-runtime-proof`; never move the change directory manually.
