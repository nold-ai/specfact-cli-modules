## ADDED Requirements

### Requirement: Ruff findings map to governed review categories
The bundle SHALL invoke `ruff check --output-format json` for only the provided files
and translate supported Ruff rules into `ReviewFinding` records.

#### Scenario: Security rules map to the security category
- **GIVEN** Ruff reports a rule beginning with `S`
- **WHEN** `run_ruff(files=[...])` is called
- **THEN** the returned finding has `category="security"` and `tool="ruff"`

#### Scenario: Complexity rules map to clean_code
- **GIVEN** Ruff reports rule `C901`
- **WHEN** `run_ruff(files=[...])` is called
- **THEN** the returned finding has `category="clean_code"`

#### Scenario: Style rules map to style
- **GIVEN** Ruff reports a rule beginning with `E`, `F`, `I`, or `W`
- **WHEN** `run_ruff(files=[...])` is called
- **THEN** the returned finding has `category="style"`

#### Scenario: Findings are filtered to the provided file list
- **GIVEN** a file list containing one Python file
- **WHEN** mocked Ruff output includes findings for another file
- **THEN** only findings for the provided file are returned

#### Scenario: Parse errors or missing Ruff produce tool_error
- **GIVEN** Ruff is unavailable or returns invalid JSON
- **WHEN** `run_ruff(files=[...])` is called
- **THEN** exactly one `ReviewFinding` with `category="tool_error"` is returned
