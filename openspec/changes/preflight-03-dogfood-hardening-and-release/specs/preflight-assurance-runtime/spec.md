## MODIFIED Requirements

### Requirement: Deterministic pre-implementation loop

The stable module SHALL execute the approved pre-implementation loop and SHALL retain regression evidence for every accepted dogfood defect that affected snapshotting, validation, review, refinement, approval, sealing, or verification.

#### Scenario: Hardened loop processes the C14 corpus

- **GIVEN** the exact accepted C14 dogfood corpus and a fresh supported environment
- **WHEN** the stable candidate executes the loop
- **THEN** all required validators complete with the expected findings and readiness states
- **AND** no previously accepted defect regresses.

### Requirement: Canonical skill and slash-command contract

The stable module SHALL publish the versioned canonical `specfact-preflight` workflow with tested CLI delegation and without external harness-specific packaging.

#### Scenario: Stable workflow asset is loaded

- **GIVEN** the signed module is installed through the official path
- **WHEN** a compatible generic installer discovers the workflow asset
- **THEN** it receives the canonical workflow identity and supported invocation contract
- **AND** adapter-specific files are not required to execute the underlying CLI.
