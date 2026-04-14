## ADDED Requirements

### Requirement: Review-run CLI scenarios cover enforcement mode, focus facets, and severity level

The modules repository SHALL extend `tests/cli-contracts/specfact-code-review-run.scenarios.yaml` so contract tests exercise the new `specfact code review run` flags together with existing scope and JSON output behaviour.

#### Scenario: Scenarios cover shadow versus enforce exit behaviour

- **GIVEN** `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`
- **WHEN** it is validated after this change
- **THEN** it includes at least one scenario asserting `--mode shadow` yields process success (exit `0`) while JSON still reports a failing verdict when findings warrant it
- **AND** it includes a control scenario showing `--mode enforce` (or default) preserves non-zero exit on blocking failures

#### Scenario: Scenarios cover --focus facets

- **GIVEN** the same scenario file
- **WHEN** it is validated
- **THEN** it includes coverage for `--focus` union behaviour (e.g. `source` + `docs`) and for `--focus tests` narrowing the file set

#### Scenario: Scenarios cover --level filtering

- **GIVEN** the same scenario file
- **WHEN** it is validated
- **THEN** it includes at least one scenario where `--level error` removes warnings from the JSON `findings` list

#### Scenario: Scenarios cover invalid flag combinations

- **GIVEN** the same scenario file
- **WHEN** it is validated
- **THEN** it includes an error-path scenario for `--focus` combined with `--include-tests` or `--exclude-tests`
