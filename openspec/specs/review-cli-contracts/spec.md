# review-cli-contracts Specification

## Purpose
TBD - created by archiving change code-review-08-review-run-integration. Update Purpose after archive.
## Requirements
### Requirement: cli-val scenarios exist for review command groups
The modules repository SHALL define cli-val-compatible scenario YAML files for
the `specfact code review run`, `ledger`, and `rules` command groups, including
scope-mode and path-filter coverage for the review run command.

#### Scenario: review-run scenarios cover success, scope selection, and error paths
- **GIVEN** `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`
- **WHEN** it is validated
- **THEN** it includes success coverage, changed-only and full-review scope examples, subtree-filtered examples, and an error or anti-pattern scenario

#### Scenario: ledger scenarios cover update, status, and reset guardrails
- **GIVEN** `tests/cli-contracts/specfact-code-review-ledger.scenarios.yaml`
- **WHEN** it is validated
- **THEN** it includes `update`, `status`, and reset guardrail coverage

#### Scenario: rules scenarios cover init, show, and update
- **GIVEN** `tests/cli-contracts/specfact-code-review-rules.scenarios.yaml`
- **WHEN** it is validated
- **THEN** it includes the supported rules subcommands

### Requirement: Review CLI contracts cover clean-code output categories
The modules repository SHALL keep CLI review scenarios aligned with the expanded clean-code report surface.

#### Scenario: Review-run scenarios cover clean-code categories
- **GIVEN** `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`
- **WHEN** it is validated after this change
- **THEN** it includes at least one scenario that asserts clean-code categories in the governed review output
- **AND** it continues covering success, scope selection, and error paths

#### Scenario: PR-mode scenarios cover advisory checklist findings
- **GIVEN** review CLI scenarios include PR-mode execution
- **WHEN** the scenario output is validated
- **THEN** advisory checklist findings are represented without changing the base report schema
- **AND** unknown clean-code category names are rejected by the scenario contract layer

### Requirement: Review-run CLI scenarios cover enforcement mode, bug-hunt, focus facets, and severity level

The modules repository SHALL extend `tests/cli-contracts/specfact-code-review-run.scenarios.yaml` so contract tests exercise the new `specfact code review run` flags together with existing scope and JSON output behaviour.

#### Scenario: Scenarios cover shadow versus enforce exit behaviour

- **GIVEN** `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`
- **WHEN** it is validated after this change
- **THEN** it includes at least one scenario asserting `--mode shadow` yields process success (exit `0`) while JSON still reports a failing verdict when findings warrant it
- **AND** it includes a control scenario showing `--mode enforce` (or default) preserves non-zero exit on blocking failures

#### Scenario: Scenarios cover --bug-hunt in shadow and enforce modes

- **GIVEN** `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`
- **WHEN** it is validated after this change
- **THEN** it includes at least one scenario with `--bug-hunt --mode shadow`
- **AND** it includes at least one scenario with `--bug-hunt --mode enforce`

#### Scenario: Scenarios cover --focus facets

- **GIVEN** the same scenario file
- **WHEN** it is validated
- **THEN** it includes coverage for `--focus` union behaviour (e.g. `source` + `docs`) and for `--focus tests` narrowing the file set
- **AND** it includes coverage for `--bug-hunt` composed with `--focus`

#### Scenario: Scenarios cover --level filtering

- **GIVEN** the same scenario file
- **WHEN** it is validated
- **THEN** it includes at least one scenario where `--level error` removes warnings from the JSON `findings` list
- **AND** it includes coverage for `--bug-hunt` composed with `--level error`

#### Scenario: Scenarios cover invalid flag combinations

- **GIVEN** the same scenario file
- **WHEN** it is validated
- **THEN** it includes an error-path scenario for `--focus` combined with `--include-tests` or `--exclude-tests`
- **AND** `--bug-hunt` remains composable with test-selection flags

