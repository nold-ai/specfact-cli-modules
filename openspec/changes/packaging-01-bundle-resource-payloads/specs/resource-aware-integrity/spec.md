## ADDED Requirements

### Requirement: Bundle integrity SHALL cover resource payloads
Bundle signing, verification, and publish validation SHALL treat bundled resource files as part of the signed module payload so that resource-only changes are detected as bundle changes.

#### Scenario: Resource edit changes signed payload
- **WHEN** a prompt template or other bundled resource file changes inside a bundle package
- **THEN** integrity verification detects a payload change until the manifest version and signature are refreshed

#### Scenario: Resource-only change triggers version-bump enforcement
- **WHEN** a bundled resource file changes but the bundle manifest version is not incremented
- **THEN** the modules-repo version-bump enforcement reports that the bundle payload changed without a version bump

### Requirement: Bundle resource layout SHALL be discoverable by core CLI
Bundled resources SHALL live at stable paths inside the bundle package so that the core CLI can resolve them from an installed bundle root without hardcoded core-repo fallbacks.

#### Scenario: Core resolves prompt resources from installed bundle root
- **WHEN** the core CLI inspects an installed official bundle package
- **THEN** the bundle contains a stable prompt resource path that can be discovered without scanning the core CLI repository

#### Scenario: Core resolves backlog templates from installed bundle root
- **WHEN** the core CLI inspects an installed backlog bundle package
- **THEN** the bundle contains a stable template resource path for backlog field mapping templates
