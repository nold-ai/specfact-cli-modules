## MODIFIED Requirements

### Requirement: End-to-End `specfact code review run` in modules repo
The `specfact-code-review` bundle SHALL provide a fully wired
`specfact code review run` command that orchestrates the existing tool runners,
supports explicit `changed` and `full` auto-discovery modes plus repo-relative
path filtering, and emits a governed `ReviewReport` with correct exit codes.

#### Scenario: Clean review fixture returns PASS
- **GIVEN** `tests/fixtures/review/clean_module.py` and its matching tests
- **WHEN** `specfact code review run tests/fixtures/review/clean_module.py` is executed
- **THEN** the report verdict is `PASS` and the process exits `0`

#### Scenario: Dirty review fixture returns FAIL
- **GIVEN** `tests/fixtures/review/dirty_module.py` with blocking findings
- **WHEN** `specfact code review run tests/fixtures/review/dirty_module.py` is executed
- **THEN** the report verdict is `FAIL` and the process exits `1`

#### Scenario: JSON output writes a valid ReviewReport to a file
- **GIVEN** a review run over one or more files
- **WHEN** `specfact code review run --json` is executed
- **THEN** the command writes a valid `ReviewReport` JSON payload to the selected output path
- **AND** stdout reports that output path instead of printing the full JSON payload

#### Scenario: Score-only output emits only reward delta
- **GIVEN** a review run over one or more files
- **WHEN** `specfact code review run --score-only` is executed
- **THEN** stdout contains only the integer reward delta and a trailing newline

#### Scenario: Default auto-discovery reviews changed files
- **GIVEN** no positional file arguments and no explicit `--scope`
- **WHEN** `specfact code review run` is executed
- **THEN** the command reviews files from the changed-file set for the current repo

#### Scenario: Full scope reviews the governed repository file set
- **GIVEN** no positional file arguments
- **WHEN** `specfact code review run --scope full` is executed
- **THEN** the command reviews the governed repository Python file set instead of only changed files
- **AND** test files remain excluded by default unless users opt in with `--include-tests` or explicitly target test subtrees with `--path tests/...`

#### Scenario: Full scope can be limited to a package subtree
- **GIVEN** no positional file arguments
- **WHEN** `specfact code review run --scope full --path packages/specfact-code-review` is executed
- **THEN** only reviewable files under that package path and its subfolders are included

#### Scenario: Changed scope can be limited to test and source subtrees
- **GIVEN** changed files exist in multiple repository areas
- **WHEN** `specfact code review run --scope changed --path packages/specfact-code-review --path tests/unit/specfact_code_review` is executed
- **THEN** only changed files under those repo-relative prefixes are reviewed

#### Scenario: Empty filtered scope fails fast
- **GIVEN** the selected scope and path filters match no reviewable files
- **WHEN** `specfact code review run` is executed
- **THEN** the command exits non-zero with an actionable empty-scope message

#### Scenario: Positional files cannot be mixed with auto-scope controls
- **GIVEN** one or more positional file arguments
- **WHEN** `specfact code review run src/example.py --scope full --path src` is executed
- **THEN** the command rejects the invocation and instructs the user to choose positional files or auto-scope controls
