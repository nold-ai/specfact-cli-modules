# Change: Optional Developer ID signing and notarization for macOS capsules

## Why

Apple-recognized publisher identity and notarization can improve distribution trust. Paid membership is deferred while initial native delivery proves its actual install route with default host protections.

## What Changes

- Add optional maintainer Developer ID Application signing, notarization and applicable ticket stapling through protected release credentials.
- Manage certificate expiry, renewal and revocation without rewriting immutable historical artifacts.
- Re-run tracing, confinement, loading, complete native/Linux suites and independent ordinary-user installation against the exact final Apple-signed payload.
- Preserve SpecFact manifest authentication, lifecycle guarantees and honest trust evidence; credentials and notarization alone never prove sandbox safety.

## Capabilities

### New Capabilities

- `review-macos-apple-distribution`: optional Apple publisher trust and artifact-bound distribution acceptance.

### Modified Capabilities

None until explicitly prioritized and implemented.

## Dependencies and Impact

Optional and unscheduled. #460 / `code-review-native-platform-execution` blocks this follow-up; this change does not block #460 implementation, capsule shipment or canonical GHCR publication. Parent Feature #163 under Epic #162; Project SpecFact CLI. Initial ad-hoc distribution remains eligible only after its own complete acceptance. A failed Apple promotion withdraws only the affected artifact and preserves accepted initial/Linux distributions.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#488](https://github.com/nold-ai/specfact-cli-modules/issues/488)
- **Prerequisite**: [#460](https://github.com/nold-ai/specfact-cli-modules/issues/460), [native proposal](../code-review-native-platform-execution/proposal.md)
- **Last Synced Status**: open / Todo, optional and unscheduled, 2026-10-02 Europe/Berlin
