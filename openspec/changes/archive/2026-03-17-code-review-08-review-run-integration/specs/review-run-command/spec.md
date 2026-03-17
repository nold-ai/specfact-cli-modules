## ADDED Requirements

### Requirement: End-to-End `specfact code review run` in modules repo
The `specfact-code-review` bundle SHALL provide a fully wired
`specfact code review run` command that orchestrates the existing tool runners
and emits a governed `ReviewReport` with correct exit codes.

#### Scenario: Clean review fixture returns PASS
- **GIVEN** `tests/fixtures/review/clean_module.py` and its matching tests
- **WHEN** `specfact code review run tests/fixtures/review/clean_module.py` is executed
- **THEN** the report verdict is `PASS` and the process exits `0`

#### Scenario: Dirty review fixture returns FAIL
- **GIVEN** `tests/fixtures/review/dirty_module.py` with blocking findings
- **WHEN** `specfact code review run tests/fixtures/review/dirty_module.py` is executed
- **THEN** the report verdict is `FAIL` and the process exits `1`

#### Scenario: JSON output emits a valid ReviewReport
- **GIVEN** a review run over one or more files
- **WHEN** `specfact code review run --json` is executed
- **THEN** stdout parses as `ReviewReport`

#### Scenario: Score-only output emits only reward delta
- **GIVEN** a review run over one or more files
- **WHEN** `specfact code review run --score-only` is executed
- **THEN** stdout contains only the integer reward delta and a trailing newline

#### Scenario: Missing files fall back to git diff HEAD
- **GIVEN** no file arguments are provided
- **WHEN** `specfact code review run` is executed
- **THEN** the command reviews files from `git diff HEAD --name-only`
