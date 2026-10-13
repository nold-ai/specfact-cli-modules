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

### Requirement: Sealed nonportable pytest budget propagation

A nondefault explicitly admitted Linux pytest budget SHALL be carried in the immutable capsule request and applied to both the member launch and nonportable pytest subprocess. Absent or default300 SHALL preserve the legacy120-second inner deadline and300-second outer deadline. Private controls SHALL admit exact integers1..600 only for targeted-pytest-coverage, remain operation-local across nested/concurrent calls and restore after exceptions. Portable pytest keeps its existing inner policy; Darwin and the other nine members remain unchanged.

#### Scenario: Explicit nonportable subprocess

- **WHEN** an operator selects600seconds for sealed Linux nonportable pytest
- **THEN** its actual subprocess receives600seconds and the report records both requested and effective inner/outer budgets

#### Scenario: Invalid private control

- **WHEN** a malformed budget or another member carries a pytest budget
- **THEN** request admission fails closed before member execution

#### Scenario: Restored operation context

- **WHEN** nested or concurrent invocations finish or raise
- **THEN** each invocation retains its own budget and later default calls retain the legacy deadline
