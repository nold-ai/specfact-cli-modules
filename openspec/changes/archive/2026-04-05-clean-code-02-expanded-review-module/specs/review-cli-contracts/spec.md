## ADDED Requirements

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
