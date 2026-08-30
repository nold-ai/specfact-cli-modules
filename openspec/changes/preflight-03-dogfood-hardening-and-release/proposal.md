# Change: Evidence-Backed Preflight Hardening and Stable Publication

## Why

The unpublished preflight runtime must not become a stable module or a dependency of C15 based only on proposal confidence. It needs fixes and regression coverage derived from the core C14 dogfood evidence, followed by the repository's signed publication and compatibility proof.

## What Changes

- **MODIFY**: Harden only validators, workflow behavior, rendering, persistence, or module contracts that have a reproducible dogfood finding and generalized regression case.
- **NEW**: A bounded regression corpus covering the accepted C14 findings plus stale-input, unknown-validator, approval, renderer-parity, and cross-repository dependency cases.
- **NEW**: Stable module versioning, exact core compatibility proof, manifest, registry, and structured release-history updates, signing, publication evidence, and install/load smoke through the official module path.
- **NEW**: A published canonical `specfact-preflight` skill/workflow asset consumable by generic skill installation and later harness adapters.
- **CLARIFY**: Speculative improvements remain follow-ups; release readiness cannot be inferred from one green dogfood narrative or unsigned feature-branch artifacts.

## Capabilities

### New Capabilities

- `preflight-assurance-release`: Evidence-gated hardening, compatibility proof, signing, and stable publication of the official preflight module.

### Modified Capabilities

- `preflight-assurance-runtime`: Harden runtime behavior only where accepted dogfood evidence requires it.
- `preflight-assurance-workflow`: Harden canonical workflow content and its CLI delegation without adding external adapter packages.

## Impact

- Planning artifacts only in this phase. No package source, tests, manifest, registry, signature, version, skill file, artifact, adapter, workflow, or release is changed now.
- Future implementation touches signed module surfaces and therefore requires version, compatibility, registry, publication, and signature gates as one release unit.
- External Codex/ECC/hatch3r packaging remains downstream in `preflight-04-harness-adapters`.

## Dependencies

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Blocked by modules `preflight-02-assurance-runtime` [#431](https://github.com/nold-ai/specfact-cli-modules/issues/431) and paired core `preflight-03-dogfood-hardening-and-release` readiness evidence [#683](https://github.com/nold-ai/specfact-cli/issues/683).
- Required selection order is core contract [#682](https://github.com/nold-ai/specfact-cli/issues/682) -> modules #431 -> core C14 [#680](https://github.com/nold-ai/specfact-cli/issues/680) -> core #683 -> this change; transitive prerequisites cannot be skipped merely because #431 and #683 are the direct native blockers.
- Publication is also conditional on a released core installer/registry contract that can reject a withdrawn exact version; absence of that interface requires a separately accepted core change before release work proceeds.
- Blocks core `preflight-05-implementation-conformance` [#684](https://github.com/nold-ai/specfact-cli/issues/684) and modules C15 [#417](https://github.com/nold-ai/specfact-cli-modules/issues/417). Modules #434 then consumes both this stable #432 handoff and core #684; core #251/#253 and modules #433 remain downstream of signed #434.

## Explicit Non-Goals

- No adapter packaging for Codex, ECC, hatch3r, or other external harnesses.
- No generated AGENTS.md/OpenSpec/Spec Kit instruction files.
- No postimplementation conformance comparison.
- No close or status change for modules C14 [#416](https://github.com/nold-ai/specfact-cli-modules/issues/416) without separate confirmation.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #432
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/432>
- **Cross-Repository Counterpart**: <https://github.com/nold-ai/specfact-cli/issues/683>
- **Last Synced Status**: proposed
- **Sanitized**: true
