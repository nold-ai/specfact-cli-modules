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

#### Scenario: Changed-source type analysis
- **WHEN** independent review checks the exact changed Python inventory
- **THEN** its type-analysis projection includes every changed Python file, retains trusted type settings and import context, and does not scan unrelated files whose diagnostics the signed adapter discards
- **AND** timeouts remain incomplete and the full-repository quality type gate remains required

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

#### Scenario: Existing package test layouts
- **WHEN** a changed package source lacks a mirrored unit-test filename
- **THEN** native review selects the package's existing unit-test files without requiring a new layout, and rejects a package with no unit tests

#### Scenario: Test selection follows coverage roots
- **WHEN** a changed production source belongs to a configured coverage root, including `tools/` or top-level `src/`
- **THEN** native review selects its existing mirrored, flat or package unit tests before enforcing coverage, using the same trusted root inventory for both operations

#### Scenario: Explicit nonmirrored test correspondence
- **WHEN** a production source has known tests outside its mirrored or directory layout
- **THEN** native review selects all explicitly mapped existing test files before directory fallback, and rejects a missing mapped file
- **AND** the applicable per-file coverage policy remains required after selection

#### Scenario: Preserve paired-core smoke ownership
- **WHEN** the paired core requires its reviewed portable fixture for package-manager smoke
- **THEN** CI authenticates that fixture and runs all six existing launchers with isolated launcher dependencies, while candidate source remains subject to the complete quality, native acceptance and signing gates
- **AND** fixture smoke does not claim candidate module acceptance
- **AND** CI authenticates and seeds the paired core's frozen dependency cache before its offline child synchronization

#### Scenario: Preserve released and paired core verification
- **WHEN** quality intentionally installs the selected paired core checkout instead of the immutable development release
- **THEN** the complete quality matrix verifies its editable distribution identity and registry API import origins against that selected checkout
- **AND** the declared development core remains exactly version 0.55.4, and the independent native job always verifies that released version and both registry APIs before candidate bootstrap
- **AND** an unrelated or unproven installation cannot satisfy either verification mode
