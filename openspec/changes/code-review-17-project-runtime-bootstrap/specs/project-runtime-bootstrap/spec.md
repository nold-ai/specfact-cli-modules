## ADDED Requirements

### Requirement: Independent customer interpreter selection
The runtime service SHALL select and probe the customer interpreter independently of the external SpecFact interpreter. Explicit selection SHALL take precedence over unambiguous project discovery. It SHALL preserve project Python constraints and report ambiguity or unavailable interpreters without substituting the controller Python.

#### Scenario: Different controller and project versions
- **GIVEN** SpecFact runs through pipx or uvx using a different Python from the project
- **WHEN** review resolves the selected project environment
- **THEN** project imports and commands use the selected interpreter and the report records both identities

#### Scenario: Ambiguous or missing interpreter
- **GIVEN** multiple environments match or the required project interpreter is absent
- **WHEN** inspection resolves the project
- **THEN** it names the candidates or missing version and performs no installation or controller-Python fallback

#### Scenario: Absolute native Hatch Python declaration
- **GIVEN** a detached Hatch environment declares an absolute Python executable, optionally alongside a compatible .python-version
- **WHEN** pure inspection records the declarations and preparation selects an existing or cold environment
- **THEN** preparation probes the declared executable and validates the selected target's base interpreter and full version without rejecting the absolute path as a numeric version
- **AND** cold preparation uses the declared absolute executable before numeric discovery when no caller override is supplied
- **AND** conflicting numeric declaration components or incompatible actual interpreter facts fail with a diagnostic
- **AND** numeric declarations for an existing target do not require a separate host Python lookup

### Requirement: Faithful external sidecar preparation
Preparation SHALL use native pip or pip-tools, Hatch, uv, or Poetry semantics in SpecFact-owned external storage. It SHALL preserve locks, constraints, markers, selected groups and extras, editable behavior, local or VCS origins, build hooks, generated sources, and entrypoints. Existing customer environments SHALL remain execution targets without SpecFact package installation.

#### Scenario: First detached Hatch workflow
- **GIVEN** the existing detached Hatch fixture has an explicitly selected review environment and a compatible project Python different from the CLI
- **WHEN** review uses an existing environment and then prepares the same project from a cold state
- **THEN** both execute the selected project command, native pytest plugin, entrypoint and dependency imports with unchanged project declarations and customer environment inventory

#### Scenario: Existing Hatch execution does not synchronize dependencies
- **GIVEN** a selected existing Hatch environment has a verified compatible project interpreter and installed project dependencies
- **WHEN** preparation selects it and a project command executes
- **THEN** execution uses that environment without invoking dependency synchronization or installing SpecFact or analyzer packages
- **AND** the environment package inventory and project declarations remain unchanged

#### Scenario: Cold Hatch state stays outside the project
- **GIVEN** the selected detached Hatch environment does not exist and the required project interpreter and Hatch executable are available
- **WHEN** preparation creates the environment in SpecFact-owned external storage
- **THEN** native Hatch consumes the selected environment's declared dependencies using that interpreter
- **AND** the service does not inject SpecFact dependencies, rewrite project declarations or locks, or publish an interrupted preparation as ready
- **AND** source-only checks can retain their own results when required dynamic preparation fails

#### Scenario: Locked manager preparation
- **GIVEN** a project supplies a manager lock or pip requirements and constraints
- **WHEN** its selected adapter prepares an external environment
- **THEN** the native manager consumes the selected inputs without rewriting locks, weakening constraints, or replacing manager semantics with a generic pip install

#### Scenario: Unlocked project resolution
- **GIVEN** the project deliberately supplies no lock but supplies valid dependency declarations
- **WHEN** preparation resolves that declared project using its selected manager
- **THEN** the resulting dependency and origin identities are recorded externally and no lock or constraints are written into the customer project

#### Scenario: Native Hatch storage selection survives controller isolation
- **GIVEN** a trusted project has an existing detached Hatch environment in customer-selected HATCH_DATA_DIR and HATCH_CACHE_DIR storage
- **WHEN** preparation discovers the environment while the controller carries unrelated active-environment and interpreter settings
- **THEN** native discovery uses the selected customer storage and project root without inheriting the controller environment selection or creating a replacement environment

### Requirement: Single project execution owner
specfact_codebase.project_runtime SHALL own inspection, preparation, and project command execution. Code Review and existing framework sidecar validation SHALL consume this service without a reverse dependency on Code Review. Commands SHALL bind argv, working directory, environment overrides, and a timeout.

#### Scenario: Existing sidecar consumes project context
- **GIVEN** framework sidecar validation needs a project interpreter and dependencies
- **WHEN** it prepares and executes a project command
- **THEN** it uses the shared service without separately installing unpinned analyzer or framework packages into the customer environment

#### Scenario: Manager scripts and workspace roots
- **GIVEN** the project uses manager scripts, a monorepo member, or a source layout
- **WHEN** a named check executes
- **THEN** the chosen working directory, manager environment, script expansion and import roots match the project context rather than a controller heuristic

