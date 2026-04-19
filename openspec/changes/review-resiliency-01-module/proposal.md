# Change: Review Resiliency Module

## Why

The core repo can define resiliency contracts and scoring, but SpecFact still lacks a modules-side bundle that actually runs resiliency-oriented checks against repositories. Without a dedicated bundle, operational-scalability review remains a paper capability instead of a runnable part of the platform.

## What Changes

- **NEW**: Add a `specfact-review-resiliency` bundle scaffold under `packages/` with `review-resiliency` as its primary command.
- **NEW**: Package deterministic resiliency rule packs for retry, timeout, idempotency, backpressure, and graceful-degradation checks that map into the paired core findings contract.
- **NEW**: Add optional probe adapters for lightweight load-profile validation behind explicit opt-in flags so default review runs stay local-first and safe for CI.
- **NEW**: Emit findings in the shared review report shape and, when the knowledge bundle is installed, forward evidence metadata to the memory runtime without making that integration mandatory.
- **EXTEND**: Document the new bundle on modules docs and declare manifest, registry, and bundle-dependency expectations for later implementation.

## Capabilities

### New Capabilities

- `review-resiliency-module`: Runtime bundle, command surfaces, packaged rule sets, and evidence adapters for resiliency review.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-review-resiliency/`, bundle loader wiring, and rule resources under `resources/`.
- Affected docs: bundle overview and command-reference pages on modules.specfact.io for resiliency review.
- Dependencies: paired core change `review-resiliency-01-contracts`; optional knowledge integration with `knowledge-01-module-memory-runtime`.
- Release impact: introduces a new signed official bundle with a new `module-package.yaml` and registry entry.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#217](https://github.com/nold-ai/specfact-cli-modules/issues/217)
- **GitHub Issue**: [#226](https://github.com/nold-ai/specfact-cli-modules/issues/226)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/226>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
