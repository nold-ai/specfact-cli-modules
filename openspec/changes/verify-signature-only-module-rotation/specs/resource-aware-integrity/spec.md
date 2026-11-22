## ADDED Requirements

### Requirement: Authenticate signature-only source manifest rotation

The version check SHALL allow a same-version signature-only source manifest change when the module is outside the immutable cutoff inventory, the exact replacement public key verifies the unchanged payload, and every other manifest byte and package Git entry is unchanged.

#### Scenario: Replacement signature over unchanged source

- **WHEN** the only package change is the signature on an existing source manifest
- **AND** full verification verifies the unchanged checksum and payload with the pinned replacement key
- **THEN** the version check allows the existing module version.

#### Scenario: Other changes or missing authentication

- **WHEN** the package or other manifest bytes change, the replacement signature fails, or only metadata is checked
- **THEN** the same-version exception is denied.

### Requirement: Authenticate capsule review controllers

Deferred capsule review SHALL verify the Code Review source controller with the pinned replacement public key before loading it. The independent capsule job SHALL install its historical review fixture and dependencies from Git base artifacts whose full archive hashes match the fixed CI inventory. The fixture registry SHALL be local to the isolated review job and shall not alter the release cutoff.

#### Scenario: Review a signature rotation with isolated controller trust

- **GIVEN** a candidate with a replacement signature on the Code Review source manifest
- **WHEN** the capsule jobs prepare their review controllers
- **THEN** deferred review requires the replacement-key signature over the source payload
- **AND** independent review rejects any historical fixture archive outside the exact CI inventory
- **AND** the independent reviewer obtains its runtime receipt from the ordinary installer

#### Scenario: Host fixtures exercise the current verification boundary

- **GIVEN** the deferred host fixture supplies the signed source controller and the independent bootstrap fixture supplies the pinned base archives
- **WHEN** the fixtures execute the hosted workflow steps
- **THEN** the real released verifier selected by the capsule workflow accepts the signed controller and rejects an invalid signature before preparation or review, including when the parent test environment uses paired editable core
- **AND** the independent bootstrap checks its pinned inputs while remaining isolated from the candidate's working directory

### Requirement: Separate public verification from replacement signing

CI SHALL verify module manifests without a private key or write access. PR approval events SHALL NOT sign or modify source manifests. The main-branch reproducibility check SHALL use the protected V2 key to reproduce checked-in replacement signatures and SHALL verify frozen bundles against their cutoff tree hashes.

#### Scenario: Verify a push without a signing secret

- **WHEN** a push targets `dev` or `main`
- **THEN** the public verification job checks payloads, signatures, and version rules without signing or writing back.

#### Scenario: Reproduce a signature after a protected main push

- **WHEN** verification succeeds for a protected `main` push
- **THEN** the reproducibility job requires the encrypted V2 key, its passphrase, and the pinned replacement fingerprint in the `module-signing` environment
- **AND** it checks stored signatures outside the cutoff against newly computed signatures over the same complete module payload
- **AND** it verifies exact frozen trees without re-signing them or modifying files.
