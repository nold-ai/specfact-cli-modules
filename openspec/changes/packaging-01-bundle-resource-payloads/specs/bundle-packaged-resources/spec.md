## ADDED Requirements

### Requirement: Official bundles SHALL ship module-owned resource payloads
Each official bundle package SHALL include the prompt templates and other non-code resources that are owned by that bundle's workflows or commands. Bundle-owned resources SHALL not depend on fallback storage under the core CLI repository.

#### Scenario: Backlog bundle ships its prompt resources
- **WHEN** the backlog bundle package is inspected from source or from an installed artifact
- **THEN** the package contains the prompt templates owned by backlog workflows under the agreed bundle resource path

#### Scenario: Backlog bundle ships field mapping templates
- **WHEN** the backlog bundle package is inspected from source or from an installed artifact
- **THEN** the package contains the backlog field mapping templates that `specfact init` or related flows need to copy into workspace state

#### Scenario: Core no longer remains the source of truth for bundle prompts
- **WHEN** a workflow prompt belongs to an extracted bundle rather than to core lifecycle commands
- **THEN** that prompt's canonical packaged source exists in the owning bundle package
- **AND** release packaging does not rely on the core CLI repo as the canonical source for that prompt
