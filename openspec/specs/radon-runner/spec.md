# radon-runner Specification

## Purpose
TBD - created by archiving change code-review-02-ruff-radon-runners. Update Purpose after archive.
## Requirements
### Requirement: Radon complexity maps to review findings
The bundle SHALL invoke `radon cc -j` for only the provided files and convert function
complexity above 12 into `ReviewFinding` records.

#### Scenario: Complexity 13 produces a warning
- **GIVEN** Radon reports a function with complexity 13
- **WHEN** `run_radon(files=[...])` is called
- **THEN** a `ReviewFinding` is returned with `severity="warning"` and
  `category="clean_code"`

#### Scenario: Complexity 16 produces an error
- **GIVEN** Radon reports a function with complexity 16
- **WHEN** `run_radon(files=[...])` is called
- **THEN** a `ReviewFinding` is returned with `severity="error"` and
  `category="clean_code"`

#### Scenario: Complexity 12 or below produces no finding
- **GIVEN** all reported blocks have complexity 12 or below
- **WHEN** `run_radon(files=[...])` is called
- **THEN** no findings are returned

#### Scenario: Findings are filtered to the provided file list
- **GIVEN** a file list containing one Python file
- **WHEN** mocked Radon output includes a second file
- **THEN** findings for the second file are excluded

#### Scenario: Parse errors or missing Radon produce tool_error
- **GIVEN** Radon is unavailable or returns invalid JSON
- **WHEN** `run_radon(files=[...])` is called
- **THEN** exactly one `ReviewFinding` with `category="tool_error"` is returned

### Requirement: Radon is available in the standard repo environment
The bundle SHALL declare the Radon executable in the default development environment
used by local and CI quality gates.

#### Scenario: Repo quality environment can execute Radon
- **GIVEN** the standard repository development environment is created
- **WHEN** Radon-backed review tooling or tests run in that environment
- **THEN** the `radon` executable is available on `PATH`

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

