## ADDED Requirements

### Requirement: Module Commands Follow Shared CLI Error Contract

Module command groups and leaf commands SHALL render actionable help for missing subcommands and missing required parameters.

#### Scenario: Backlog auth without subcommand shows help and missing-subcommand guidance

- **GIVEN** the user invokes `specfact backlog auth`
- **WHEN** no auth subcommand is provided
- **THEN** the output includes `backlog auth` help
- **AND** it states that a subcommand is required
- **AND** it lists provider/status/clear subcommands
- **AND** the command exits with a usage-error status.

#### Scenario: Backlog delta status names missing required inputs

- **GIVEN** the user invokes `specfact backlog delta status` without resolvable project or repository inputs
- **WHEN** required inputs cannot be resolved from CLI arguments or configuration
- **THEN** the output includes command help
- **AND** it names the missing CLI options using kebab-case option names
- **AND** it does not emit undocumented snake_case parameter names.

#### Scenario: Code import legacy option ordering is actionable

- **GIVEN** the user invokes `specfact code import <bundle> --repo .`
- **WHEN** that ordering is not accepted by the command contract
- **THEN** the output includes help or migration guidance
- **AND** it shows the canonical supported invocation
- **AND** it does not report only `No such command '--repo'`.

#### Scenario: Project regenerate null bundle data is typed

- **GIVEN** project bundle processing encounters missing or null bundle data
- **WHEN** `specfact project regenerate` runs
- **THEN** the command reports a typed validation or bundle-data diagnostic
- **AND** it does not crash with a raw `NoneType` attribute error.
