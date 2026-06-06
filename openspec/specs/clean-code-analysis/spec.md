# clean-code-analysis Specification

## Purpose
TBD - created by archiving change clean-code-02-expanded-review-module. Update Purpose after archive.
## Requirements
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

### Requirement: Clean-code signals can contribute to simplification feedback

The clean-code analysis layer SHALL allow high-confidence `dry` and `kiss` findings to contribute to the simplification feedback queue when they include deterministic rewrite or consolidation evidence. This SHALL NOT change the existing clean-code category semantics or blocking policy.

#### Scenario: High-confidence duplicate shape contributes related locations

- **WHEN** AST clean-code analysis detects duplicate intent with stable related locations
- **THEN** the finding MAY include simplification metadata such as `intent_key`, `rewrite_hint`, and `related_locations`
- **AND** the finding SHALL retain its governed category, such as `dry`, when that category is the primary principle

#### Scenario: Clean-code policy remains unchanged

- **WHEN** a clean-code finding contributes to the simplification queue
- **THEN** its existing category and severity semantics SHALL remain unchanged
- **AND** inclusion in `--focus simplify` SHALL NOT by itself make the finding more severe

