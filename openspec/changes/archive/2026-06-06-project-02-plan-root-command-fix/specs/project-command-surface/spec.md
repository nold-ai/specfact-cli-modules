## ADDED Requirements
### Requirement: Project bundle exposes plan command group
The `nold-ai/specfact-project` bundle SHALL declare both `project` and `plan` in its manifest command list so installed bundle routing can delegate `specfact plan ...` calls.

#### Scenario: Manifest includes plan command group
- **WHEN** a consumer inspects `packages/specfact-project/module-package.yaml`
- **THEN** the `commands` list contains `plan`
- **AND** docs for module command categories and marketplace bundle summary mention plan as part of the project bundle surface.
