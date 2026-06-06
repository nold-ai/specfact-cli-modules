## ADDED Requirements

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
