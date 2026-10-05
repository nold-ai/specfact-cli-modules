# Design: Optional Apple distribution trust

## Admission and dependency direction

Implement only after #460's native capsule is accepted and this optional story is explicitly prioritized. Missing Apple membership, certificates or notary credentials cannot fail the initial release. The current Apple credential preflight remains an optional utility; its successful result is not proof of private-key access, team association, boundary safety or distribution acceptance.

## Protected signing and artifact identity

Maintainers enroll in the Apple Developer Program and provision Developer ID Application identities and notary authentication in the protected release environment. PR builds and customer machines receive no credentials. Record exact signature identities, narrowly reviewed entitlements and hardened-runtime settings; review tracing effects on code-signing enforcement. Sign before computing final distributed payload digests, notarize the applicable distribution and staple tickets where supported. Bind SpecFact-signed manifests and acceptance to the actual final bytes, including packaging changes.

## Acceptance and rollback

Changed signing configuration requires fresh boundary/tracing/library-loading proof, complete analyzer and project-manager suites, Linux regressions and fresh ordinary-user CLI/GHCR installation on each advertised macOS/ABI combination. Preserve the five-second cleanup bound and 100 lifecycle-race repetitions from #460. Credential availability, notarization or prior ad-hoc evidence alone cannot promote the artifact. Keep host protections enabled and avoid quarantine stripping or security overrides.

Manage expiration, renewal, revocation and unavailable notary services as explicit promotion failures. Never rewrite immutable historical payloads. Withdraw the affected Apple-signed publication and retain accepted initial-distribution and Linux artifacts; do not automatically downgrade customer caches or reinterpret failed acceptance as success.

## References

Inspected 2026-10-02: [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), [trusted execution](https://developer.apple.com/forums/thread/706442), [tracing warning](https://developer.apple.com/videos/play/wwdc2019/703/).
