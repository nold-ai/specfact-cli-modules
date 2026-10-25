## ADDED Requirements

### Requirement: Preserve complete independent native review
The repository SHALL require a separately installed verified signed reviewer, all ten existing review members, native test coverage and module signatures before accepting a code pull request. It SHALL preserve changed enforcement and independent security without executing capsule review.

#### Scenario: Complete native review
- **WHEN** the exact candidate has complete native analyzer and test evidence
- **THEN** the required native job may pass under the existing finding policy

#### Scenario: Incomplete analyzer cannot pass
- **WHEN** a required member is absent, duplicated, skipped, unknown, malformed, timed out or has a tool error
- **THEN** acceptance fails even if the ordinary engine exit is zero

#### Scenario: Trusted reviewer and configuration
- **WHEN** candidate code attempts to shadow reviewer imports or omit required rules
- **THEN** the controller retains the signed installation and rejects missing control inputs

#### Scenario: Conflicting analyzer dependencies
- **WHEN** a pinned analyzer CLI has dependencies incompatible with the signed controller
- **THEN** CI installs that CLI separately, preserves its trusted pin and recorded transitive constraints, records the version of the executable actually invoked and retains bounded startup failure diagnostics

### Requirement: Bind acceptance to exact source and required jobs
The native CI receipt SHALL bind the event head and complete required-member inventory. The quality matrix SHALL reject every non-successful native prerequisite. Native receipts SHALL NOT satisfy protected pr_range, core #680 or C15 contracts.

#### Scenario: Reject stale evidence
- **WHEN** a receipt belongs to another head or source changes during execution
- **THEN** acceptance fails

#### Scenario: Preserve mandatory prerequisites
- **WHEN** signatures, native Hatch, independent review or migration scope fail or are skipped
- **THEN** quality cannot pass
