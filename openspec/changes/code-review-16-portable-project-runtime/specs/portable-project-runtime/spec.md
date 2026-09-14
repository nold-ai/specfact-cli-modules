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

#### Scenario: Source changes during full or explicit-file analysis
- **GIVEN** a local project runtime was prepared successfully
- **WHEN** source, dependency inputs, or VCS version metadata change during analysis
- **THEN** the final runtime binding is incomplete for every dependency-sensitive member
- **AND** unchanged artifact bytes alone cannot authorize a passing source binding

#### Scenario: Hatch-declared pytest arguments
- **GIVEN** the selected native Hatch environment declares extra pytest arguments
- **WHEN** runtime preparation exports that environment
- **THEN** those arguments are retained in the runtime inventory and target pytest invocation
- **AND** explicit or disabled plugin options participate in duplicate-registration prevention

#### Scenario: Isolated xdist workers retain pytest coordination
- **GIVEN** repository pytest configuration requests xdist workers and coverage
- **WHEN** child Python processes enter fresh target namespaces
- **THEN** they retain the pytest member's dependency domain and use private coverage storage
- **AND** unrelated analyzers do not inherit that pytest domain
- **AND** worker startup failures are retained in incomplete execution evidence

#### Scenario: Analyzer package introspection respects member boundaries
- **WHEN** a member discovers its bundled checkers through filesystem-to-module lookup
- **THEN** its verified dependency closure is visible as a real import directory
- **AND** unrelated sealed packages are absent from that directory and its metadata inventory

#### Scenario: Invalid and stale runtime state fails explicitly
- **WHEN** a supplied descriptor has invalid inventory types, preparation races with another publisher, or a pytest child fails before writing evidence
- **THEN** malformed descriptors and stale observations cannot become completed evidence
- **AND** a valid concurrent cache winner is verified and reused

#### Scenario: Python startup controls cannot bypass runtime attachment
- **WHEN** a project invokes Python with an option that disables mandatory runtime bootstrap
- **THEN** execution rejects that exact option with a runtime diagnostic

#### Scenario: Review selection and candidate policies survive normalization
- **WHEN** review focus is normalized or a portable range adds referenced policy files
- **THEN** explicit runtime paths and both candidate and target policy closures remain bound to the review

#### Scenario: Source aliases cannot bypass build exclusions
- **WHEN** a source link resolves into an excluded file, directory, descendant, or Git configuration
- **THEN** discovery and copying reject it before any network-enabled build hook runs
- **AND** valid included file and directory links remain inside the copied source with their target bytes bound before building

#### Scenario: Unlocked pip-tools and legacy package metadata
- **WHEN** a repository has requirements.in without a compiled requirements.txt, or static setup.cfg Python constraints
- **THEN** discovery imports those inputs and pip prepares the selected dependencies without writing into the checkout
- **AND** a compiled requirements.txt takes precedence when both pip-tools inputs exist

#### Scenario: Optional test dependencies are selected without combining alternatives
- **WHEN** a project declares one test extra and no selected test group
- **THEN** automatic preparation selects that extra
- **AND** conflicting test extras or group/extra alternatives require explicit selection

#### Scenario: Executable source changes invalidate reuse
- **WHEN** an included source file changes executable mode without changing bytes
- **THEN** source identity and runtime reuse change with it

#### Scenario: Corpus acquisition cost is measured transparently
- **WHEN** the Linux corpus runs dependency acquisition and analysis commands
- **THEN** evidence records wall time, artifact bytes, and non-loopback host network byte deltas
- **AND** network counters are labelled as host-wide observations rather than exact package-payload transfer sizes

#### Scenario: Recorded member dependency closure is complete
- **WHEN** a required distribution is missing from both project inventory and sealed analyzer inventory
- **THEN** preparation reports the member and missing distribution rather than silently omitting the dependency edge
- **AND** genuinely undeclared project imports remain ordinary analyzer findings after successful preparation

#### Scenario: Analysis workers cannot read excluded checkout files
- **WHEN** an ordinary checkout contains excluded environment files or a local virtual environment
- **THEN** portable analyzers receive a verified private source copy with those exclusions applied
- **AND** selected included source bytes and configuration remain identical to the bound source snapshot

#### Scenario: Cached enforcement retains staged VCS context
- **WHEN** a changed-enforcement review materializes the staged index of a dynamically versioned project
- **THEN** discovery receives its repository and index context so preparation preserves sanitized VCS facts

