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
