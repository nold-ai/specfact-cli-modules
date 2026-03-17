# review-run-command Specification

## Purpose
TBD - created by archiving change code-review-08-review-run-integration. Update Purpose after archive.
## Requirements
### Requirement: End-to-End `specfact code review run` in modules repo

The `specfact-code-review` bundle SHALL provide a fully wired
`specfact code review run` command that orchestrates the existing tool runners
and emits a governed `ReviewReport` with correct exit codes.

#### Scenario: Representative modules-repo source can be reviewed without command failure
- **GIVEN** a real Python source file from this repository
- **WHEN** `specfact code review run --json <file>` is executed in the modules repo
- **THEN** the command writes a `ReviewReport` JSON file
- **AND** the command does not fail because of command wiring, path handling, or tool invocation bugs in the bundle

#### Scenario: JSON output uses file-based routing
- **GIVEN** `specfact code review run --json`
- **WHEN** the command executes successfully
- **THEN** it writes the governed `ReviewReport` JSON payload to a file path
- **AND** `--out` overrides the default JSON output path

#### Scenario: Interactive runs ask whether to include test files
- **GIVEN** `specfact code review run` executes in interactive mode
- **WHEN** test-file inclusion has not been specified explicitly
- **THEN** the CLI asks whether test files should be included in the review scope
- **AND** the answer controls whether changed files under `tests/` are reviewed

#### Scenario: Auto-detected review scope includes untracked Python files
- **GIVEN** Python files exist in the workspace that are not yet tracked by Git
- **WHEN** `specfact code review run` auto-detects review scope
- **THEN** those untracked Python files are included in review scope
- **AND** test-file inclusion rules still apply to untracked files under `tests/`

#### Scenario: Known low-signal findings are suppressible by default
- **GIVEN** a review run includes test files or other paths that can emit
  known low-signal findings
- **WHEN** noise suppression is enabled
- **THEN** the report omits those known low-signal findings
- **AND** a command option allows users to include the suppressed findings for a
  strict/full review

#### Scenario: Bundled skill instructs whether to include tests
- **GIVEN** the bundled `specfact-code-review` skill is installed
- **WHEN** it guides a review workflow
- **THEN** it instructs the reviewer to decide whether tests should be included
  before running the review

#### Scenario: Long-running review runs surface progress
- **GIVEN** a review run executes multiple tool steps that can take noticeable
  time
- **WHEN** the command is running
- **THEN** the CLI shows which review step is currently executing
- **AND** progress feedback does not replace the primary stdout contract such as
  the final JSON output path

### Requirement: Developer runtime validation helper for local modules

The modules repository SHALL provide a repo-local helper that prepares a live
module source tree for workspace runtime validation through `.specfact/modules`
without mutating the source package manifest.

#### Scenario: Helper creates shadow module with unsigned manifest copy
- **GIVEN** a local module source under `packages/<module>`
- **WHEN** the helper prepares a workspace shadow root
- **THEN** the shadow module directory contains symlinks to the live module content
- **AND** the shadow manifest omits integrity metadata so runtime validation can opt into unsigned local loading

