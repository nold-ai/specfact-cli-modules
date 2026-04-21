# Change: Security Module For SAST, SCA, And Secrets

## Why

The core repo can standardize security findings, but users still need a runnable bundle that orchestrates SAST, dependency, SBOM, and secret scans in one place. Without a dedicated module, the unified security model cannot produce real enforcement or evidence in everyday workflows.

## What Changes

- **NEW**: Add a `specfact-security` bundle under `packages/` with a `security` command for SAST, SCA, SBOM, and secret scanning.
- **NEW**: Package adapters for Semgrep, Syft, Grype or OSV-style dependency analysis, and secret scanning so their outputs normalize into the paired core finding model.
- **NEW**: Add profile-aware execution modes that honor advisory, mixed, and hard policy modes without duplicating policy semantics in the bundle.
- **NEW**: Define stable output surfaces for markdown and JSON security reports and optional evidence handoff to the knowledge runtime.
- **EXTEND**: Reserve manifest, registry, docs, and signing work required for a new official security bundle.

## Capabilities

### New Capabilities

- `security-sast-sca-secret-module`: Runtime bundle, analyzer orchestration, and normalized findings for SAST, SCA, SBOM, and secret scanning.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-security/`, bundled scanner adapters, and resource/configuration assets.
- Affected docs: new bundle overview plus command-reference documentation for `security`.
- Dependencies: paired core change `security-01-unified-findings-model`; related policy semantics from `policy-02-packs-and-modes`.
- Release impact: introduces a new official bundle with signing, registry, and compatibility declarations.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#218](https://github.com/nold-ai/specfact-cli-modules/issues/218)
- **GitHub Issue**: [#227](https://github.com/nold-ai/specfact-cli-modules/issues/227)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/227>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
