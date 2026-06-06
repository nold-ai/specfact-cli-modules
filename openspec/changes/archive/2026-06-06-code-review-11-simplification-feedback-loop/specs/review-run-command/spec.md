## ADDED Requirements

### Requirement: Review run supports simplify focus

The `specfact code review run` command SHALL accept `--focus simplify` as a targeted review focus for IDE simplification feedback. The focus SHALL retain findings that belong in the simplification queue, including `ai_bloat`, high-confidence duplicate-intent `dry`, and high-confidence simplicity `kiss` findings.

#### Scenario: Simplify focus emits simplification queue

- **WHEN** `specfact code review run --focus simplify --json --out .specfact/code-review.json` completes
- **THEN** the JSON report SHALL retain simplification-focused findings
- **AND** retained findings SHALL include enough metadata for `/specfact.08-simplify` to group and explain the candidate

#### Scenario: Simplify focus does not make advisories blocking

- **WHEN** a simplify-focused run contains only advisory simplification findings
- **THEN** the process SHALL remain non-blocking under enforce mode
- **AND** the governed score SHALL NOT be reduced by simplification-only findings

#### Scenario: Simplify focus composes with scope controls

- **WHEN** `--focus simplify` is combined with `--scope changed`, `--scope full`, `--path`, or positional files
- **THEN** the command SHALL first resolve the reviewed file set using the existing scope rules
- **AND** it SHALL then filter or prioritize findings for the simplification queue