### Requirement: Preparation failure and reuse are explicit
Preparation SHALL distinguish ready context from structured failure. Reuse SHALL require matching source and configuration inputs. It SHALL never publish partial preparation or retry a failed locked installation with relaxed constraints. Credentials SHALL not enter persisted reports or environment metadata.

#### Scenario: Missing native library or credentials
- **GIVEN** the manager cannot install or import a dependency because a native library, private index credential, or network route is missing
- **WHEN** preparation fails
- **THEN** the failure names the affected capability and remedy, preserves independent static findings, and leaves required dynamic checks incomplete

#### Scenario: Interrupted or stale preparation
- **GIVEN** a previous preparation was interrupted or its project inputs changed
- **WHEN** another invocation attempts reuse
- **THEN** the partial or stale context is not treated as ready and a fresh owned preparation can proceed without modifying customer inputs

#### Scenario: Unreadable execution identity fails structurally
- **GIVEN** a prepared project has a source or configuration file that cannot be read
- **WHEN** execution fingerprints the project before or after running a command
- **THEN** it returns execution_failed with the read diagnostic rather than raising an exception or claiming a verified unreadable identity
- **AND** a failure before execution does not run the command, while a failure after execution preserves captured stdout and stderr alongside a visible diagnostic
- **AND** combined stderr remains bounded and reports truncation when needed

#### Scenario: Cleanup failure preserves the preparation failure
- **GIVEN** preparation fails after creating its invocation-owned workspace
- **WHEN** removing the incomplete workspace also fails
- **THEN** preparation returns its original structured failure and identifies the retained workspace and cleanup error in the remedy
- **AND** it requires a fresh workspace for another preparation attempt

### Requirement: Portable inspection and bootstrap commands
code review runtime inspect SHALL remain read-only and runtime prepare SHALL initialize external sidecar state. Ordinary review SHALL prepare missing context automatically. Python and platform capability SHALL be evaluated independently of capsule ABI or architecture catalogs.

#### Scenario: Inspection has no project side effects
- **GIVEN** a supported project has not been bootstrapped
- **WHEN** runtime inspect runs
- **THEN** it reports selected inputs and ambiguities without creating environments or importing project setup code

#### Scenario: Existing descriptor option is not reinterpreted
- **GIVEN** a caller supplies the legacy --project-runtime descriptor option
- **WHEN** the replacement command parses it
- **THEN** it either reads an explicitly supported versioned local descriptor or returns a migration diagnostic, and never silently treats the descriptor path as an interpreter executable

#### Scenario: Unreadable inspection identity remains diagnostic
- **GIVEN** a project declaration selected for fingerprinting cannot be read
- **WHEN** inspection runs
- **THEN** the plan contains a diagnostic and no invented input identity, and preparation rejects the plan before querying Hatch

#### Scenario: Custom global Hatch configuration is explicitly unsupported
- **GIVEN** HATCH_CONFIG selects a custom global configuration that can alter native project context
- **WHEN** this first detached Hatch milestone inspects or prepares the project, including a changed selection after inspection
- **THEN** it reports that custom global configuration is unsupported before native queries rather than silently ignoring the selection

### Requirement: First Hatch delivery review handoff
For delivery verification of the first Hatch milestone, the approved local ARM64 Darwin feature-worktree exception SHALL recognize staged portable-runtime fixture changes that already schedule the blocking capsule workflow. It SHALL defer only capsule review and retain the existing platform, CI, branch, worktree, indexed workflow, independent job and candidate guards. All other Block 2 checks SHALL still execute. This requirement covers delivery verification only and does not claim public runtime CLI adoption or completion of change 17.

#### Scenario: Staged portable runtime fixture schedules mandatory review
- **GIVEN** an approved local ARM64 Darwin feature worktree with both required indexed review jobs and a staged portable-runtime fixture change
- **WHEN** Block 2 runs with the GitHub Linux review exception
- **THEN** capsule review reports DEFERRED rather than PASS and all other Block 2 checks and contracts execute
- **AND** exact-head hosted review remains mandatory before merge

#### Scenario: Unstaged fixture cannot authorize deferral
- **GIVEN** only the working tree contains the portable-runtime fixture change and no indexed candidate path schedules capsule review
- **WHEN** Block 2 requests the exception
- **THEN** it rejects deferral with the candidate scheduling diagnostic

#### Scenario: Indexed independent review remains mandatory
- **GIVEN** a staged portable-runtime fixture change but the indexed workflow lacks the independent signed-review job
- **WHEN** Block 2 requests the exception
- **THEN** it rejects deferral with the missing independent review diagnostic

#### Scenario: Local native proof preconditions precede allocation
- **GIVEN** the local native Hatch proof relies on executable assertions and a Python 3.12 controller
- **WHEN** it is invoked with optimized Python or another controller version
- **THEN** it refuses with an explicit diagnostic before creating the proof workspace or receipt
- **AND** the local proof remains development evidence rather than release or protected CI authority
