# Change: Repair Customer Capsule Execution

## Current disposition — 2026-09-21 (Europe/Berlin)

Issue [#466](https://github.com/nold-ai/specfact-cli-modules/issues/466) is closed as completed (2026-09-13) and its project status is Done. The implementation and acceptance checkpoints below are historical, not pending delivery instructions. Retain existing release/test records and reconcile them before native OpenSpec archival; issue closure alone does not verify every acceptance item.

## Why

Ordinary non-root Code Review on an external repository encountered private runtime access, namespace denial, a Python 3.12 integrity failure, and directory creation failure. At the investigation baseline, CI authenticated prefetch and ran a Python-only capsule smoke under sudo, so that matrix did not prove the customer path. The corrective implementation now adds a real customer execution gate. See [investigation](INVESTIGATION.md) for verified evidence and remaining unknowns.

## What Changes

- Specify public cold-cache installation and actual non-root review on GitHub-hosted Ubuntu 24.04 x86-64 for Python 3.11, 3.12, and 3.13.
- Require actionable acquisition, namespace, integrity, and filesystem diagnostics while preserving sealed runtime verification and fail-closed assurance.
- Require mount destinations to exist before sealing composition, private writable state, and immutable identity updates for any changed runtime structure.
- Implement reproduced acquisition, mount-composition, umask and diagnostic repairs with failing-first regression evidence; at the implementation checkpoint, signed publication and release-installed acceptance were pending.

## Capabilities

### New Capabilities

None. This is a corrective extension of existing capsule behavior.

### Modified Capabilities

- `review-run-command`: Non-root customer execution, truthful failure diagnostics, private runtime writes, and actual analyzer coverage.
- `code-review-tool-dependencies`: Anonymous acquisition, deterministic verified materialization, namespace prerequisites, and release-installed validation.

The delta requirements apply to the current signed capsule path. They do not reactivate historical host-PATH provisioning or missing-tool skip semantics in older canonical specifications. Completed C14 contracts remain reference context; this correction was independently authorized and is now retained for reconciliation, not further implementation authority.

## Historical implementation impact

Implementation was explicitly authorized on 2026-09-12 Europe/Berlin. This delivery changes capsule acquisition/materialization, sandbox composition/launch, analyzer state paths, customer CI and documentation. No CLI syntax or report schema change is approved; diagnostics use existing evidence surfaces and preserve authoritative status/exit semantics.

If signed payloads change later, bump `packages/specfact-code-review/module-package.yaml` by a patch version and update authenticated resource identities, module signatures, and `registry/index.json` through canonical tooling. Publish any changed OCI assets under new immutable identities. Reconcile resource/checkpoint bindings without overwriting historical evidence. Customer docs must explain supported prerequisites and troubleshooting while preserving existing published permalinks.

## Dependencies

- Issue [#466](https://github.com/nold-ai/specfact-cli-modules/issues/466) is closed completed (read back 2026-09-20); the implementation-session details describe historical delivery, not new implementation authority.
- Native parent Feature [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under Epic #162.
- No open prerequisites; completed #416 and #459 are related baseline evidence.
- Shipped #466 and #459 remain baseline dependencies of [core #680](https://github.com/nold-ai/specfact-cli/issues/680). Optional preflight #431 is not a #680 prerequisite and must not be restored by this historical correction.
- Native-platform #460 is related downstream work; no redundant transitive blocker is added. Native support, C15, and Requirements behavior are outside this correction.

## Historical acceptance checkpoint — 2026-09-13

- Corrective implementation, scenario-based deltas, planned Requirements evidence, and recorded red/green tests validate strictly.
- GitHub type, labels, assignee, parent, project/status, and native dependency relationships match this proposal and are read back.
- Implementation PR #467 and canonical registry publication #468 are merged to dev; release PR #469 promotes the repair to main after review follow-up fixes and exact-head gates.
- The signed candidate customer matrix has passed all three Python versions. At that checkpoint, public signed-release acceptance remained pending under the two delta specifications; candidate evidence did not substitute for it.

## Historical corrective-delivery non-goals

Platform expansion, unrelated Requirements/C15 behavior, premature issue closure, and archive before public acceptance remain outside this corrective delivery. No unsandboxed fallback, signature bypass, host-wide namespace-policy changes, or automatic elevation is authorized.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #466
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/466>
- **Last Synced Status**: Closed completed; project Done (read back 2026-09-21 Europe/Berlin). Earlier In Progress/public-acceptance-pending records are historical; archive reconciliation remains separate.
- **Sanitized**: true
