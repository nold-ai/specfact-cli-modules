## MODIFIED Requirements

### Requirement: Bundle overview pages SHALL provide complete bundle entry points
Each official bundle SHALL have a single overview page that lists its commands, prerequisites, examples, and relevant bundle-owned resource setup guidance.

#### Scenario: Overview page lists all bundle commands
- **GIVEN** a bundle overview page such as `bundles/backlog/overview.md`
- **WHEN** a user reads the page
- **THEN** every registered command and subcommand for that bundle is listed
- **AND** each command has a brief description

#### Scenario: Overview page includes quick examples
- **GIVEN** a bundle overview page
- **WHEN** a user reads the page
- **THEN** at least one practical example is shown for each major command group

#### Scenario: Overview page explains bundle-owned resource setup when relevant
- **GIVEN** a bundle overview page for a bundle that ships prompts or workspace templates
- **WHEN** a user reads the page
- **THEN** the page explains which resources are bundled with that package
- **AND** it points to the supported setup flow such as `specfact init ide` or bundle-specific template/bootstrap commands

#### Scenario: Command examples match actual CLI
- **GIVEN** a command example in an overview page
- **WHEN** compared against the actual `specfact <command> --help` output
- **THEN** the command name, arguments, and key options match
