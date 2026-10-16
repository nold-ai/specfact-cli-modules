## ADDED Requirements

### Requirement: External installation survives fresh invocations
Acceptance SHALL exercise clean pipx, uv tool and repeated uvx invocations with installed modules and independent customer Python. Module discovery and dependency availability SHALL not require installing SpecFact into the customer environment or mutating disposable tool environments through unmanaged pip operations.

#### Scenario: Fresh pipx and uv tool installations
- **GIVEN** the CLI and signed modules are installed outside a clean customer project
- **WHEN** the customer bootstraps and reviews through each persistent tool route
- **THEN** the command loads its modules, uses project Python, detects a seeded defect and leaves project declarations and existing environment package inventory unchanged

#### Scenario: Repeated uvx invocation
- **GIVEN** one uvx invocation installs or discovers user-scoped modules and a later fresh uvx invocation runs review
- **WHEN** the disposable controller environment differs
- **THEN** module loading and declared dependencies work through supported installation paths without relying on a previously mutated uvx environment

### Requirement: Published compatibility follows installed evidence
The release SHALL validate Linux, macOS and Windows against the supported CLI Python matrix and record project-interpreter and analyzer capabilities separately. Manager support SHALL require faithful existing and cold project execution. Missing optional capability SHALL not become an unsupported blanket runtime claim.

#### Scenario: Manager and platform corpus
- **GIVEN** pip/pip-tools, detached Hatch, locked uv and Poetry projects have representative supported host cells
- **WHEN** installed acceptance runs
- **THEN** each advertised cell demonstrates imports, entrypoints, native dependencies, plugins, configured checks and seeded defect detection or remains explicitly unadvertised

#### Scenario: Independent Python support
- **GIVEN** a project interpreter differs from the CLI matrix and is admitted by its manager
- **WHEN** compatible project commands and supplemental checks run
- **THEN** their actual compatibility is recorded independently of the controller version and no capsule ABI allowlist rejects the whole project

### Requirement: CI replacement preserves independent gates
Capsule-only CI, native build and release requirements SHALL be replaced with installed customer-workflow acceptance without weakening independent source, quality, security, signing or review checks. Producer and ordinary consumer compatibility SHALL be verified before stable downstream adoption.

#### Scenario: Capsule-specific job is retired
- **GIVEN** the local implementation and paired core consumer are ready for installed verification
- **WHEN** workflow requirements are updated through their own spec and tests
- **THEN** replacement customer acceptance remains required and unrelated signing/security obligations including module symlink rejection are preserved

#### Scenario: Required installed cell fails
- **GIVEN** a required clean-install or customer-workflow cell fails or times out
- **WHEN** release readiness is assessed
- **THEN** the release is not declared accepted and a passing component suite cannot substitute for that workflow

### Requirement: Coordinated release and rollback are explicit
The release SHALL use a breaking major for Code Review and appropriate Codebase/core compatibility updates, normal module signing and canonical publication. Migration documentation SHALL state trusted-local execution, removed containment claims, report compatibility, installation routes, supported cells and rollback to an immutable compatible CLI/module pair.

#### Scenario: Release artifacts are immutable
- **GIVEN** new local-runtime artifacts are signed and published by normal reviewed tooling
- **WHEN** customers migrate
- **THEN** old signed capsules, modules and historical reports remain unchanged and do not inherit new local support claims

#### Scenario: Rollback after consumer incompatibility
- **GIVEN** installed acceptance finds an incompatible ordinary consumer
- **WHEN** the migration is rolled back
- **THEN** the previous compatible released CLI/module pair can be pinned without restoring a permanent alternate capsule backend in the new production runner
