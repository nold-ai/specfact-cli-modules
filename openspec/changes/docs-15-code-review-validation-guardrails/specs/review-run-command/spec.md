## ADDED Requirements

### Requirement: Code Review run docs SHALL cover the public option surface

The Code Review run documentation SHALL describe every supported public `specfact code review run` option that affects targeting, output, exit behavior, analysis depth, or filtering.

#### Scenario: Newly added review options are documented

- **WHEN** the `specfact code review run` Typer command exposes `--bug-hunt`, `--mode`, `--focus`, and `--level`
- **THEN** the Code Review run guide documents those options in its key option table or equivalent option section
- **AND** docs validation fails if any of those public options are missing from the run guide

#### Scenario: Invalid option combinations are documented

- **WHEN** the command rejects combinations such as positional files with `--scope` or `--focus` with `--include-tests`
- **THEN** the Code Review docs describe the invalid combination behavior
- **AND** the docs include a user-facing alternative for the supported targeting style

### Requirement: Code Review docs SHALL stay aligned with review behavior

The Code Review docs SHALL describe current review run behavior for JSON output, shadow/enforce mode, progress output, focus filtering, severity filtering, bug-hunt budgets, and test inclusion semantics.

#### Scenario: Docs parity check detects missing behavior section

- **WHEN** the command implementation includes a public behavior that affects output, exit code, target selection, or analysis cost
- **THEN** docs parity validation checks that the behavior is represented in the Code Review run docs
- **AND** the validation fails when the behavior is absent from the docs
