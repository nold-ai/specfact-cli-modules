## ADDED Requirements

### Requirement: Evidence-backed hardening scope

Every hardening change SHALL map to an accepted dogfood observation, affected contract path, generalized rule, regression case, and owning component.

#### Scenario: Proposed change has no dogfood evidence

- **GIVEN** an enhancement is not required by the approved contract and has no accepted dogfood observation
- **WHEN** hardening scope is reviewed
- **THEN** the enhancement is excluded from the release-blocking scope
- **AND** may be filed as a separate hypothesis or follow-up.

#### Scenario: Dogfood finding becomes a regression case

- **GIVEN** the core readiness decision accepts a reproducible runtime defect
- **WHEN** hardening begins
- **THEN** a failing test captures the generalized rule before production code changes
- **AND** the fix is limited to satisfying that approved rule.

### Requirement: Complete regression rerun

The hardened module SHALL rerun the accepted C14 dogfood corpus and the declared independent regression cases after each contract-affecting fix.

#### Scenario: Fix changes a core contract meaning

- **GIVEN** a proposed runtime fix requires changing a core schema or verifier semantic
- **WHEN** the fix is reviewed
- **THEN** modules implementation stops
- **AND** a separately accepted core contract change and new dogfood approval are required.

### Requirement: Atomic stable release surface

The final module source, workflow assets, manifest, version, core compatibility, registry metadata, checksums, signatures, and publication evidence SHALL describe one exact release identity.

#### Scenario: Signed payload and manifest differ

- **GIVEN** any signed payload, workflow asset, manifest field, or registry identity changes after signing
- **WHEN** release verification runs
- **THEN** publication is blocked
- **AND** the versioned payload is regenerated and signed through the official release flow.

### Requirement: Exact compatibility proof

The stable release SHALL advertise only core identities proven by a fresh official installation, module discovery/load, contract verification, CLI matrix, and canonical workflow invocation test.

#### Scenario: Proposed compatibility range admits untested core versions

- **GIVEN** the release matrix proves only one exact core version
- **WHEN** compatibility metadata is prepared
- **THEN** metadata does not advertise a wider version range
- **AND** future core identities require their own immutable compatibility evidence.

#### Scenario: Compatibility metadata has no matrix proof

- **GIVEN** core compatibility metadata is empty or names an identity or range without matching immutable release-matrix evidence
- **WHEN** the official publication pre-check runs
- **THEN** it fails before signing or registry publication
- **AND** a warning-only result cannot authorize the release.

### Requirement: Signed publication handoff

Downstream stories SHALL receive the immutable published module version, artifact digest, signature identity, registry identity, compatible core identity, and completed regression result.

#### Scenario: Downstream adoption starts from a feature build

- **GIVEN** only an unpublished branch artifact exists
- **WHEN** #251, preflight conformance, adapters, or C15 checks readiness
- **THEN** the dependency remains unresolved
- **AND** feature-branch output cannot satisfy the stable handoff.

### Requirement: Release rollback

The release SHALL have a tested withdrawal or supersession path that prevents downstream installers from selecting or installing a known-bad identity, and publication SHALL remain blocked until that path is proven.

#### Scenario: Registry cannot make a known-bad identity unavailable

- **GIVEN** the selected registry or installer has no supported version-level withdrawal, supersession, or rejection mechanism
- **WHEN** release readiness is evaluated
- **THEN** publication is blocked
- **AND** a latest-entry update or checksum check alone cannot satisfy rollback readiness.

#### Scenario: Post-publication verification fails

- **GIVEN** a published release fails a required compatibility or integrity check
- **WHEN** rollback is initiated
- **THEN** the supported registry operation marks the faulty identity unavailable and the installer rejects it before installation
- **AND** the last verified identity remains authoritative until a newly verified release exists.
