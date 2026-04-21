# Change: License Compliance Module

## Why

License governance needs a focused runtime bundle that evaluates SBOM and SPDX license data against policy without burying those concerns inside a broader scanner module. A dedicated package keeps licensing auditable, policy-driven, and independently deployable for users who need supply-chain governance without the full security stack.

## What Changes

- **NEW**: Add a `specfact-license-compliance` bundle with a `license` command focused on SBOM and SPDX license evaluation.
- **NEW**: Package SBOM ingestion and SPDX normalization adapters that feed the paired core security/license findings model.
- **NEW**: Add policy-aware handling for allowed, denied, and exception-based license states so reports can surface explicit remediation guidance.
- **NEW**: Define bundle manifest, registry, docs, and signing expectations for a first-party official license-compliance package.
- **EXTEND**: Reserve compatibility hooks so this bundle can share generated SBOM data with the broader security bundle without forcing a single runtime package.

### Adapter Contract

The adapter boundary between SBOM/license analyzers and the core security/license findings model specifies how license evaluation flows into the normalized findings contract:

- **Core Findings Schema Fields**: Same as `security-01-unified-findings-model` (reused for license findings): `id`, `type`, `severity`, `description`, `source`, `timestamp`, `evidence_refs`
- **SPDX-to-Normalized Finding Mapping Rules**:
  - Denied SPDX identifier → `severity: "high"`, `type: "license-violation"`
  - Allowed SPDX identifier → `severity: "info"`, `type: "license-compliant"`
  - Exception-based allow → `severity: "medium"`, `type: "license-exception-applied"`
  - Unknown/missing license → `severity: "medium"`, `type: "license-unknown"`

## Capabilities

### New Capabilities

- `license-compliance-module`: Runtime bundle, command surface, and SPDX/SBOM evaluation flow for license governance.

### Modified Capabilities

_None.

### Inter-Bundle Compatibility

- **Core Compatibility Version Range**: `core_compatibility: ">=1.0.0 <2.0.0"` for `security-01-unified-findings-model` in `module-package.yaml`
- **Inter-Bundle Hook Interface**: The bundle can optionally emit SBOM artifacts to a shared location (e.g., `.specfact/sbom/`) that the `security` bundle can consume, enabling SBOM reuse without runtime coupling
- **Bundle Dependencies Declaration**: If shared policy semantics from `policy-02-packs-and-modes` are required, declare it under `bundle_dependencies` (not `core_compatibility`)

## Impact

- Affected code: future `packages/specfact-license-compliance/`, SBOM ingestion helpers, and policy mapping resources.
- Affected docs: bundle overview and command-reference documentation for `license`.
- Dependencies: This proposal depends on `security-01-unified-findings-model` and the shared policy-pack semantics from `policy-02-packs-and-modes`.
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