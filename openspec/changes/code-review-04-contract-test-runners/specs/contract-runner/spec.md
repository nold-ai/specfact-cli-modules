## ADDED Requirements

### Requirement: icontract Decorator AST Scan and CrossHair Fast Pass

The system SHALL AST-scan changed Python files for public functions missing
`@require` / `@ensure` decorators, and run CrossHair with a 2-second per-path timeout
for counterexample discovery.

#### Scenario: Public function without icontract decorators produces a contracts finding

- **GIVEN** a Python file with a public function lacking icontract decorators
- **WHEN** `run_contract_check(files=[...])` is called
- **THEN** a `ReviewFinding` is returned with `category="contracts"` and
  `severity="warning"`

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