#### Scenario: Partial pytest execution cannot hide collection or internal errors
- **WHEN** tests execute or fail alongside collection or internal errors
- **THEN** known failures remain visible and required test evidence remains incomplete

#### Scenario: Runtime descriptors and native binaries match their execution domain
- **WHEN** a descriptor has invalid pytest argument types or an ELF artifact targets another machine architecture
- **THEN** validation rejects the artifact with a precise diagnostic before worker execution

#### Scenario: Independent offline corpus proof
- **GIVEN** a cold external review has populated the verified cache
- **WHEN** the corpus repeats preparation and explicit attachment
- **THEN** both commands execute as a non-root user in a network namespace with no active non-loopback interfaces, and the evidence records this isolation separately from the offline option

#### Scenario: Controlled defect evidence remains separate
- **GIVEN** an untouched upstream review and a disposable copy with injected defects
- **WHEN** the corpus analyzes both
- **THEN** their reports have distinct artifact names and the controlled report proves actual failing tests and static detection

#### Scenario: Offline wrapper preserves ordinary process devices
- **GIVEN** warm validation runs inside a non-root user and network namespace
- **WHEN** the customer CLI or Git opens /dev/null
- **THEN** a private device filesystem supports ordinary subprocess execution without exposing host devices or external networking

#### Scenario: Disabled pytest metadata autoload
- **GIVEN** project or selected environment options disable plugin autoload
- **WHEN** the worker constructs pytest arguments
- **THEN** it does not synthesize installed third-party entry points, preserves explicit plugin choices, and loads required coverage only once unless explicitly disabled

#### Scenario: Directory-sensitive runtime identity
- **GIVEN** a cached runtime whose build can inspect directory existence and permissions
- **WHEN** an included directory is added, removed, or changes mode
- **THEN** source identity and cache reuse reflect that change, including the root directory mode

#### Scenario: Pip lock and source requirements conflict
- **GIVEN** pylock.toml and either requirements.txt or requirements.in without explicit selection
- **WHEN** discovery runs
- **THEN** one diagnostic names all competing inputs and requests explicit configuration

#### Scenario: Invalid INI remains an actionable preparation failure
- **GIVEN** malformed setup.cfg or pytest INI configuration
- **WHEN** discovery reads the configuration
- **THEN** ProjectRuntimeError identifies the affected file and review retains independent findings with incomplete runtime evidence

#### Scenario: Protected offline test launcher
- **GIVEN** customer code has run before the offline validation step
- **WHEN** the corpus selects its namespace launcher
- **THEN** only the expected regular executable under a root-owned non-writable directory is accepted, with its bytes matching an administrator-owned digest record; writable, substituted, symlinked, or mismatched launchers are rejected before execution

#### Scenario: Relative customer file selections enter the private source copy
- **WHEN** an ordinary review selects repository-relative source and test paths
- **THEN** the private analysis copy SHALL preserve those selections as paths within the copied repository
- **AND** equivalent absolute selections SHALL resolve to the same files
- **AND** a selection escaping the repository SHALL be rejected before analyzer execution.

#### Scenario: Git HTTPS dependencies are acquired in the disposable builder
- **WHEN** dependencies use Git HTTPS transport, including a source tree without Git metadata
- **THEN** preparation SHALL provide the Git executable and HTTP/HTTPS transport helpers with their native dependencies and an explicit private Git exec path
- **AND** helper identities SHALL participate in cache reuse.

#### Scenario: A selected pytest dependency violates an analyzer requirement
- **WHEN** a selected project distribution violates an active worker dependency specifier
- **THEN** preparation SHALL report the domain, dependency, selected version and required specifier before sealing the runtime
- **AND** independent static analysis SHALL remain available without silently replacing the project version.

#### Scenario: Analyzer source mounts exclude Git history
- **WHEN** an ordinary worktree is copied for analyzer execution
- **THEN** its source mount SHALL exclude Git metadata and historical objects
- **AND** the separate disposable build copy SHALL retain sanitized VCS context for dynamic package versions.

#### Scenario: Pytest configuration leaves discovery roots unspecified
- **WHEN** pytest testpaths is absent or empty
- **THEN** full review SHALL use the repository root as pytest's native default
- **AND** explicit source review SHALL discover corresponding root-level tests.

#### Scenario: Git identity probing fails before cache lookup
- **WHEN** Git exec-path discovery fails, times out or cannot execute
- **THEN** preparation SHALL raise a precise ProjectRuntimeError with the original exception chained
- **AND** review SHALL retain the existing incomplete-runtime diagnostic path.

