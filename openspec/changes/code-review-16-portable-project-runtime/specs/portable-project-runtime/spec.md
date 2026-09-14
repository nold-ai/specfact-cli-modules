# Portable project runtime

## ADDED Requirements

### Requirement: Discover a project without executing its code

The system SHALL expose read-only runtime inspection with deterministic package-manager and input discovery. Explicit configuration SHALL win over active environment context and unambiguous repository discovery. Build backend metadata SHALL NOT imply an environment manager. Unsafe paths, ambiguous environments and unsupported Python constraints SHALL be actionable diagnostics.

#### Scenario: Hatchling is only a build backend
- **GIVEN** a project using hatchling with uv.lock and no Hatch environments
- **WHEN** runtime inspection runs
- **THEN** uv is selected and no environment is created

#### Scenario: External Hatch configuration
- **GIVEN** inherited and detached environments in hatch.toml and pyproject.toml
- **WHEN** a specific environment is selected
- **THEN** its dependencies, extras, source roots and configuration inputs are captured without merging unrelated environments

#### Scenario: Conflicting environment evidence
- **GIVEN** both Poetry and uv lockfiles and no explicit selection
- **WHEN** runtime inspection runs
- **THEN** one diagnostic names the competing managers and the project-config remedy

#### Scenario: Requirements constraints and local inputs
- **GIVEN** pip requirements with recursive requirement/constraint includes and repository-local editable dependencies
- **WHEN** inputs are discovered
- **THEN** their bytes are bound to the plan and escaping or cyclic includes are rejected

### Requirement: Prepare an isolated reproducible runtime

The system SHALL automatically prepare or reuse a private runtime using the selected manager. The system SHALL preserve source files, lockfiles and existing environments, isolate executable build hooks, record resolved dependencies and native components, verify cached content, and support offline warm reuse. Unlocked resolution SHALL be recorded without changing the customer's lockfiles.

#### Scenario: Cold preparation and offline warm reuse
- **GIVEN** a supported project and an empty private cache
- **WHEN** prepare runs and then repeats offline
- **THEN** both return the same validated dependency artifact and no customer source changes

#### Scenario: Changed dependency inputs
- **GIVEN** a prepared runtime
- **WHEN** a dependency, constraint, selected group or lock changes
- **THEN** the previous runtime is not reused as matching evidence

#### Scenario: Corrupt or escaping artifact
- **GIVEN** modified cached bytes, an escaping symlink, or interrupted preparation
- **WHEN** runtime attachment or reuse runs
- **THEN** the artifact is rejected and cannot yield PASS

### Requirement: Separate project imports from the sealed supervisor

The system SHALL introduce project-runtime-layer-v2 for local runtime descriptors, preserve the v1 reader and protected trust rules, and run target imports/plugins in isolated workers. Customer dependencies SHALL NOT shadow supervisor entry points. Ordinary project dependency names SHALL NOT be rejected merely because an analyzer also depends on them.

#### Scenario: Common dependency collision
- **GIVEN** a target depending on requests, httpx, icontract or pydantic
- **WHEN** v2 worker analysis runs
- **THEN** the project's recorded dependencies are used without importing them into the supervisor

#### Scenario: Real incompatibility
- **GIVEN** incompatible tool/project constraints or a missing required native library
- **WHEN** preparation or worker preflight runs
- **THEN** the exact incompatible dependency/library is reported without silently substituting versions

#### Scenario: Member-specific dependency closure
- **GIVEN** the signed analyzer environment contains packages outside a member's declared dependency graph
- **WHEN** a project worker or that analyzer member resolves imports
- **THEN** unrelated analyzer packages are unavailable, project-owned dependencies take precedence where compatible, and the selected member's dependency graph is recorded


### Requirement: Attach context to every review scope

The system SHALL attach runtime evidence to explicit-file, full, worktree, index and range review. Base/head snapshots with different inputs SHALL receive different runtime bindings. Local provenance SHALL NOT become protected PR authority. Official installed customer modules SHALL work with GITHUB_ACTIONS=true.

#### Scenario: Explicit-file customer review
- **GIVEN** an installed official module in an external repository
- **WHEN** changed Python files are reviewed without a PR context descriptor
- **THEN** runtime preparation happens automatically and dependent analyzers use it

