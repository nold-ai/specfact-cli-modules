## ADDED Requirements

### Requirement: Radon runner reports staged KISS metrics
The bundle SHALL extend the Radon-backed runner with LOC, nesting-depth, and parameter-count findings while preserving complexity findings.

#### Scenario: Phase A LOC thresholds produce findings
- **GIVEN** a function exceeds the Phase A LOC threshold
- **WHEN** the radon-backed clean-code runner analyzes the file
- **THEN** it emits a `kiss` finding using the staged `>80` / `>120` thresholds
- **AND** existing complexity findings still use the current complexity mapping

#### Scenario: Nesting and parameter findings use the same governed report path
- **GIVEN** a function exceeds nesting-depth or parameter-count limits
- **WHEN** the runner analyzes the file
- **THEN** the resulting findings are emitted through the existing `ReviewFinding` model
- **AND** downstream scoring and policy consumers do not require a second report format
