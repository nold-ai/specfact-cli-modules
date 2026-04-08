## MODIFIED Requirements

### Requirement: icontract Decorator AST Scan and CrossHair Fast Pass

The system SHALL AST-scan changed Python files for public functions missing
`@require` / `@ensure` decorators, and run CrossHair with a configurable
per-path timeout for counterexample discovery. When no icontract usage is
detected in the reviewed files, `MISSING_ICONTRACT` findings SHALL be
suppressed entirely for that run.

#### Scenario: Public function without icontract decorators produces a contracts finding when icontract is in use

- **GIVEN** a Python file with a public function lacking icontract decorators
- **AND** at least one other reviewed file imports from `icontract`
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** a `ReviewFinding` is returned with `category="contracts"` and
  `severity="warning"`

#### Scenario: MISSING_ICONTRACT suppressed when no icontract usage detected

- **GIVEN** a set of reviewed Python files containing no `from icontract import` or
  `import icontract` statements
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** no `MISSING_ICONTRACT` findings are returned
- **AND** CrossHair still runs on the files

#### Scenario: Decorated public function produces no contracts finding

- **GIVEN** a Python file with a public function decorated with both `@require` and
  `@ensure`
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** no contract-related finding is returned for that function

#### Scenario: Private functions are excluded from the scan

- **GIVEN** a Python file with a function named `_private_helper` and no icontract
  decorators
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** no finding is produced for `_private_helper`

#### Scenario: CrossHair counterexample maps to a contracts warning

- **GIVEN** CrossHair finds a counterexample for a reviewed function
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** a `ReviewFinding` is returned with `category="contracts"`,
  `severity="warning"`, and `tool="crosshair"`

#### Scenario: CrossHair timeout or unavailability degrades gracefully

- **GIVEN** CrossHair times out or is not installed
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** the AST scan still runs
- **AND** no exception propagates to the caller
- **AND** CrossHair unavailability does not produce a blocking finding

#### Scenario: Bug-hunt mode uses extended CrossHair timeouts

- **GIVEN** `run_contract_check(files=[...], bug_hunt=True)` is called
- **WHEN** CrossHair executes
- **THEN** CrossHair runs with `--per_path_timeout 10`
- **AND** the subprocess timeout is 120 seconds
