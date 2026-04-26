## ADDED Requirements

### Requirement: Bundle runtime commands SHALL distinguish sanctioned external artifacts from SpecFact-managed artifacts
Bundle runtime commands SHALL treat files outside `.specfact` as user-owned by default and SHALL treat files inside `.specfact` as SpecFact-managed unless a command explicitly documents a narrower ownership split.

#### Scenario: Runtime command targets a sanctioned external user-owned artifact
- **WHEN** a bundle runtime command mutates a sanctioned path outside `.specfact`
- **THEN** it SHALL reuse the paired core safe-write contract
- **AND** SHALL NOT silently overwrite the existing user-owned file

#### Scenario: Runtime command targets a fully owned SpecFact artifact
- **WHEN** a bundle runtime command updates a fully owned artifact under `.specfact`
- **THEN** it MAY rewrite that artifact deterministically according to the command's managed-state contract
- **AND** it SHALL NOT treat the file as a user-owned external artifact by default

### Requirement: Partially user-tuned `.specfact` config SHALL preserve unrelated content
Bundle commands that update partially owned config files under `.specfact` SHALL preserve unrelated user-managed keys or sections during supported updates.

#### Scenario: Supported config merge preserves unrelated provider settings
- **WHEN** a regression fixture contains an existing `.specfact` config file with additional user-managed settings
- **AND** a bundle command updates only a declared SpecFact-managed subtree
- **THEN** unrelated keys or sections SHALL remain intact
- **AND** only the managed subtree SHALL change

#### Scenario: Unsupported config shape fails safe
- **WHEN** a bundle command encounters an existing `.specfact` config shape that it cannot reconcile safely
- **THEN** the command SHALL fail with actionable guidance
- **AND** SHALL leave the existing file unchanged by default
