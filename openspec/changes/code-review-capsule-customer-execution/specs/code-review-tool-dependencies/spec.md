# Specification: code-review-tool-dependencies

## ADDED Requirements

### Requirement: Anonymous verified capsule acquisition and reuse

The signed capsule path SHALL acquire public runtime artifacts through the production downloader without publisher/account credentials, verify signed descriptor identities and bounds, and revalidate verified caches before reuse. Anonymous registry-issued bearer challenges are allowed. This requirement does not authorize historical host-tool fallback behavior.

#### Scenario: Empty customer cache retrieves public runtime

- **GIVEN** a supported ABI and an empty user-owned cache without registry login or publisher tokens
- **WHEN** the installed CLI retrieves every required runtime descriptor and layer through its production downloader
- **THEN** anonymous authentication and allowed redirects complete with all required digest/size checks and materialization evidence

#### Scenario: Warm cache preserves verified identity

- **GIVEN** a complete verified cache and otherwise equivalent bound inputs
- **WHEN** acquisition is repeated with network access prohibited
- **THEN** cached bytes are reverified and base/toolchain identity agrees with the cold run; composition identity agrees when its bound inputs agree

#### Scenario: Corrupt or incomplete cache is not accepted

- **GIVEN** a cache with changed bytes, wrong size, a missing required entry, or mixed ABI content and no acquisition network access
- **WHEN** the runtime is requested
- **THEN** incomplete or invalid content fails closed before analyzer execution and cannot be treated as a verified cache hit

### Requirement: Non-root deterministic capsule materialization

The controller SHALL materialize capsules in user-owned staging without root privileges and verify their expected signed content and filesystem manifest. Equivalent supported installations SHALL produce the declared identity independently of cache location and supported ambient umask, without weakening integrity checks.

#### Scenario: Every supported ABI root identity is reproducible

- **GIVEN** the same locked artifacts for each of cp311, cp312 and cp313, two distinct fresh cache roots, and ordinary host users under explicit umasks 022 and 077
- **WHEN** acquisition, offline installation and final-root verification run
- **THEN** materialization satisfies the signed content/mode manifest in both cases and records exact entry evidence for any failure
- **AND** observed mismatches are not used to overwrite trusted digests merely to pass verification

### Requirement: Verified launcher namespace prerequisite

The capability probe SHALL exercise the verified static launcher with the production descriptor execution, namespace flags, and observation constraints. It SHALL report unsupported host policy before claiming analyzer completion, without silent elevation, global host-policy weakening, or a host-launcher substitute.

#### Scenario: Namespace policy permits the production launcher

- **GIVEN** a supported host policy and verified launcher
- **WHEN** a non-root user probes materialization and review launch capabilities
- **THEN** the actual production execution mechanisms succeed and their identity/capability evidence is recorded

#### Scenario: Namespace policy denies the production launcher

- **GIVEN** host policy denies required namespace or observation capabilities
- **WHEN** capsule execution is requested
- **THEN** the run fails closed with actionable supported-prerequisite guidance, without running review as root, changing host policy automatically, or falling back outside the sandbox

### Requirement: Signed release customer execution gate

A capsule repair release SHALL pass the GitHub-hosted Ubuntu 24.04 x86-64 Python 3.11/3.12/3.13 customer matrix against its actual public signed installation. Changed immutable artifacts SHALL receive new identities and consistent module patch version, lock/resource bindings, signatures and registry entries through canonical publication.

#### Scenario: Published repair is accepted

- **GIVEN** candidate regressions and quality gates passed and a corrected signed release was published
- **WHEN** fresh non-root GitHub-hosted Ubuntu 24.04 x86-64 jobs for Python 3.11, 3.12 and 3.13 install that release and exercise clean/defective fixtures and the modules repository
- **THEN** all required analyzer coverage and expected outcomes are verified before the bug is closed
- **AND** candidate-only smoke, prepared caches, privileged execution, skipped required analyzers, or UNKNOWN cannot replace that evidence

#### Scenario: Release rollback preserves immutable history

- **GIVEN** a published repair needs rollback
- **WHEN** maintainers revert through canonical signed publication and registry procedures
- **THEN** previously published payload bytes and historical integrity evidence remain immutable and any known defect in the restored baseline is documented
