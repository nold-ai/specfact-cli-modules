## MODIFIED Requirements

### Requirement: End-to-End `specfact code review run` in modules repo

The `specfact-code-review` bundle SHALL provide a fully wired `specfact code review run` command that orchestrates the existing tool runners, supports scoped file selection, emits governed review reports, and provides simplify-specific cleanup forecast and handoff controls.

#### Scenario: Run command previews simplify fixes without mutating files

- **WHEN** `specfact code review run --focus simplify --preview-fixes --json --out <path>` is executed
- **THEN** the command SHALL compute preview evidence for supported safe-mechanical simplification fixers
- **AND** it SHALL write the forecast evidence to the JSON report
- **AND** it SHALL NOT edit tracked source files

#### Scenario: Run command rejects preview and fix together

- **WHEN** `specfact code review run --focus simplify --preview-fixes --fix` is executed
- **THEN** the command SHALL fail before review execution with a clear invalid-combination error

#### Scenario: Run command scopes mutation proof to simplify focus

- **WHEN** `specfact code review run --with-mutation` is executed without `--focus simplify`
- **THEN** the command SHALL fail before review execution with a clear invalid-combination error

- **WHEN** `specfact code review run --focus simplify --with-mutation` is executed
- **THEN** the command SHALL run mutation proof only for candidate cleanup findings
- **AND** it SHALL record mutation outcomes in the report without making mutation proof part of the default review path
