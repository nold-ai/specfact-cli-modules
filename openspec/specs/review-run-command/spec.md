# review-run-command Specification

## Purpose
This specification defines the public `specfact code review run` contract for
the modules repository: target selection, orchestration, governed JSON reports,
exit behavior, cleanup forecast controls, and documentation parity.

## Requirements
### Requirement: End-to-End `specfact code review run` in modules repo

The `specfact-code-review` bundle SHALL provide a fully wired `specfact code review run` command that orchestrates the existing tool runners, supports scoped file selection, emits governed review reports, and provides simplify-specific cleanup forecast and handoff controls.

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

- **GIVEN** a review run includes test files or other paths that can emit known low-signal findings
- **WHEN** noise suppression is enabled
- **THEN** the report omits those known low-signal findings
- **AND** a command option allows users to include the suppressed findings for a strict/full review

#### Scenario: Bundled skill instructs whether to include tests

- **GIVEN** the bundled `specfact-code-review` skill is installed
- **WHEN** it guides a review workflow
- **THEN** it instructs the reviewer to decide whether tests should be included before running the review

#### Scenario: Long-running review runs surface progress

- **GIVEN** a review run executes multiple tool steps that can take noticeable time
- **WHEN** the command is running
- **THEN** the CLI shows which review step is currently executing
- **AND** progress feedback does not replace the primary stdout contract such as the final JSON output path

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

### Requirement: Developer runtime validation helper for local modules

The modules repository SHALL provide a repo-local helper that prepares a live
module source tree for workspace runtime validation through `.specfact/modules`
without mutating the source package manifest.

#### Scenario: Helper creates shadow module with unsigned manifest copy
- **GIVEN** a local module source under `packages/<module>`
- **WHEN** the helper prepares a workspace shadow root
- **THEN** the shadow module directory contains symlinks to the live module content
- **AND** the shadow manifest omits integrity metadata so runtime validation can opt into unsigned local loading

### Requirement: Review run command orchestrates clean-code analysis
The bundle SHALL run the expanded clean-code analysis set as part of the governed review workflow.

#### Scenario: Review run includes clean-code categories in normal output
- **GIVEN** `specfact code review run --json <file>` executes with clean-code analysis enabled
- **WHEN** the run completes
- **THEN** the JSON report may contain findings in `naming`, `kiss`, `yagni`, `dry`, and `solid`
- **AND** the command keeps the same report envelope used by earlier runner changes

#### Scenario: PR mode runs checklist enforcement as advisory analysis
- **GIVEN** review run executes in PR mode
- **WHEN** checklist enforcement finds missing clean-code reasoning in the proposal or PR context
- **THEN** the report includes an advisory checklist finding
- **AND** the checklist finding does not create a new command surface

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

### Requirement: --mode shadow and --mode enforce

The `specfact code review run` command SHALL accept `--mode shadow` or `--mode enforce`.

#### Scenario: Default mode is enforce

- **GIVEN** `specfact code review run` is invoked without `--mode`
- **WHEN** the command parses its arguments
- **THEN** enforcement behaves as today: `ci_exit_code` reflects blocking findings

#### Scenario: Shadow mode never returns a failing process exit

- **GIVEN** a review run that would yield `ci_exit_code == 1` under enforce semantics
- **WHEN** `specfact code review run --mode shadow` completes
- **THEN** the process exit code is `0`
- **AND** `ReviewReport.ci_exit_code` in JSON is `0`
- **AND** `overall_verdict` still reflects the computed verdict (including `FAIL` when applicable)

#### Scenario: Enforce mode matches legacy exit behaviour

- **GIVEN** the same findings payload as today for a failing run
- **WHEN** `specfact code review run --mode enforce` completes
- **THEN** process exit and `ci_exit_code` match the pre-change `enforce` default

#### Scenario: --mode composes with --bug-hunt and --json

- **WHEN** `specfact code review run --bug-hunt --mode shadow --json --out report.json` is executed
- **THEN** the command parses successfully
- **AND** CrossHair uses bug-hunt timeouts
- **AND** the process exits `0` even if findings would fail under enforce semantics

### Requirement: Repeatable --focus for source, tests, and docs

The command SHALL accept repeated `--focus` options with values `source`, `tests`, and `docs`. When at least one `--focus` is present, the reviewed Python file set SHALL be the intersection of the scope-resolved files with the **union** of the selected facets:

- `tests`: files where `tests` appears in the path’s directory components (same rule as existing test detection).
- `docs`: Python files where `docs` appears in the path’s directory components.
- `source`: Python files that match neither the `tests` nor the `docs` facet.

#### Scenario: --focus tests restricts to test paths

