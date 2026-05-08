## MODIFIED Requirements

### Requirement: Bundle integrity SHALL cover resource payloads

Bundle signing, verification, and publish validation SHALL treat bundled resource files as part of the signed module payload so that resource-only changes are detected as bundle changes. Prompt resource edits SHALL also be covered by prompt command validation before release.

#### Scenario: Resource edit changes signed payload

- **WHEN** a prompt template or other bundled resource file changes inside a bundle package
- **THEN** integrity verification detects a payload change until the manifest version and signature are refreshed

#### Scenario: Resource-only change triggers version-bump enforcement

- **WHEN** a bundled resource file changes but the bundle manifest version is not incremented
- **THEN** the modules-repo version-bump enforcement reports that the bundle payload changed without a version bump

#### Scenario: Prompt resource edit triggers command-contract validation

- **WHEN** a bundled prompt resource changes
- **THEN** the local and CI validation gates run prompt command validation
- **AND** stale command paths or options are reported before the changed resource can ship
