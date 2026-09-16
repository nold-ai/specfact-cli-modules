## ADDED Requirements

### Requirement: Validate the exact staged snapshot before running unchanged hooks
The transport SHALL bind an allowlisted regular-file patch to its SHA256, immutable base and resulting tree, and SHALL reject changes to hooks, workflows, dependencies or trust controls.

#### Scenario: Valid snapshot
- **GIVEN** a clean checkout and an allowlisted patch with matching base, digest and tree
- **WHEN** native hook transport prepares the snapshot
- **THEN** its staged tree equals the requested tree and the original hooks remain unchanged

#### Scenario: Untrusted or corrupt snapshot
- **GIVEN** a digest, base, tree, path, size or file-mode violation
- **WHEN** the transport validates the request
- **THEN** it fails before executing hooks

### Requirement: Preserve real execution authority and hook outcome
The transport SHALL execute every unchanged pre-commit stage in a credential-free child, retain real outer Actions identity and propagate nonzero exits or tracked source mutation. Its receipt SHALL identify local explicit-file evidence and SHALL NOT grant protected PR range or customer release authority.

#### Scenario: Failure and credentials
- **GIVEN** caller credentials and real Actions context
- **WHEN** a hook fails
- **THEN** the child receives only the explicit environment allowlist, the receipt retains actual outer identity and the failure is propagated

#### Scenario: Default workflow
- **GIVEN** an ordinary workflow invocation without the transport request
- **WHEN** the workflow selects jobs
- **THEN** the original customer corpus runs and the transport does not
