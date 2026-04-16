# Modules pre-commit quality parity

## MODIFIED Requirements

### Requirement: Docs-only pre-commit changes SHALL run docs validation before safe bypass

The modules repo pre-commit helper SHALL run deterministic docs validation for staged docs-only changes before skipping code-specific review and contract-test stages.

#### Scenario: Docs-only commit with broken link fails pre-commit

- **WHEN** only docs files are staged and one staged docs page introduces a broken published-route link
- **THEN** pre-commit runs docs validation
- **AND** pre-commit fails before reporting the change as safe

#### Scenario: Docs-only commit with valid docs skips code-specific checks

- **WHEN** only docs files are staged and docs validation passes
- **THEN** pre-commit may skip code review and contract-test stages
- **AND** pre-commit reports that docs validation passed before applying the safe-change bypass

### Requirement: Pre-commit and CI docs gates SHALL share validation categories

The local pre-commit docs gate and CI docs review workflow SHALL report the same docs validation categories for matching defects.

#### Scenario: Same broken docs route reports same category locally and in CI

- **WHEN** a docs change introduces a broken generated public route
- **THEN** local pre-commit reports a `published-link` finding
- **AND** the docs review CI workflow reports a `published-link` finding for the same defect category
