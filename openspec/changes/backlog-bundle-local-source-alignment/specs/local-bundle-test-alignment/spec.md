## ADDED Requirements

### Requirement: Pytest Bootstrap Must Prefer Local Bundle Sources

The modules-repo pytest bootstrap SHALL prefer bundle imports from the checked-out workspace over installed user-home bundle copies.

#### Scenario: User-home path is present before local import
- **WHEN** a user-home bundle source path under `~/.specfact/modules` is present on `sys.path`
- **THEN** pytest bootstrap removes that external path from precedence for bundle package imports
- **AND** backlog bundle imports resolve from the workspace package source under `packages/specfact-backlog/src`.

### Requirement: Pytest Bootstrap Must Recover From Shadowed Bundle Modules

The modules-repo pytest bootstrap SHALL purge bundle modules already imported from user-home module roots so later imports rebind to the workspace sources.

#### Scenario: Shadowed backlog module is already imported
- **WHEN** `specfact_backlog` or its submodules were imported from `~/.specfact/modules`
- **THEN** pytest bootstrap removes those shadowed modules from `sys.modules`
- **AND** subsequent imports resolve from the workspace source tree.
