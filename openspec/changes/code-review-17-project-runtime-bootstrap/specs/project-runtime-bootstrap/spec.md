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

### Requirement: Faithful external sidecar preparation
Preparation SHALL use native pip or pip-tools, Hatch, uv, or Poetry semantics in SpecFact-owned external storage. It SHALL preserve locks, constraints, markers, selected groups and extras, editable behavior, local or VCS origins, build hooks, generated sources, and entrypoints. Existing customer environments SHALL remain execution targets without SpecFact package installation.

#### Scenario: First detached Hatch workflow
- **GIVEN** the existing detached Hatch fixture has an explicitly selected review environment and a compatible project Python different from the CLI
- **WHEN** review uses an existing environment and then prepares the same project from a cold state
- **THEN** both execute the selected project command, native pytest plugin, entrypoint and dependency imports with unchanged project declarations and customer environment inventory

#### Scenario: Locked manager preparation
- **GIVEN** a project supplies a manager lock or pip requirements and constraints
- **WHEN** its selected adapter prepares an external environment
- **THEN** the native manager consumes the selected inputs without rewriting locks, weakening constraints, or replacing manager semantics with a generic pip install

#### Scenario: Unlocked project resolution
- **GIVEN** the project deliberately supplies no lock but supplies valid dependency declarations
- **WHEN** preparation resolves that declared project using its selected manager
- **THEN** the resulting dependency and origin identities are recorded externally and no lock or constraints are written into the customer project

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
