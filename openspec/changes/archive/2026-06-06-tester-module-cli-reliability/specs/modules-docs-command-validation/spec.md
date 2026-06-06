## ADDED Requirements

### Requirement: Module docs command examples are validated

Module documentation command examples SHALL be validated against the generated module command overview.

#### Scenario: Legacy flat sync command fails validation

- **GIVEN** module docs, help examples, prompts, Jinja2 templates, YAML/JSON resources, or text guidance contain `specfact sync bridge`
- **WHEN** docs command validation runs
- **THEN** validation fails unless the reference is explicitly marked as historical migration material
- **AND** the finding identifies `specfact project sync bridge` as the canonical command when appropriate.

#### Scenario: Prompt validators do not whitelist removed flat mounts

- **GIVEN** a validator scans module prompt resources
- **WHEN** it builds the command contract
- **THEN** it uses generated module command overview data
- **AND** it does not accept removed flat mounts such as `specfact import`, `specfact sync`, `specfact plan`, or `specfact migrate` as canonical command groups.

#### Scenario: Invalid option ordering fails validation

- **GIVEN** docs or prompts contain `specfact code import <bundle> --repo .`
- **WHEN** validation runs
- **THEN** the validator rejects the example if the command contract does not support that order
- **AND** the finding includes the canonical supported command form.
