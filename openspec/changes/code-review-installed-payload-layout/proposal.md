# Change: Repair C14 Installed Payload Layout Handling

## Why

A normal signed Code Review installation places Python code under src/specfact_code_review. C14 assumes specfact_code_review directly beneath the installed module root. Core signature verification succeeds, but handoff fails before analyzers execute. This is a correction to already-required C14 installed-module behavior, not a new trust exception.

## What Changes

- Resolve the supported src and flat package layouts consistently for manifest construction, re-verification, and capsule copying.
- Preserve actual install-relative paths, bytes, modes, signed provenance, and the existing capsule import destination.
- Add real installer integration coverage and specific handoff diagnostics without weakening fail-closed behavior.

## Capabilities

### New Capabilities

- `review-installed-payload-layout`: Requirements and verification obligations for the installed-payload correction only.

### Modified Capabilities

None in this planning delivery. Future implementation must reconcile these obligations with the then-current review contracts before modifying a public interface.

## Impact

Planning artifacts only. No runtime source, tests, schemas, versions, signatures, registry entries, or supported-platform claims change. Future signed bundle changes require semver/core compatibility and canonical publication. No current CLI/API additions are approved.

## Dependencies

- Parent: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under epic #162.
- Related completed implementation: modules [#416](https://github.com/nold-ai/specfact-cli-modules/issues/416).
- No open prerequisites; blocks core [#680](https://github.com/nold-ai/specfact-cli/issues/680).
- Blocks native execution [#460](https://github.com/nold-ai/specfact-cli-modules/issues/460).
- Do not depend on C15 or the preflight release chain: core #680 is upstream of that chain.

## Acceptance Criteria

- This change has proposal, design, scenario-based spec deltas, ordered future tasks, and planned Requirements evidence.
- GitHub type, assignee, parent, project Todo status, labels, and native dependency relationships match this proposal.
- Strict OpenSpec validation, Markdown checks, staged planned-maturity Requirements validation, and applicable planning review pass.
- The planning PR targets dev, references the issue without closing it, and leaves implementation tasks unchecked.
- Future behavior acceptance is defined in specs/review-installed-payload-layout/spec.md; planning acceptance does not establish runtime correctness.

## Non-Goals

No production implementation, runtime tests, release actions, implementation completion, or archive operation in this PR. Existing unrelated changes remain untouched.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #459
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/459>
- **Last Synced Status**: proposed; Todo; implementation not started
- **Sanitized**: true