- **GIVEN** a repository with both `src/app.py` and `tests/test_app.py` in scope
- **WHEN** `specfact code review run --scope full --focus tests --json` runs
- **THEN** only files under the `tests` facet are analyzed

#### Scenario: Union of multiple focuses

- **GIVEN** scope includes `src/a.py`, `tests/t.py`, and `docs/conf.py`
- **WHEN** `specfact code review run --scope full --focus source --focus docs --json` runs
- **THEN** `tests/t.py` is excluded
- **AND** `src/a.py` and `docs/conf.py` are included

#### Scenario: --focus conflicts with --include-tests

- **WHEN** `specfact code review run --focus source --include-tests` is parsed
- **THEN** the CLI rejects the combination with a clear error

#### Scenario: --focus conflicts with --exclude-tests

- **WHEN** `specfact code review run --focus tests --exclude-tests` is parsed
- **THEN** the CLI rejects the combination with a clear error

### Requirement: --level error and --level warning

The command SHALL accept `--level error` or `--level warning` to filter findings **before** scoring and verdict.

#### Scenario: --level error drops warnings and info

- **GIVEN** a run that produces both `warning` and `error` severity findings
- **WHEN** `specfact code review run --level error --json` completes
- **THEN** the JSON `findings` list contains only `severity == "error"` items
- **AND** score and verdict are computed from that filtered list

#### Scenario: --level warning retains errors and warnings

- **GIVEN** a run that produces `info`, `warning`, and `error` findings
- **WHEN** `specfact code review run --level warning --json` completes
- **THEN** the JSON `findings` list contains no `severity == "info"` items
- **AND** score and verdict are computed from the filtered list

#### Scenario: Omitted --level keeps all severities

- **WHEN** `specfact code review run --json` runs without `--level`
- **THEN** all severities appear in output as they do today

### Requirement: Code Review run docs SHALL cover the public option surface

The Code Review run documentation SHALL describe every supported public `specfact code review run` option that affects targeting, output, exit behavior, analysis depth, or filtering.

#### Scenario: Newly added review options are documented

- **WHEN** the `specfact code review run` Typer command exposes `--bug-hunt`, `--mode`, `--focus`, and `--level`
- **THEN** the Code Review run guide documents those options in its key option table or equivalent option section
- **AND** docs validation fails if any of those public options are missing from the run guide

#### Scenario: Invalid option combinations are documented

- **WHEN** the command rejects combinations such as positional files with `--scope` or `--path`, or `--focus` with `--include-tests`
- **THEN** the Code Review docs describe the invalid combination behavior
- **AND** the docs include a user-facing alternative for the supported targeting style: pass explicit positional file paths for a fixed review set, or use **`--scope`** / **`--path`** without positional files to auto-discover targets from the repo

### Requirement: Code Review docs SHALL stay aligned with review behavior

The Code Review docs SHALL describe current review run behavior for JSON output, shadow/enforce mode, progress output, focus filtering, severity filtering, bug-hunt budgets, and test inclusion semantics.

#### Scenario: Docs parity check detects missing behavior section

- **WHEN** the command implementation includes a public behavior that affects output, exit code, target selection, or analysis cost
- **THEN** docs parity validation checks that the behavior is represented in the Code Review run docs
- **AND** the validation fails when the behavior is absent from the docs

### Requirement: Review run supports simplify focus

The `specfact code review run` command SHALL accept `--focus simplify` as a targeted review focus for simplification feedback. The focus SHALL retain findings that belong in the simplification queue and SHALL classify them with actionable guidance.

#### Scenario: Simplify focus emits guided simplification queue

- **WHEN** `specfact code review run --focus simplify --json --out .specfact/code-review.json` completes
- **THEN** the JSON report SHALL retain simplification-focused findings
- **AND** retained findings SHALL include guidance metadata for actionability, preservation, or design judgment
- **AND** the report SHALL include a simplification summary when guided findings are present

#### Scenario: Simplify enforce blocks only safe mechanical debt

- **WHEN** `specfact code review run --focus simplify --mode enforce` runs
- **THEN** the process SHALL fail only when unresolved findings with `guidance_kind="safe_mechanical"` remain
- **AND** findings classified as `needs_tests`, `design_judgment`, or `preserve` SHALL NOT make the run fail

#### Scenario: Simplify fix applies only safe mechanical rewrites

- **WHEN** `specfact code review run --focus simplify --fix` runs
- **THEN** automatic rewrites SHALL be limited to deterministic safe-mechanical findings
- **AND** the command SHALL rerun review after applying rewrites
- **AND** the JSON report SHALL record applied, failed, and still-recommended outcomes
