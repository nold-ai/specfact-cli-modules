## Scope rescope — 2026-09-20

Consume independent current_execution and optional chronology without inflating test results into full requirement coverage. The full validation graph is not a prerequisite for <https://github.com/nold-ai/specfact-cli-modules/issues/481> or ordinary current-run validation.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## ADDED Requirements

### Requirement: Full Chain Sidecar Inputs

The sidecar validation capability SHALL support full-chain payload checks in addition to spec-code checks.

#### Scenario: Sidecar consumes full-chain input set

- **GIVEN** requirement and architecture artifact paths are provided
- **WHEN** sidecar validation runs
- **THEN** sidecar validates layered chain references
- **AND** results are merged into full-chain evidence output.

#### Scenario: Existing spec-code validation remains supported

- **GIVEN** sidecar is invoked without requirements/architecture inputs
- **WHEN** validation executes
- **THEN** existing spec-code validation behavior continues unchanged.
