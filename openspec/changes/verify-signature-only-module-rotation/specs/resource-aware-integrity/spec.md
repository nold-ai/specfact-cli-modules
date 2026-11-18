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

### Requirement: Authenticate capsule source controllers with the replacement key

Deferred capsule review SHALL verify the Code Review source controller with the pinned replacement public key before loading it. The independent job SHALL execute the controller from its immutable PR base with a verified signature. If the base still carries the retired signature, the job SHALL accept only a replacement signature over identical package and manifest bytes.

#### Scenario: Review a signature rotation with isolated controller trust

- **GIVEN** a candidate whose only package change is a replacement signature on the Code Review manifest
- **WHEN** the candidate and independent capsule jobs prepare their review controllers
- **THEN** both verify the Code Review payload with the pinned replacement key
- **AND** the independent job imports its controller from the base tree outside the candidate subject
- **AND** unsigned or incorrectly signed controllers fail before review
