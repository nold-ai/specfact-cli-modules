# backlog-delta Specification

## Purpose
TBD - created by archiving change backlog-02-migrate-core-commands. Update Purpose after archive.
## Requirements
### Requirement: Restore backlog delta subcommands

The system SHALL provide `specfact backlog delta` with subcommands for backlog change analysis.

#### Scenario: Delta status shows backlog changes
- **WHEN** the user runs `specfact backlog delta status --project-id <id>`
- **THEN** current backlog state is compared to baseline
- **AND** added/updated/deleted items are listed

#### Scenario: Delta impact analyzes item effects
- **WHEN** the user runs `specfact backlog delta impact <item-id>`
- **THEN** dependent items and cascade effects are identified

#### Scenario: Delta cost-estimate calculates effort
- **WHEN** the user runs `specfact backlog delta cost-estimate`
- **THEN** story points and business value deltas are aggregated

#### Scenario: Delta rollback-analysis shows revert options
- **WHEN** the user runs `specfact backlog delta rollback-analysis`
- **THEN** safe rollback paths and risks are presented

### Requirement: Backlog delta status resolves documented defaults

`backlog delta status` SHALL resolve project and repository inputs consistently with other backlog commands where configuration defaults are available.

#### Scenario: Delta status uses configured GitHub repository defaults

- **GIVEN** `.specfact/backlog-config.yaml` contains a default GitHub repository owner and name
- **WHEN** the user runs `specfact backlog delta status github`
- **THEN** the command resolves the repository owner and name from configuration
- **AND** it does not require undocumented repo parameters.

#### Scenario: Delta status exposes missing repository inputs

- **GIVEN** required repository inputs are not present in CLI arguments or configuration
- **WHEN** the user runs `specfact backlog delta status`
- **THEN** the command help and error output names the missing kebab-case options
- **AND** the command does not emit raw internal names such as `repo_owner` or `repo_name`.

