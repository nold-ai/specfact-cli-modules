# Change: Isolate Dynamic Paired-Core Validation From Manual Cache Scope

## Why

Three validation workflows combine dynamic paired-core branch checkouts with a
manual-dispatch trigger that writes in the default-branch cache scope. Their
step conditions prevent the dynamic checkout during manual runs, but GitHub's
workflow security model cannot prove that event-level separation across the
job. The safer contract is to keep dynamic paired-core execution only in
pull-request and protected-branch push contexts.

## What Changes

- Remove `workflow_dispatch` from the three workflows that dynamically resolve
  and execute paired-core source.
- Preserve same-named paired-core branch validation for pull requests and the
  existing `main`/`dev` push behavior.
- Replace the previous manual-ref contract tests with trigger-isolation
  contracts that fail if a default-cache-writing manual trigger is reintroduced
  beside the dynamic checkout.
- Correct `specfact-code-review` runtime compatibility metadata from an exact
  core identity to the proven range `>=0.55.1,<1.0.0`; the upper boundary is
  required by the current Codebase and Requirements dependency manifests.
- Keep the immutable core 0.55.1 smoke as minimum-version evidence while the
  paired-core quality job validates the candidate against the current core.

## Capabilities

### New Capabilities

- `module-core-runtime-compatibility`: module releases declare evidence-backed
  ranges bounded by their required dependency graph.

### Modified Capabilities

- `paired-core-workflow-ref-trust`: dynamic paired-core validation is no longer
  manually dispatchable from the same workflow.

## Impact

- The cache-scope correction affects `.github/workflows/docs-review.yml`,
  `.github/workflows/pr-orchestrator.yml`,
  `.github/workflows/requirements-evidence.yml`, the focused workflow contract
  test, and this OpenSpec change.
- Manual **Run workflow** actions for these three files are removed. Pull
  requests, protected-branch pushes, and GitHub's rerun controls remain.
- Bumps and re-signs the `specfact-code-review` manifest for a one-time
  compatibility correction. The canonical post-merge publisher owns the new
  immutable archive and registry-index promotion.
- Updates focused manifest, runtime, and workflow contracts plus active
  change-order guidance for that correction.
- Declares `packaging` directly in the default test environment because focused
  compatibility tests import it during collection.
- Does not change analyzer behavior, frozen C14 provenance identities,
  runtime bundle dependencies, or source-code contracts.
- The authoritative scanner records remain in GitHub Security. In accordance
  with `SECURITY.md`, no public vulnerability issue or exploit detail is added.

## Assumptions And Rollback

- Assumption: manual dispatch convenience is less important than an analyzer-
  enforceable cache trust boundary. If a manual entrypoint is required later,
  it needs a separate design that contains no dynamic paired-core checkout.
- Rollback is a single revert of the workflow triggers, test contract, and
  OpenSpec delta. Reintroducing the old trigger also reintroduces the security
  analysis failure and is not a safe steady state.
- Assumption: core 0.55.1 is the earliest supported runtime. Required Codebase
  and Requirements modules currently cap compatibility below core 1.0.0, so
  the parent advertises the same ceiling. Remove that ceiling only after the
  dependency graph is widened and validated; rollback is a metadata-only patch
  release that narrows the range.
