# Change: FinOps Cost And Outcome Module

## Why

The core repo can define session evidence and budget contracts, but users still need a runtime bundle that collects cost and token data, classifies outcomes, and writes reusable evidence. Without a module-side implementation, the FinOps pillar cannot measure whether the platform is actually improving efficiency over time.

## What Changes

- **NEW**: Add a `specfact-finops` bundle with a `finops` command surface for collection, classification, and reporting.
- **NEW**: Package cost collectors for supported LLM providers plus a local-friendly fallback path for air-gapped or inference-only environments.
- **NEW**: Add an outcome classifier that maps session telemetry and downstream workflow results into the paired core outcome taxonomy.
- **NEW**: Emit evidence files compatible with the paired core FinOps schema and the knowledge distillation loop.
- **EXTEND**: Reserve manifest, registry, docs, and signing work for a first-party FinOps bundle.

## Capabilities

### New Capabilities

- `finops-cost-outcome-module`: Runtime bundle, collectors, classifiers, and reporting surfaces for FinOps evidence generation.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-finops/`, provider adapters, and evidence/report helpers.
- Affected docs: bundle overview and command-reference documentation for `finops`.
- Dependencies: paired core changes `telemetry-01-opentelemetry-default-on` and `finops-01-telemetry-and-outcomes`.
- Release impact: introduces a new signed official bundle and registry entry.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#220](https://github.com/nold-ai/specfact-cli-modules/issues/220)
- **GitHub Issue**: [#223](https://github.com/nold-ai/specfact-cli-modules/issues/223)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/223>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
