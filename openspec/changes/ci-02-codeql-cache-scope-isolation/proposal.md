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

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `paired-core-workflow-ref-trust`: dynamic paired-core validation is no longer
  manually dispatchable from the same workflow.

## Impact

- Affects only `.github/workflows/docs-review.yml`,
  `.github/workflows/pr-orchestrator.yml`,
  `.github/workflows/requirements-evidence.yml`, the focused workflow contract
  test, and this OpenSpec change.
- Manual **Run workflow** actions for these three files are removed. Pull
  requests, protected-branch pushes, and GitHub's rerun controls remain.
- Does not change module source, manifests, registry metadata, versions,
  signatures, dependency files, package publishing, or C14 artifacts.
- The authoritative scanner records remain in GitHub Security. In accordance
  with `SECURITY.md`, no public vulnerability issue or exploit detail is added.

## Assumptions And Rollback

- Assumption: manual dispatch convenience is less important than an analyzer-
  enforceable cache trust boundary. If a manual entrypoint is required later,
  it needs a separate design that contains no dynamic paired-core checkout.
- Rollback is a single revert of the workflow triggers, test contract, and
  OpenSpec delta. Reintroducing the old trigger also reintroduces the security
  analysis failure and is not a safe steady state.