#### Scenario: Missing runtime preserves independent evidence
- **GIVEN** preparation fails
- **WHEN** the review runs
- **THEN** independent static members still execute and dependent members reference one actionable root diagnostic with incomplete evidence

### Requirement: Observe ordinary customer pytest execution

The system SHALL preserve pytest configuration, source paths, plugins and selection semantics, and record actual collection/execution. Unsupported controls SHALL name the exact option and affected evidence. Genuine findings SHALL remain after a valid runtime is attached.

#### Scenario: Detached Hatch reconstruction
- **GIVEN** src layout, mixed source/test input, third-party/native imports, -p pytest_asyncio.plugin, importlib mode and pythonpath
- **WHEN** capsule review runs
- **THEN** applicable analyzers complete and pytest executes the selected tests

#### Scenario: Controlled regression
- **GIVEN** a known failing assertion or genuine missing import in a disposable copy
- **WHEN** review runs
- **THEN** real findings and failing evidence remain visible

### Requirement: Validate external repositories through released installation

The system SHALL require a pinned Requests/pip, Hatch/Hatch, Flask/uv and Poetry/Poetry corpus on Ubuntu 24.04 CPython 3.11/3.12/3.13 for relevant changes and published releases. Tests SHALL reject empty or UNKNOWN required analysis, retain real findings, verify source immutability, and capture exact artifacts, test inventory, exit codes, duration and transfer cost.

#### Scenario: Signed release acceptance
- **GIVEN** the published signed module and pinned upstream checkouts
- **WHEN** cold and offline-warm customer reviews run
- **THEN** actual applicable analysis and test execution complete without development overrides

### Requirement: Native environment and execution evidence fidelity
The runtime SHALL select a concrete environment from the package manager's native export, preserve installed executable entry points, and retain actual pytest setup, collection, and call failures. Corpus host baselines SHALL reject startup failures without executed tests.

#### Scenario: Hatch internal matrix selection
- **GIVEN** a Hatch test matrix with one environment matching the selected Python ABI
- **WHEN** preparation selects the matrix
- **THEN** Hatch creates and locates that concrete environment using its positional environment argument
- **AND** multiple matching environments produce an ambiguity diagnostic before installation

#### Scenario: Native executable required by test setup
- **GIVEN** an installed distribution that owns a console script or native executable
- **WHEN** a target worker starts tests
- **THEN** the executable is available in the isolated target runtime and included in its inventory
- **AND** its build-machine interpreter path is never retained

#### Scenario: Test setup and host startup failures
- **GIVEN** pytest fails before a test call
- **WHEN** observations are recorded
- **THEN** the failed phase and exception text remain available with incomplete evidence
- **AND** a host command that never executes tests cannot satisfy corpus acceptance

#### Scenario: VCS-derived build version and cache reuse
- **GIVEN** a project whose build derives its version from Git history or tags
- **WHEN** its runtime is prepared for a worktree or immutable review side
- **THEN** the private build receives sanitized Git metadata and an index matching the selected commit
- **AND** cache identity includes the selected commit, tag identities, and shallow-history boundary
- **AND** source modifications remain modifications rather than becoming a fabricated clean version

#### Scenario: Project Python differs from the controller
- **GIVEN** a project selects Python 3.11 through explicit configuration or `.python-version`, while the controller uses Python 3.12
- **WHEN** preparation or review starts
- **THEN** the signed Python 3.11 worker is selected and verified against the project's full Python version constraint
- **AND** base and head snapshots select their own compatible workers
- **AND** an unsupported pin or conflicting version constraint produces an explicit diagnostic

#### Scenario: Offline plugin coordination
- **GIVEN** a pytest plugin uses localhost sockets to coordinate workers
- **WHEN** tests run in an offline target namespace
- **THEN** localhost resolves using a fixed private hosts file without granting external network access
- **AND** pytest internal errors retain their exact traceback as incomplete evidence

#### Scenario: Nested review tests do not inherit controller scope
- **GIVEN** the development review controller uses cached-diff enforcement
- **WHEN** it executes repository tests that invoke review themselves
- **THEN** controller-only diff selection does not leak into those test processes
- **AND** tests can explicitly select their own diff scope
