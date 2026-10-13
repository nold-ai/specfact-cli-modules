## ADDED Requirements

### Requirement: Bounded operator Linux pytest execution budget

The reviewer SHALL accept an operator-selected integer Linux pytest member launch budget from1 through600seconds, defaulting to300seconds. It SHALL reject booleans, nonintegers and out-of-range values before launch. Only the targeted-pytest-coverage member SHALL receive the selected budget; all other existing deadlines, scope, tests, coverage, sandbox and signature requirements SHALL remain unchanged.

#### Scenario: Legacy invocation

- **WHEN** an operator supplies no budget
- **THEN** the Linux pytest member retains300seconds

#### Scenario: Explicit complete-suite budget

- **WHEN** an operator selects600seconds for Linux pytest
- **THEN** the complete configured pytest invocation receives600seconds and other members retain their existing budgets

#### Scenario: Invalid budget

- **WHEN** a boolean, noninteger, nonpositive or greater-than600 budget is supplied
- **THEN** admission rejects before execution

### Requirement: Budget provenance and incomplete evidence

Native reports SHALL retain requested and effective Linux pytest budgets without granting execution or coverage authority. A timed-out or incomplete invocation SHALL remain UNKNOWN with nonzero failure. Darwin default behavior SHALL remain unchanged and unsupported nondefault Linux overrides SHALL fail closed.

#### Scenario: Exhausted budget

- **WHEN** pytest does not complete within its budget
- **THEN** evidence remains UNKNOWN and cannot become a passing partial result

#### Scenario: Unsupported platform override

- **WHEN** a nondefault Linux-only budget is requested for a Darwin broker invocation
- **THEN** unsupported evidence is explicit and no override is silently ignored
