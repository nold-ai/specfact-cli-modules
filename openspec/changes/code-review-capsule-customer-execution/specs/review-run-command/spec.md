# Specification: review-run-command

## ADDED Requirements

### Requirement: Non-root customer capsule execution

For the supported Linux x86-64 capsule path, the installed review command SHALL run as an ordinary host user with a verified runtime and documented host prerequisites. It SHALL preserve existing CLI syntax and assurance semantics and record nonempty scope and actual required analyzer coverage. These requirements do not grant local evidence protected PR authority.

#### Scenario: Public installation reviews independent fixtures

- **GIVEN** a fresh public installation on hosted Ubuntu 24.04 x86-64 for each of Python 3.11, 3.12, and 3.13, with signed official modules and supported namespace policy
- **AND** the installed module is verified with the approved public key, required integrity and signature checks, and its exact module name, publisher, version and payload digest are recorded independently of the capsule identity
- **WHEN** a non-root user reviews independent clean and deliberately defective Git fixtures through the real CLI
- **THEN** required analyzers actually execute and the reports and exit codes match fixture expectations, without publisher credentials, development source links, or signature overrides
- **AND** empty selection, missing required analyzer coverage, or UNKNOWN does not satisfy successful fixture execution

#### Scenario: Installed CLI reviews the modules repository

- **GIVEN** the same public installation and an explicit nonempty selection in the modules repository
- **WHEN** its installed CLI executes review
- **THEN** artifacts record actual analyzer coverage and findings, with no source-checkout import override or requirement to suppress existing findings to obtain a green result

#### Scenario: Customer GitHub Actions uses the installed signed payload

- **GIVEN** the official signed module is installed in a customer GitHub Actions repository
- **WHEN** that repository invokes review
- **THEN** the payload comes from verified installation provenance rather than requiring the modules repository's protected candidate checkout
- **AND** an actual candidate source checkout retains its strict candidate-context checks without fallback to a stale release

### Requirement: Sealed capsule mount destinations and private writes

The controller SHALL establish all required mount destinations before sealing the relevant runtime composition and SHALL authenticate added structure in its appropriate identity. Runtime payloads and source/configuration inputs SHALL remain read-only; analyzer home, cache, temporary state and output writes SHALL stay within declared process-private writable roots.

#### Scenario: Every launch mount variant starts

- **GIVEN** snapshot, multiple config roots, Radon control, project runtime, and plugin-preflight launch variants
- **WHEN** the verified production launcher builds each sandbox
- **THEN** required destinations already exist before the enclosing composition is sealed and launch does not need to create directories beneath a read-only parent
- **AND** destination collisions, symlink escapes, or unbound structure changes are rejected before analyzer execution

#### Scenario: Private state succeeds while sealed writes fail

- **GIVEN** a launched analyzer with declared private home/cache/temp/output roots
- **WHEN** it writes private state and attempts to modify the runtime payload or read-only snapshot
- **THEN** declared private writes succeed and sealed writes fail, without modifying signed installed files or the immutable cached base
- **AND** process-private roots are cleaned after success or failure according to their existing lifecycle

### Requirement: Actionable capsule failure evidence

Capsule failures SHALL retain the failed stage and ABI plus available sanitized diagnostics, expected/observed integrity identities, and filesystem path/error details. Infrastructure uncertainty SHALL remain visible under the existing authoritative status and failing-exit contract; it SHALL never become empty-review success or protected PR assurance.

#### Scenario: Namespace or directory setup fails

- **GIVEN** the verified launch fails because namespace permission is denied or a mount destination cannot be established
- **WHEN** the controller reports the failed run
- **THEN** evidence distinguishes capability denial from filesystem setup and analyzer failure, retains available path/errno/stderr, and provides actionable prerequisite guidance without credentials
- **AND** absent another known blocking finding, assurance is UNKNOWN with a failing exit and no unsandboxed retry

#### Scenario: Runtime digest differs

- **GIVEN** manifest, layer, wheel, installed-root, or composition verification fails
- **WHEN** the failure is surfaced through the review report
- **THEN** evidence identifies the verification stage, ABI and available expected/observed identities rather than silently adjusting the trusted checksum or counting an analyzer as complete
