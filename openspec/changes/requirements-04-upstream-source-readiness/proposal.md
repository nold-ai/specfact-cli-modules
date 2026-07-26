## Why

The import-first runtime shipped by `openspec-01-intent-trace` can turn an
unfinished native source into apparently valid requirement evidence. A pristine
Spec Kit 0.12.15 scaffold produced six placeholder records during local
end-to-end testing. Invalid OpenSpec changes need the same protection when the
repository policy requires native OpenSpec validation.

Evidence must be trustworthy before it reaches coverage and CI gates. An
incomplete or upstream-invalid source must be reported clearly, not silently
normalised into misleading records.

## What Changes

- Add a core-owned upstream-source readiness contract for native OpenSpec and
  Spec Kit imports; the Requirements module only delegates and renders its
  results.
- Reject incomplete Spec Kit sources that retain known official template
  markers, unresolved `NEEDS CLARIFICATION` markers, no substantive functional
  requirements, or no meaningful acceptance scenario where user stories exist.
- Reject OpenSpec sources whose strict native validation fails when an explicit
  or strict/enterprise upstream-validation policy requires the OpenSpec CLI.
- Return structured diagnostics and a non-zero result while persisting zero
  requirement records for any rejected source.
- Preserve completed native imports, stable identifiers, hash provenance,
  idempotency, read-only source behavior, and portable basic imports.
- Dogfood this shipped OpenSpec source through the Requirements evidence adapter
  with an explicit test-link sidecar, so the source-readiness claim has
  machine-readable traceability evidence rather than only historical test logs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `requirements-module`: Native OpenSpec and Spec Kit import gains
  source-readiness diagnostics and fail-closed persistence semantics.

## Impact

- Paired core dependency: `nold-ai/specfact-cli#648` owns native readiness
  evaluation, the OpenSpec CLI adapter/policy, and diagnostic contracts. This
  modules change is blocked until that contract ships.
- Affected modules code: `packages/specfact-requirements` import command and
  thin runtime delegation.
- Affected tests: Requirements module command/runtime integration coverage,
  source read-only/idempotency regression coverage, and an actual-source
  Requirements evidence replay covering this change together with #352.
- Affected user docs: Requirements import examples and diagnostic guidance.
- Release impact: patch release of `nold-ai/specfact-requirements` after the
  paired core compatibility floor is available; no registry or signed manifest
  change belongs in this proposal-only change.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #346
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/346>
- **Parent Feature**: #161 Context Adapters For Validation Evidence
- **Follow-up To**: #168
- **Core Counterpart**: nold-ai/specfact-cli#648
- **Last Synced Status**: reopened for traceability repair (aligned 2026-07-26)
- **Sanitized**: false
