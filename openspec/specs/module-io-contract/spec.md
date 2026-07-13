# module-io-contract Specification

## Purpose
TBD - created by archiving change requirements-02-module-commands. Update Purpose after archive.
## Requirements
### Requirement: Module Io Contract

The requirements module SHALL consume core requirements context adapter helpers
through the existing `ModuleIOContract` boundary.

#### Scenario: Import operation maps backlog items to requirements

- **GIVEN** source-attributed requirement records imported by a module command
- **WHEN** the runtime stores normalized requirements on a `ProjectBundle`
- **THEN** requirements are added under the `requirements.inputs` extension with stable IDs
- **AND** parse diagnostics remain available to the module runtime for partial failures.

#### Scenario: Validate operation enforces profile schema

- **GIVEN** a requirements bundle and active validation profile
- **WHEN** the runtime delegates to core requirements context validation
- **THEN** missing evidence links and weak context are reported
- **AND** validation severity respects the selected evidence strictness profile.

