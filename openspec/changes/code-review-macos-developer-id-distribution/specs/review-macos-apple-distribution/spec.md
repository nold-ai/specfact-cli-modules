## ADDED Requirements

### Requirement: Optional Apple distribution dependency

Developer ID signing and notarization SHALL be optional follow-up work blocked by accepted native capsule delivery under #460. This story SHALL NOT block #460 implementation, execution, shipment or canonical GHCR publication. Maintainer credentials SHALL remain in protected release environments and SHALL NOT be required on customer machines or in PR builds.

#### Scenario: Apple credentials are absent during initial delivery

- **WHEN** the initial capsule has no Developer ID certificate or notary credentials
- **THEN** this follow-up remains deferred and cannot fail initial delivery's independent integrity, boundary and installation acceptance

#### Scenario: Optional promotion is requested without prerequisites

- **WHEN** Apple-specific promotion lacks accepted native delivery or valid protected signing/notary configuration
- **THEN** only the optional promotion is blocked; accepted initial and Linux distributions remain available

### Requirement: Exact Apple-signed distribution acceptance

The optional distribution SHALL verify Developer ID signatures, narrow reviewed entitlements, hardened-runtime behavior, notarization and applicable ticket stapling. Final payload manifests SHALL authenticate actual distributed bytes. Fresh boundary, tracing, library-loading, complete analyzer/project-manager and native/Linux installation suites SHALL be bound to the final artifact; credentials, notarization and prior ad-hoc results alone SHALL NOT establish acceptance. Certificate expiry, renewal, revocation and notary failures SHALL be handled without rewriting immutable historical artifacts.

#### Scenario: Signing configuration changes

- **WHEN** the previously accepted runtime is repackaged with Developer ID signing or changed entitlements
- **THEN** promotion requires fresh final-artifact acceptance, including independent ordinary-user default-protection installation, five-second cleanup and 100 repetitions per lifecycle race

#### Scenario: Apple promotion fails or its certificate is revoked

- **WHEN** mandatory Apple-specific validation fails or a published signing certificate becomes invalid
- **THEN** promotion fails or the affected publication is withdrawn while accepted initial/Linux artifacts and diagnostic evidence are preserved
