## ADDED Requirements

### Requirement: Radon complexity maps to review findings
The bundle SHALL invoke `radon cc -j` for only the provided files and convert function
complexity above 12 into `ReviewFinding` records.

### Requirement: Radon is available in the standard repo environment
The bundle SHALL declare the Radon executable in the default development environment
used by local and CI quality gates.

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
