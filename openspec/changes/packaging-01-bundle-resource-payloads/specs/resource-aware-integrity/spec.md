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

#### Scenario: Installed backlog bundle contributes prompt source catalog entries
- **WHEN** `nold-ai/specfact-backlog` is installed under an effective module root with the packaged backlog prompt files
- **THEN** core prompt-source discovery includes `nold-ai/specfact-backlog` as a prompt source
- **AND** `specfact init ide` can export the backlog prompt filenames from that installed module root

#### Scenario: Core resolves prompt companion resources with exported prompts
- **WHEN** the core CLI exports a prompt that depends on a companion file such as `shared/cli-enforcement.md`
- **THEN** the companion resource is discoverable from the same installed bundle root
- **AND** the exported prompt does not contain a broken relative reference after copy

#### Scenario: Core resolves backlog workspace-template seeds from installed bundle root
- **WHEN** the core CLI inspects an installed backlog bundle package
- **THEN** the bundle contains a stable template resource path for backlog field mapping templates
- **AND** that path exposes every seed template the init/install flows are expected to copy
