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

The final module source, workflow assets, delegated CLI identity, manifest, version, core compatibility, registry metadata, structured release-history entry, checksums, signatures, and publication evidence SHALL describe one exact release identity. The signed workflow version/digest and delegated CLI identity SHALL be verified as one bound tuple through the official installation or preflight path. Every correction or withdrawal after publication SHALL use a new patch version, while the prior artifact, digest, signature, registry record, and release-history entry remain immutable and retained as historical evidence.

#### Scenario: Signed payload and manifest differ

- **GIVEN** any signed payload, workflow asset, manifest field, or registry identity changes after signing
- **WHEN** release verification runs
- **THEN** publication is blocked
- **AND** the versioned payload is regenerated and signed through the official release flow.

#### Scenario: Release history or workflow binding is incomplete

- **GIVEN** the new module version lacks its structured release-history entry or the installed workflow/CLI tuple does not match the signed release identity
- **WHEN** publication verification runs
- **THEN** publication is blocked
- **AND** no downstream handoff is emitted for that version.

#### Scenario: Post-publication correction reuses a version

- **GIVEN** a published identity requires correction, withdrawal, or supersession
- **WHEN** release tooling prepares replacement bytes or metadata under the same version
- **THEN** publication is blocked
- **AND** the correction uses a new patch version without replacing or deleting the prior artifact, digest, signature, registry record, or release-history entry.

### Requirement: Bounded compatibility proof

The stable release SHALL advertise a dependency-backed bounded core range. Its inclusive minimum SHALL be the first immutable released core containing the accepted #682 preflight contracts, proven by official tag, full commit, and full tree; its exclusive maximum SHALL remain aligned with every required module dependency. The release matrix SHALL exercise that exact minimum and selected current in-range core versions across supported Python versions, while versions below the minimum or at or above the upper bound are rejected. A compatible in-range core update SHALL NOT require a module metadata release; changing either bound SHALL require new dependency and matrix evidence.

#### Scenario: Proposed compatibility range exceeds dependency bounds

- **GIVEN** compatibility metadata lowers the proven minimum, removes or widens the dependency-backed upper bound, or otherwise admits a core version rejected by a required module dependency
- **WHEN** compatibility metadata is prepared
- **THEN** publication is blocked
- **AND** the range is not widened until matching dependency manifests and the supported matrix prove the new bounds.

#### Scenario: Compatibility metadata has no matrix proof

- **GIVEN** core compatibility metadata is empty or names an identity or range without matching immutable release-matrix evidence
- **WHEN** the official publication pre-check runs
- **THEN** it fails before signing or registry publication
- **AND** a warning-only result cannot authorize the release.

#### Scenario: Minimum provenance or bounded admission is weakened

- **GIVEN** the release proposes empty compatibility, exact-only equality, ordinary equality (`==`), wildcard, an unbounded range, a minimum before the first immutable core release containing #682, an upper bound above the required dependency graph, or a tag/commit/tree that does not identify the declared minimum
- **WHEN** the official publication pre-check runs
- **THEN** it fails before signing
- **AND** only a bounded range with matching immutable-minimum, dependency, and supported-matrix evidence can authorize publication.

### Requirement: Signed publication handoff

Downstream stories SHALL receive the immutable published module version, artifact digest, signature identity, registry identity, compatible core identity, signed canonical workflow version/digest, delegated CLI identity, and completed regression result.

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
- **AND** a prior verified identity remains authoritative when one exists
- **AND** after failure of the first stable publication, no preflight identity remains installable until a newly verified release exists.

#### Scenario: Candidate persistence cannot survive rollback

- **GIVEN** the candidate can write a persisted schema that the last verified module cannot read, or no prior stable preflight baseline exists
- **WHEN** release readiness is evaluated
- **THEN** publication is blocked until a tested backward-read, migration with backup/restore, or explicit no-install/reset outcome is available
- **AND** rollback evidence does not claim unsupported persisted state remains readable.