#### Scenario: Hosted runner has writable optional-tool directories
- **WHEN** a hosted runner exposes a customer-writable `/opt` ancestor
- **THEN** the offline corpus launcher SHALL be provisioned outside that ancestor
- **AND** all launcher ownership and ancestor permission checks SHALL remain enforced.

#### Scenario: Source package is named venv
- **WHEN** a repository contains a legitimate package directory named `venv` without a virtual-environment marker
- **THEN** source identity and both build/analysis copies SHALL retain that package
- **AND** actual environments identified by `pyvenv.cfg` SHALL remain excluded regardless of directory name
- **AND** symlink aliases SHALL not expose excluded environment contents.

#### Scenario: Default test discovery encounters an existing environment
- **WHEN** repository-root test discovery encounters tests inside an excluded virtual environment
- **THEN** those installed dependency tests SHALL not create ambiguity or enter the customer test selection
- **AND** discovery SHALL prune excluded environment directories before traversal.

#### Scenario: Runtime preparation fails before independent static analysis
- **WHEN** discovery or preparation fails and independent static members remain applicable
- **THEN** those members SHALL receive the same sanitized private source copy as successful preparation
- **AND** if that copy cannot be established safely, no analyzer SHALL receive the original source and required evidence SHALL remain incomplete.

#### Scenario: Poetry constrains the effective Python runtime
- **WHEN** Poetry declares its Python constraint in tool.poetry.dependencies.python
- **THEN** discovery SHALL import that constraint and intersect it with PEP621 requires-python when both are declared
- **AND** unsupported manager-specific constraint syntax SHALL identify the exact declaration and remedy rather than be ignored or passed unmodified to a PEP440 interpreter selector.

#### Scenario: Non-pip manager receives explicit pip dependency inputs
- **WHEN** explicit project configuration supplies requirements or constraints for uv, Hatch or Poetry
- **THEN** discovery and adapter dispatch SHALL reject unsupported fields with the selected manager and a remedy before installation
- **AND** unrelated exported requirements files SHALL not override native manager configuration.

#### Scenario: Source-only pytest selection respects recursion exclusions
- **WHEN** matching test discovery traverses the repository root
- **THEN** pytest's default norecursedirs exclusions SHALL be retained when unspecified
- **AND** explicit norecursedirs configuration SHALL replace those defaults consistently with native pytest.

#### Scenario: Pytest deselection preserves the executed selection inventory
- **GIVEN** repository pytest options select a subset with `-k` or `--deselect`
- **WHEN** the isolated worker collects and executes that selection
- **THEN** its required execution inventory contains the final selected items, deselected items do not become false unexecuted evidence, and actual selected failures or interrupted execution remain visible, including distributed execution.

#### Scenario: Immutable portable snapshots retain safe tracked project links
- **GIVEN** an immutable Git snapshot contains tracked package or data symlinks needed by the project runtime
- **WHEN** portable discovery and preparation materialize that snapshot
- **THEN** safe in-snapshot links remain available with their original targets, while escaping or excluded-source aliases fail closed and existing governed-Python symlink restrictions remain enforced.

#### Scenario: Invalid pytest path options preserve static fallback
- **GIVEN** a supported pytest configuration declares `pythonpath` or `testpaths` with a value other than a string or list of strings
- **WHEN** runtime discovery consumes that configuration
- **THEN** it returns a project-runtime diagnostic naming the option and source configuration, and ordinary review retains independent static evidence without an uncaught type error.

#### Scenario: Staged snapshots retain their captured Git tree
- **GIVEN** an index review captures a staged tree that differs from HEAD
- **WHEN** its portable project runtime records VCS identity and prepares a private build copy
- **THEN** the descriptor and cache identity SHALL bind the captured tree separately from the HEAD commit
- **AND** the private Git index SHALL be populated from that captured tree while HEAD remains the selected commit
- **AND** staged-only paths and renames SHALL remain visible to Git-aware build hooks without reading the mutable live index.

#### Scenario: Plain dependency preparation does not require unused Git capabilities
- **GIVEN** a plain project uses package-index dependencies without VCS context
- **WHEN** Git or its HTTP transport helpers are unavailable on the builder
- **THEN** preparation SHALL stage and fingerprint only available Git capabilities and SHALL permit ordinary dependency installation
- **AND** an actual acquisition requiring an unavailable Git capability SHALL retain the package manager failure and an actionable remedy rather than claim successful preparation.

