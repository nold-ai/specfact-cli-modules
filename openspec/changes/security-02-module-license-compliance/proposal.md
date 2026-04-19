# Change: License Compliance Module

## Why

License governance needs a focused runtime bundle that evaluates SBOM and SPDX license data against policy without burying those concerns inside a broader scanner module. A dedicated package keeps licensing auditable, policy-driven, and independently deployable for users who need supply-chain governance without the full security stack.

## What Changes

- **NEW**: Add a `specfact-license-compliance` bundle with a `license` command focused on SBOM and SPDX license evaluation.
- **NEW**: Package SBOM ingestion and SPDX normalization adapters that feed the paired core security/license findings model.
- **NEW**: Add policy-aware handling for allowed, denied, and exception-based license states so reports can surface explicit remediation guidance.
- **NEW**: Define bundle manifest, registry, docs, and signing expectations for a first-party official license-compliance package.
- **EXTEND**: Reserve compatibility hooks so this bundle can share generated SBOM data with the broader security bundle without forcing a single runtime package.

## Capabilities

### New Capabilities

- `license-compliance-module`: Runtime bundle, command surface, and SPDX/SBOM evaluation flow for license governance.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-license-compliance/`, SBOM ingestion helpers, and policy mapping resources.
- Affected docs: bundle overview and command-reference documentation for `license`.
- Dependencies: paired core changes `security-01-unified-findings-model` and `security-02-eu-gdpr-baseline` for shared policy-pack semantics where relevant.
- Release impact: introduces a new signed official bundle and registry entry.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#218](https://github.com/nold-ai/specfact-cli-modules/issues/218)
- **GitHub Issue**: [#228](https://github.com/nold-ai/specfact-cli-modules/issues/228)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/228>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
