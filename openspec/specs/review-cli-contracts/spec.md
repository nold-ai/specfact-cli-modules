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

