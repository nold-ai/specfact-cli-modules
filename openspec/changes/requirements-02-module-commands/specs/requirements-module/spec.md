## ADDED Requirements

### Requirement: Requirements Runtime Commands

The system SHALL provide module-owned `specfact requirements ...` commands for
importing, validating, listing, and inspecting upstream requirement context as
validation evidence.

#### Scenario: Import local requirement records into bundle extensions

- **GIVEN** a local JSON or YAML file containing source-attributed requirement records
- **WHEN** `specfact requirements import --from-file <path> --bundle <bundle>` runs
- **THEN** valid records are stored under the bundle's `requirements.inputs` extension
- **AND** invalid records are returned as bounded diagnostics.

#### Scenario: Validate requirement context by profile

- **GIVEN** a project bundle with normalized requirement inputs
- **WHEN** `specfact requirements validate --bundle <bundle> --profile enterprise` runs
- **THEN** validation delegates to the core profile-aware requirements context helper
- **AND** missing downstream evidence links are reported as failed validation.

#### Scenario: List requirements with coverage summary

- **GIVEN** requirement inputs are present on a project bundle
- **WHEN** `specfact requirements list --bundle <bundle> --show-coverage --format json` runs
- **THEN** each requirement ID and title is returned
- **AND** the output includes a machine-readable coverage summary.

#### Scenario: No authoring command is exposed

- **GIVEN** the requirements module is installed
- **WHEN** the user inspects `specfact requirements --help`
- **THEN** import, validate, list, and coverage commands are visible
- **AND** requirement authoring commands are not exposed.
