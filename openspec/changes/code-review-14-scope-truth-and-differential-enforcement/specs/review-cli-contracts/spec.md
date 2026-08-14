## ADDED Requirements

### Requirement: Truthful Review Assurance Status

The governed review report SHALL expose assurance status `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE`. `WAIVED` SHALL be a governance overlay, not a verifier-produced status. A mandatory UNKNOWN SHALL prevent PASS. NOT_APPLICABLE SHALL require successfully resolved no-governed-impact evidence.

#### Scenario: Mandatory evidence is unknown

- **GIVEN** scope or a mandatory analyzer is unknown
- **WHEN** enforce-mode reporting completes
- **THEN** assurance is UNKNOWN and process exit is non-zero
- **AND** partial facts/findings remain available
- **AND** the human summary does not say all validations passed.

#### Scenario: Shadow preserves unknown while exiting zero

- **GIVEN** the same unknown evidence under shadow mode
- **WHEN** reporting completes
- **THEN** process exit may be zero for rollout
- **AND** report assurance remains UNKNOWN
- **AND** no field rewrites the unknown claim to pass.

### Requirement: Review CLI Contracts Cover Explicit Scope and Differential Evidence

CLI contract fixtures SHALL cover worktree, index, range, full, positional files, deprecated changed alias, full-ref validation, merge-base selection, changed-test inclusion, empty range, Git failure, base/head classifications, analyzer coverage, and invalid option combinations.

#### Scenario: Range contract requires base and head

- **GIVEN** range scope is requested without one required ref or together with positional files
- **WHEN** the CLI parses the request
- **THEN** it fails with a bounded error and a supported invocation example.

