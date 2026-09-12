# Change: Repair Customer Capsule Execution

## Why

Ordinary non-root Code Review on an external repository encountered private runtime access, namespace denial, a Python 3.12 integrity failure, and directory creation failure. Current CI authenticates prefetch and runs a Python-only capsule smoke under sudo, so its green matrix does not prove the customer path. See [investigation](INVESTIGATION.md) for verified evidence and remaining unknowns.

## What Changes

- Specify public cold-cache installation and actual non-root review on GitHub-hosted Ubuntu 24.04 x86-64 for Python 3.11, 3.12, and 3.13.
- Require actionable acquisition, namespace, integrity, and filesystem diagnostics while preserving sealed runtime verification and fail-closed assurance.
- Require mount destinations to exist before sealing composition, private writable state, and immutable identity updates for any changed runtime structure.
- Schedule reproduction, failing-first regressions, bounded repairs, signed patch publication, and release-installed validation as future unchecked work.

## Capabilities

### New Capabilities

None. This is a corrective extension of existing capsule behavior.

### Modified Capabilities

- `review-run-command`: Non-root customer execution, truthful failure diagnostics, private runtime writes, and actual analyzer coverage.
- `code-review-tool-dependencies`: Anonymous acquisition, deterministic verified materialization, namespace prerequisites, and release-installed validation.

The delta requirements apply to the current signed capsule path. They do not reactivate historical host-PATH provisioning or missing-tool skip semantics in older canonical specifications. Completed C14 contracts remain reference context; this change is independent implementation authority after acceptance.

## Impact

This delivery changes OpenSpec planning artifacts and change ordering only. Future bounded repairs may touch capsule acquisition/materialization, sandbox composition/launch, related analyzer state paths, customer CI, and documentation. No CLI syntax or report schema change is approved; diagnostics use existing evidence surfaces and preserve authoritative status/exit semantics.

If signed payloads change later, bump `packages/specfact-code-review/module-package.yaml` by a patch version and update authenticated resource identities, module signatures, and `registry/index.json` through canonical tooling. Publish any changed OCI assets under new immutable identities. Reconcile resource/checkpoint bindings without overwriting historical evidence. Customer docs must explain supported prerequisites and troubleshooting while preserving existing published permalinks.

## Dependencies

- Issue [#466](https://github.com/nold-ai/specfact-cli-modules/issues/466), type Bug, assignee djm81, project SpecFact CLI, status Todo, no milestone.
- Native parent Feature [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under Epic #162.
- No open prerequisites; completed #416 and #459 are related baseline evidence.
- Blocks [core #680](https://github.com/nold-ai/specfact-cli/issues/680); preserve its existing #431 and completed #459 dependencies.
- Native-platform #460 is related downstream work; no redundant transitive blocker is added. Native support, C15, and Requirements behavior are outside this correction.

## Acceptance Criteria

- Planning artifacts, scenario-based deltas, planned Requirements evidence, and ordered future tasks validate strictly.
- GitHub type, labels, assignee, parent, project/status, and native dependency relationships match this proposal and are read back.
- The planning PR targets dev, uses Refs #466, and leaves the bug open/Todo and future work unchecked.
- Future runtime acceptance is defined by the two delta specifications; planning acceptance does not establish runtime correctness.

## Non-Goals

No production code, runtime tests, workflow edits, release artifacts, version bumps, platform expansion, issue closure, or archive operation in this planning delivery. No unsandboxed fallback, signature bypass, host-wide namespace-policy changes, or automatic elevation is authorized.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #466
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/466>
- **Last Synced Status**: proposed; Todo; implementation not started
- **Sanitized**: true
