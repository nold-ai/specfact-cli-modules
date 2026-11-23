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

#### Scenario: CrossHair analyzes variadic constructors and preserves findings
- **WHEN** the pinned Python 3.12 contracts analyzer synthesizes a constructor whose allocation and initialization methods accept variadic arguments
- **THEN** it binds the constructor without passing a receiver or discarding variadic parameters
- **AND** it sends candidate console output to diagnostics and keeps contract findings in the structured result stream
- **AND** unexpected analyzer source inputs or incomplete execution fail the existing independent review

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

### Requirement: Resolve CI verification inputs without weakening trust

The orchestrator SHALL preserve cryptographic manifest verification, filesystem payload checks, version-bump enforcement and main-target signature requirements. Secret-free verification SHALL read the pinned replacement public key from the exact trusted event commit and fail closed when that authority is unavailable.

#### Scenario: Secret-free signature verification
- **WHEN** neither public-key secret is configured and the exact PR base commit or pre-push commit contains the public key
- **THEN** the workflow verifies signed candidate bundles with the replacement key in that commit and retains every payload and version check

#### Scenario: Candidate cannot replace trust
- **WHEN** a candidate replaces the public key and signs a fixture with its replacement private key
- **THEN** verification fails under the trusted event key

#### Scenario: Invalid verification inputs
- **WHEN** a signature or payload is invalid, the configured key is invalid, or the trusted fallback revision is missing, zero, malformed, unavailable or lacks the key
- **THEN** the signature prerequisite fails without a looser fallback
- **AND** an invalid configured secret cannot trigger fallback to a repository key

### Requirement: Keep the released reviewer controller reproducible

Both controller dependency installation operations SHALL constrain Typer to the already reviewed compatible version 0.27.0. The job SHALL assert the final Typer version together with released core 0.55.4 and preserve signed marketplace reviewer 0.51.2, immutable registry API checks, separate Semgrep constraints, exact-head review completeness, coverage and failure propagation. This compatibility correction SHALL not upgrade the reviewer or change candidate runtime policy.

#### Scenario: Repository Ruff and signed reviewer Ruff diverge
- **WHEN** the repository development configuration requires a different Ruff version from the trusted analyzer lock
- **THEN** the isolated signed reviewer installs Ruff at the lock's exact pin and the repository quality environment retains its own Ruff dependency

#### Scenario: Released controller installs after dependency drift
- **WHEN** the independent reviewer is installed in a fresh controller environment
- **THEN** both controller resolution operations retain Typer 0.27.0 and the released CLI and registry APIs load before the signed marketplace reviewer executes

### Requirement: Preserve generated CLI evidence across supported argument types

Command-overview validation SHALL render positional argument labels for supported Click and Typer argument objects. Explicit metavars and existing generated command semantics SHALL remain unchanged when an optional display-name attribute is unavailable. This compatibility correction SHALL preserve the required documentation and quality gates without changing customer command behavior.

#### Scenario: Current Typer argument has no display-name property
- **WHEN** a supported Typer argument exposes its name but lacks human_readable_name
- **THEN** command-overview generation renders the same default uppercase argument label without raising AttributeError

#### Scenario: Explicit argument label remains authoritative
- **WHEN** an argument declares an explicit metavar
- **THEN** generation preserves that label for both Click and Typer argument objects

#### Scenario: Independent analyzer imports the command overview generator
- **WHEN** the contracts analyzer imports the hyphenated command-overview script by its source path
- **THEN** the generator's runtime contracts load without an annotation-resolution error and the analyzer inspects generation and freshness without passing its own arguments to the generator's CLI
- **AND** the standalone documentation CI environment installs the same pinned analyzer before running the regression test
