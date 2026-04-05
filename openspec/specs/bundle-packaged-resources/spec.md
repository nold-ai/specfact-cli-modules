# bundle-packaged-resources Specification

## Purpose
TBD - created by archiving change packaging-01-bundle-resource-payloads. Update Purpose after archive.
## Requirements
### Requirement: Official bundles SHALL ship module-owned resource payloads
Each official bundle package SHALL include the prompt templates and other non-code resources that are owned by that bundle's workflows or commands. Bundle-owned resources SHALL not depend on fallback storage under the core CLI repository.

#### Scenario: Official bundles ship the audited prompt inventory
- **WHEN** the audited prompt inventory from `RESOURCE_OWNERSHIP_AUDIT.md` is inspected
- **THEN** each prompt template's canonical packaged source exists under the owning official bundle package
- **AND** the ownership mapping covers the codebase, project, spec, govern, and backlog bundles for the currently supported prompt set

#### Scenario: Backlog bundle ships the restored slash-prompt inventory
- **WHEN** the backlog bundle package is inspected from source or from an installed artifact
- **THEN** `resources/prompts/` contains `specfact.backlog-add.md`, `specfact.backlog-daily.md`, `specfact.backlog-refine.md`, and `specfact.sync-backlog.md`
- **AND** those prompt files are treated as canonical bundle-owned sources rather than historical leftovers

#### Scenario: Prompt companion resources ship with prompt payloads
- **WHEN** an exported prompt template references a companion file by relative path, such as `./shared/cli-enforcement.md`
- **THEN** the owning bundle package contains that companion resource in a stable relative location
- **AND** prompt export/copy flows can preserve a resolvable relative layout in the target IDE workspace

#### Scenario: Backlog bundle ships workspace-template seed resources
- **WHEN** the backlog bundle package is inspected from source or from an installed artifact
- **THEN** the package contains the backlog field mapping templates that `specfact init` or related flows need to copy into workspace state
- **AND** the packaged set includes both ADO and non-ADO seed templates required by supported backlog flows

#### Scenario: Core no longer remains the source of truth for bundle prompts
- **WHEN** a workflow prompt belongs to an extracted bundle rather than to core lifecycle commands
- **THEN** that prompt's canonical packaged source exists in the owning bundle package
- **AND** release packaging does not rely on the core CLI repo as the canonical source for that prompt

