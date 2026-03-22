## ADDED Requirements

### Requirement: Clean-Code Analysis Runners
The review bundle SHALL emit governed findings for the clean-code categories required by the 2026-03-22 plan.

#### Scenario: Naming and exception-pattern rules emit governed findings
- **GIVEN** a reviewed Python file contains a public symbol with a banned generic name or a swallowed exception pattern
- **WHEN** the clean-code analysis runs
- **THEN** the review report includes findings in the appropriate clean-code category
- **AND** the finding payload keeps rule ID, severity, category, and file location stable

#### Scenario: AST-based clean-code runners stay repo-local and Python-native
- **GIVEN** solid, yagni, and dry checks are enabled
- **WHEN** the bundle analyzes Python source files
- **THEN** the checks run without introducing a Node.js dependency
- **AND** each finding is attributed to `solid`, `yagni`, or `dry` respectively