#### Scenario: Malformed pytest tables preserve runtime diagnostics
- **GIVEN** a pytest TOML file or pyproject declares its pytest or ini_options section as a scalar or array
- **WHEN** discovery selects that configuration
- **THEN** it SHALL reject the malformed table with the source filename and section path before converting or reading options
- **AND** ordinary review SHALL retain independent static findings and incomplete dependency-sensitive evidence.

#### Scenario: Index policy discovery fails after snapshot materialization
- **GIVEN** both immutable index snapshots have been created
- **WHEN** changed-path, policy, or manifest discovery raises before ownership is returned
- **THEN** both temporary snapshot roots SHALL be removed and the existing scope failure diagnostic SHALL remain intact.

#### Scenario: Private build Git metadata contains only identity-bound objects
- **GIVEN** a source repository also contains unrelated branches, remote refs, or unreachable objects
- **WHEN** portable preparation copies Git context
- **THEN** the private repository SHALL contain only the reachable object closure bound by the selected commit, captured index tree, declared tags, and shallow boundary
- **AND** selected ancestry, SCM tags, and detached staged objects SHALL remain available without unrelated refs or object storage.

#### Scenario: Analyzer-owned dependencies precede project imports during startup
- **GIVEN** a member dependency graph records a package as analyzer-owned and the snapshot or target site-packages contains an import with the same name
- **WHEN** the member configures its runtime, including imports executed by target `.pth` files
- **THEN** the analyzer-owned package and its submodules SHALL resolve only from the verified member analyzer root before ordinary path lookup can select project code
- **AND** invalid or unavailable sealed origins SHALL fail closed rather than fall back to project code
- **AND** graph entries owned by the project and ordinary project-Python execution SHALL retain project import behavior.

#### Scenario: Discovery validates consumed metadata tables before selection
- **GIVEN** pyproject or Hatch metadata declares a table consumed by discovery as a scalar or array
- **WHEN** discovery parses metadata, including with an explicit manager selection
- **THEN** it SHALL reject the malformed table before selection or constraint processing with a project-runtime diagnostic naming the source file and table path
- **AND** ordinary review SHALL preserve independent static findings and mark dependency-sensitive evidence incomplete.

#### Scenario: Index manifests retain unchanged referenced policy evidence without widening selection
- **GIVEN** an index snapshot whose Ruff or basedpyright policy transitively references unchanged regular files
- **WHEN** index scope resolution constructs its input evidence
- **THEN** head and base input manifests SHALL retain the resolved policy closure identities in addition to selected changed paths
- **AND** selected_paths SHALL remain limited to changed governed inputs, preserving NOT_APPLICABLE/no_governed_impact for an unchanged index.

#### Scenario: Bound Git metadata disappears during preparation
- **GIVEN** a runtime plan records nonempty Git provenance
- **WHEN** the bound repository loses its Git metadata after input verification
- **THEN** preparation SHALL fail before dependency acquisition instead of silently omitting that provenance
- **AND** intentionally metadata-free immutable source copies SHALL use their separately bound repository for Git export.

#### Scenario: Targeted pytest evidence preserves parameter identities
- **GIVEN** selected pytest functions or class methods have parameter identifiers containing `::` or brackets
- **WHEN** targeted review reconciles collection, execution, JUnit, and process evidence
- **THEN** parameter text SHALL remain part of the test name rather than become a module or class qualifier
- **AND** complete passing selections SHALL reconcile as PASS while missing execution and conflicting outcomes remain incomplete evidence.

#### Scenario: Python-version-only projects attach their declared runtime automatically

- **GIVEN** a source repository declares its Python interpreter only through a root `.python-version` file, without packaging or dependency metadata
- **WHEN** an ordinary capsule review selects source files without explicit project-runtime options
- **THEN** review MUST discover and prepare the portable project runtime using the declared interpreter before dependency-sensitive analysis
- **AND** an unsupported declared interpreter MUST retain independent static analysis while marking runtime-dependent evidence incomplete with an actionable runtime diagnostic
- **AND** an otherwise equivalent source-only repository without `.python-version` or other project metadata MUST retain the existing standard-library review path

#### Scenario: Quoted pytest paths retain native argument boundaries
- **GIVEN** repository INI-style pytest options contain quoted test paths, source paths, or file patterns with spaces
- **WHEN** portable runtime discovery and test selection import those options
- **THEN** string values follow pytest argument quoting rules and array values retain their declared boundaries
- **AND** full and source-only review select the same real tests as native pytest
- **AND** malformed quoting identifies the configuration option through an actionable runtime diagnostic

