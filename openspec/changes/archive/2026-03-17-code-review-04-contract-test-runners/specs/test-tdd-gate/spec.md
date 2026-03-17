## ADDED Requirements

### Requirement: TDD Gate Enforcing Test File Existence and Coverage Threshold

The system SHALL block the review if any changed bundle source file has no corresponding
test file, if the targeted tests fail, or if measured coverage is below 80%.

#### Scenario: Changed bundle source file with no test file produces BLOCK

- **GIVEN** a changed file
  `packages/specfact-code-review/src/specfact_code_review/run/scorer.py`
- **AND** no corresponding file exists at
  `tests/unit/specfact_code_review/run/test_scorer.py`
- **WHEN** the TDD gate runs
- **THEN** a `ReviewFinding` with `rule="TEST_FILE_MISSING"`, `severity="error"`, and
  `category="testing"` is returned
- **AND** the overall verdict is forced to BLOCK

#### Scenario: Passing tests with coverage at or above 80% produce no testing finding

- **GIVEN** a changed bundle source file with a corresponding test file
- **AND** the targeted tests pass with 85% coverage
- **WHEN** the TDD gate runs
- **THEN** no testing finding is returned

#### Scenario: Test failure produces BLOCK finding

- **GIVEN** a changed bundle source file with a corresponding test file
- **AND** the targeted test run fails
- **WHEN** the TDD gate runs
- **THEN** a `ReviewFinding` with `severity="error"` and `category="testing"` is
  returned

#### Scenario: Coverage below 80% produces warning

- **GIVEN** a changed bundle source file with a corresponding test file
- **AND** the targeted test run passes with 65% coverage
- **WHEN** the TDD gate runs
- **THEN** a `ReviewFinding` with `severity="warning"` and `category="testing"` is
  returned

#### Scenario: `no_tests` skips the TDD gate

- **GIVEN** `no_tests=True` is passed to the review runner
- **WHEN** the runner executes
- **THEN** no TDD gate check is performed
- **AND** no testing findings are returned

#### Scenario: Absolute reviewed source paths still map to the expected test file

- **GIVEN** a changed bundle source file is provided as an absolute path
- **WHEN** the TDD gate derives the expected unit test location
- **THEN** it resolves the same `tests/unit/specfact_code_review/...` path as the
  corresponding repo-relative source file
- **AND** missing tests and coverage enforcement still apply
