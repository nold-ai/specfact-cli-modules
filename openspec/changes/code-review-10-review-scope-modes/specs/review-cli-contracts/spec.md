## MODIFIED Requirements

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