#### Scenario: Executable project startup preserves the member import boundary
- **GIVEN** target site initialization processes executable `.pth` files, including ordinary editable-install and setuptools startup hooks
- **WHEN** an analyzer member finishes site initialization
- **THEN** its validated member finder SHALL regain first lookup precedence while legitimate additive project finders and rebased workspace paths remain available
- **AND** removal or mutation of protected finders or import machinery, or added paths outside the target and verified runtime roots, SHALL produce an explicit startup diagnostic before member execution
- **AND** project-Python startup SHALL retain native `.pth` behavior; these integrity checks SHALL NOT be described as a sandbox for arbitrary malicious code in the same interpreter.

#### Scenario: uv manager signals require a valid table
- **GIVEN** pyproject metadata contains a scalar or array `tool.uv` value
- **WHEN** discovery validates manager signals, including with explicit manager selection
- **THEN** it SHALL reject the value before selection with the precise `project_config_invalid:pyproject.toml:tool.uv` table diagnostic

#### Scenario: Analyzer import ownership follows its installed payload

- **GIVEN** an analyzer distribution has missing or stale `top_level.txt` metadata, including names for build directories absent from its installed payload
- **WHEN** review constructs a member's sealed dependency graph
- **THEN** sealed import names MUST be derived from that distribution's recorded, present Python module, package, namespace, or native-extension payload, independently of the supervisor Python ABI
- **AND** a directory installed by another distribution MUST NOT establish ownership for a stale declared name
- **AND** a project-owned package sharing a stale name MUST remain importable in the project domain while actual analyzer imports retain strict origin enforcement
- **AND** unavailable distribution file inventory MUST produce an explicit analyzer inventory diagnostic instead of trusting unverified declarations
- **AND** changes to import-ownership logic MUST invalidate cached runtime preparation through the existing builder source identity

#### Scenario: Portable range selection preserves absent Python paths
- **GIVEN** a portable range or index review selects Python paths added or deleted between its immutable snapshots
- **WHEN** one side has no surviving selected Python file
- **THEN** that side SHALL retain an empty Python analysis selection rather than expand to unrelated source files
- **AND** findings from unrelated unchanged files SHALL NOT become introduced or fixed because only one side analyzed them
- **AND** a nonempty metadata-only selection SHALL retain symmetric whole-source analysis, while an empty overall selection SHALL remain empty.

#### Scenario: Containment applies to parsed pytest search paths

- **GIVEN** repository pytest configuration supplies quoted `testpaths` or `pythonpath` values containing spaces
- **WHEN** portable runtime discovery validates repository paths
- **THEN** it MUST apply containment and symlink checks to the same shell-parsed values that pytest and portable test selection consume
- **AND** quoted parent traversal, absolute paths, and escaping symlink paths MUST fail before preparation or selection
- **AND** explicit review `source_roots` MUST NOT suppress validation of pytest's own `pythonpath`
- **AND** valid repository-relative paths containing spaces and native list values MUST remain unchanged in recorded configuration

#### Scenario: Unborn Git repositories have no version context

- **GIVEN** a newly initialized Git repository has a valid symbolic HEAD pointing to an absent branch and no first commit
- **WHEN** runtime discovery or inspection gathers optional VCS version context without requesting an explicit revision
- **THEN** it SHALL return empty VCS context and permit ordinary dependency discovery and preparation
- **AND** missing explicit revisions, detached or malformed HEAD state, and corrupt repositories SHALL remain precise diagnostics rather than being silently treated as unborn repositories

#### Scenario: Runtime attachment preserves installed-package import precedence

- **GIVEN** a project has a built package installed in its selected runtime and raw source under `src/`, with no declared pytest `pythonpath` or explicit review `source_roots`
- **WHEN** the capsule attaches the runtime and executes the project's tests
- **THEN** attachment SHALL NOT invent `src` or repository-root import overrides
- **AND** native pytest import/configuration behavior SHALL select the installed package, including build-generated package contents, while source-file analysis remains available
- **AND** explicitly configured review `source_roots`, pytest `pythonpath`, and installed editable hooks SHALL retain their declared import behavior
- **AND** native Python CLI current-directory and script-path behavior, and pytest's own test-module path handling, SHALL remain effective for uninstalled source-only repositories
