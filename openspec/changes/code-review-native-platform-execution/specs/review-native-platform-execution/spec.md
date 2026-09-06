# Specification: review-native-platform-execution

## ADDED Requirements

### Requirement: Native local execution

Code Review SHALL execute directly on the user's macOS Linux or Windows host without an OS or CPU emulation dependency.

#### Scenario: Agent invokes the native CLI

- **GIVEN** a supported OS and architecture with verified native runtime artifacts provisioned
- **WHEN** a developer or agent invokes the ordinary review command locally
- **THEN** review executes on that OS without Docker WSL VM or emulation and produces agent-readable results independently of GitHub

#### Scenario: Architecture is not silently substituted

- **GIVEN** a requested x64 or ARM64 OS combination lacks a required native artifact
- **WHEN** runtime support is assessed or execution is requested
- **THEN** the missing support remains explicit and no emulated substitute is advertised as native

### Requirement: Native isolation capability evidence

Each native backend SHALL enforce and report its approved isolation capabilities without falsely claiming Linux-specific observations on another OS.

#### Scenario: Isolation and cleanup are proven

- **GIVEN** a backend selected for native execution
- **WHEN** filesystem and network policy child-process cleanup resource bounds and load-path integrity are exercised
- **THEN** native tests prove the approved capability contract and results identify the backend OS architecture and runtime

#### Scenario: Required capability is unavailable

- **GIVEN** an isolation capability or required analyzer is missing incompatible or unverifiable
- **WHEN** review evaluates assurance
- **THEN** it reports explicit incomplete evidence according to the approved status/exit contract rather than silently weakening isolation or dropping an analyzer

### Requirement: Portable review semantics

Native execution SHALL preserve the released scope differential and C15 authoritative enforcement contracts while recording platform-dependent behavior honestly.

#### Scenario: Portable fixture classification

- **GIVEN** the same portable fixture and equivalent approved analyzer and policy versions on each supported platform
- **WHEN** native review evaluates introduced fixed and unchanged findings
- **THEN** classification and authoritative status/exit semantics agree without promoting local evidence to protected CI authority

#### Scenario: OS dependent project tests

- **GIVEN** project dependencies or tests have intentional OS-specific behavior
- **WHEN** native validation evaluates the project
- **THEN** results retain their actual platform identity and observed outcomes rather than claiming identical runtime behavior

### Requirement: Verified provisioning and offline reuse

Native runtimes SHALL preserve full-module-directory checksum/signature verification for module-shipped files. External runtimes SHALL use a separately approved signed lock/manifest binding artifact digests, applicable layer digests, installed payload/root manifests, OS/architecture/Python ABI, dependency closure, and cache identity. Provisioning SHALL verify artifact and extracted payload integrity; every launch, including offline reuse, SHALL revalidate the selected payload/root against the approved bindings. Unbound, stale, partial, mixed, or mismatched caches SHALL fail closed before analyzer execution.

#### Scenario: Cached native runtime

- **GIVEN** a complete verified native runtime cache for the active OS architecture and Python ABI
- **WHEN** review runs without network access
- **THEN** it revalidates the selected runtime payload/root against the approved signed bindings, uses that runtime, and records its identity without unreported host dependency fallback

#### Scenario: Invalid native artifact

- **GIVEN** a runtime or dependency has mismatched integrity incompatible ABI or unavailable native code
- **WHEN** provisioning or execution is requested
- **THEN** the runtime fails closed with an actionable diagnostic and does not use emulation

#### Scenario: Module-shipped native artifact changes

- **GIVEN** a native file covered by the full-module checksum/signature has changed
- **WHEN** module payload verification is performed before launch
- **THEN** verification fails and no analyzer executes; verification is not narrowed to only the Python package

#### Scenario: External cache has no approved binding

- **GIVEN** a cached native artifact is outside the module directory and has no approved signed lock/manifest binding
- **WHEN** provisioning or offline reuse is requested
- **THEN** it fails closed before analyzer execution even when module verification succeeds

#### Scenario: Stale external cache identity

- **GIVEN** a cached runtime matches an earlier approved lock but not the currently selected runtime identity
- **WHEN** review prepares to launch from that cache
- **THEN** the stale cache is rejected before analyzer execution

#### Scenario: Partial external runtime cache

- **GIVEN** a selected cache lacks a file or dependency required by its signed installed payload/root manifest
- **WHEN** provisioning or offline reuse verifies the selected runtime
- **THEN** the incomplete cache is rejected before analyzer execution

#### Scenario: Mixed external runtime cache

- **GIVEN** cached files come from different versions platforms or Python ABIs despite individual artifact digests being valid
- **WHEN** the complete runtime is checked against the approved signed lock and dependency closure
- **THEN** the mixed cache is rejected before analyzer execution

### Requirement: Released baseline implementation gate

Native production implementation SHALL wait for the layout correction released checkpoint/conformance runtime and released core C15 adoption and SHALL be reassessed against their exact identities.

#### Scenario: Prerequisite remains incomplete

- **GIVEN** one of modules #459 modules #434 or core #679 is not complete with required release evidence
- **WHEN** an agent prepares to implement native execution
- **THEN** it stops before production changes while planning artifacts may still merge to dev

#### Scenario: Baseline drives the full lifecycle

- **GIVEN** the prerequisite releases are verified and pinned
- **WHEN** native implementation is prepared performed and finalized
- **THEN** approved design and failing-first tests precede code checkpoints verify progress and final conformance verifies the resulting exact candidate
