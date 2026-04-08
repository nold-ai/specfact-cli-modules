## ADDED Requirements

### Requirement: --bug-hunt flag on review run command

The `specfact code review run` command SHALL accept a `--bug-hunt` flag that
enables extended CrossHair timeouts and is composable with all existing flags.

#### Scenario: --bug-hunt flag accepted without error

- **GIVEN** `specfact code review run --bug-hunt --json <file>` is executed
- **WHEN** the command parses its arguments
- **THEN** the command proceeds without a CLI argument error
- **AND** `ReviewRunRequest.bug_hunt` is `True`

#### Scenario: --bug-hunt flag absent defaults to False

- **GIVEN** `specfact code review run --json <file>` is executed without `--bug-hunt`
- **WHEN** the command parses its arguments
- **THEN** `ReviewRunRequest.bug_hunt` is `False`
- **AND** CrossHair uses the standard 2-second per-path timeout
