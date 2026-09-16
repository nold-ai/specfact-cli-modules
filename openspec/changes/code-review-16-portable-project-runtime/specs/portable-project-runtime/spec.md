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

#### Scenario: Verified activation survives an immutable index snapshot
- **GIVEN** a verified active repository environment and an independently materialized index or revision snapshot
- **WHEN** automatic runtime discovery reviews that snapshot
- **THEN** activation is verified against the controller-owned original repository while all dependency inputs, configuration and source identity come from the snapshot
- **AND** explicit project configuration wins, unrelated or spoofed activation is ignored, and an active environment absent from the selected snapshot is diagnosed rather than substituted

#### Scenario: Verified implicit Hatch default activation
- **GIVEN** Hatch's implicit default environment exists while only custom environments are explicitly declared
- **AND** the running interpreter has verified repository-local default activation
- **WHEN** discovering the live project, an index snapshot or an immutable revision
- **THEN** default is selected without requiring an explicit default table, using dependency bytes from the selected source
- **AND** explicit environment-only configuration wins, unrelated activation remains invalid and absent named custom environments still fail

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

#### Scenario: Structured Semgrep failures retain bounded diagnostic context
- **GIVEN** either required Semgrep pass returns a nonempty structured errors list
- **WHEN** capsule review reports incomplete analysis
- **THEN** its tool error retains the total error count and at most the first three errors' scalar type, code and message fields, with strings bounded to 512 characters, JSON-escaped controls and a 4000-character total bound
- **AND** omitted errors are identified, arbitrary fields, nested objects and source snippets are excluded, and analysis remains UNKNOWN
- **AND** diagnostic messages may contain reviewed-source text under the existing bounded-stderr policy; no universal secret-redaction claim is made

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

#### Scenario: Portable pytest preserves non-passing outcomes

- **GIVEN** a portable suite contains a passing call and a skipped, XFAIL, non-strict XPASS, or failed selected test
- **WHEN** the capsule evaluates the observed phases
- **THEN** it SHALL emit a blocking `TEST_OUTCOME_NOT_PASS` finding for every non-passing observed test outcome
- **AND** intentional skips SHALL remain terminal observations without inventing executed call phases
- **AND** genuine non-pass findings SHALL remain visible alongside incomplete execution diagnostics

#### Scenario: Portable coverage validates each reviewed production source

- **GIVEN** a portable suite completes and produces a coverage document
- **WHEN** the capsule evaluates reviewed production Python files
- **THEN** every applicable reviewed source SHALL have coverage evidence, and absent evidence SHALL mark analysis incomplete
- **AND** measured coverage below the greater of the established 80 percent floor and the effective project threshold SHALL emit blocking `TEST_COVERAGE_LOW` findings
- **AND** unrelated covered files SHALL NOT satisfy another source file's coverage requirement
- **AND** actual selected test modules, conventional test support directories, conftest files and type stubs SHALL NOT be treated as production coverage targets
- **AND** source initializers SHALL retain only the established empty-initializer exemption, without assuming SpecFact's own omit policy applies to customers

#### Scenario: Native pytest roots do not redefine production sources

- **GIVEN** pytest selects a nested configuration root or uses a package directory as its test-discovery root
- **WHEN** the capsule maps observed node identifiers and determines production coverage targets
- **THEN** it SHALL resolve raw node identifiers against pytest's actual root inside the source snapshot
- **AND** it SHALL reject an observed pytest root outside the snapshot with an explicit incomplete-evidence diagnostic
- **AND** a discovery root containing production modules SHALL NOT exempt those modules from coverage requirements

#### Scenario: Nested pytest outcome findings identify snapshot files

- **GIVEN** pytest reports a non-passing node identifier relative to a contained nested pytest root
- **WHEN** the portable adapter creates a review finding
- **THEN** the finding file SHALL identify the actual snapshot-relative test path while the native node identifier remains unchanged in observed evidence and diagnostic text
- **AND** absolute or escaping pytest roots outside the snapshot SHALL produce incomplete-evidence diagnostics before outcome paths are mapped
- **AND** an escaping observed node path SHALL NOT create a finding attributed outside the snapshot

#### Scenario: Pytest startup failure preserves recorded execution

- **GIVEN** native pytest exits with a usage error before session finish and records no pytest root or test outcomes
- **WHEN** the portable adapter evaluates the observation
- **THEN** it SHALL retain the targeted pytest member identity, the original target execution record and an actionable configuration diagnostic naming the native exit code
- **AND** it SHALL NOT invent a root or attempt outcome-path mapping for absent outcomes
- **AND** otherwise usable observations with null, empty or non-string roots SHALL return an explicit incomplete-evidence diagnostic instead of an uncaught adapter exception

#### Scenario: Reviewer instrumentation does not activate a native aggregate coverage gate
- **GIVEN** the effective native pytest invocation does not enable pytest-cov and does not explicitly disable coverage
- **WHEN** the capsule obtains required reviewer coverage evidence
- **THEN** it SHALL use a separately identified reviewer-owned collector while preserving the native pytest exit and the configured coverage threshold value
- **AND** it SHALL enforce the existing per-reviewed-source floor of the greater of 80 percent and the effective configured threshold
- **AND** native Coverage source, source_pkgs, source_dirs, include and omit semantics SHALL remain authoritative; default scope may include only the snapshot and controller-verified installed directories when no such configuration is present
- **AND** excluded or missing reviewed sources SHALL remain incomplete rather than receive synthesized coverage.

#### Scenario: Explicit native coverage policy retains its outcome and report destinations
- **GIVEN** native pytest configuration or arguments enable pytest-cov
- **WHEN** the capsule observes coverage
- **THEN** it SHALL preserve effective source, reset, configuration path, report destination, report-disable, threshold, precision, no-cov and no-cov-on-fail controls without appending overriding coverage options
- **AND** private review evidence SHALL be exported separately through the finished native Coverage object without replacing requested reports
- **AND** an actual native aggregate threshold failure SHALL remain a blocking coverage-policy finding with the observed total, threshold and precision rather than an unexplained missing-test failure
- **AND** explicit coverage disabling or failure-driven report suppression SHALL leave required reviewer evidence incomplete.

#### Scenario: Reviewer collection preserves distributed and subprocess evidence
- **GIVEN** native pytest uses xdist or configured Coverage subprocess support
- **WHEN** reviewer-only instrumentation is active
- **THEN** the verified target-only plugin SHALL use the supported pytest-cov lifecycle and worker transfer without adding customer imports to the supervisor or double tracing an active native collector
- **AND** the report SHALL retain instrumentation provenance, effective run/report configuration, and actual collection/execution outcomes
- **AND** an unsupported plugin contract or missing worker coverage SHALL produce an actionable incomplete-evidence diagnostic.

#### Scenario: Installed project source receives authenticated coverage attribution

- **GIVEN** the native package manager installs a non-editable local project and its tests execute the installed package rather than the reviewed source path
- **WHEN** the sealed controller prepares targeted coverage
- **THEN** it SHALL preserve installed-package import precedence and use the sealed distribution's local origin and RECORD ownership to select installed coverage directories
- **AND** it SHALL attribute an actual installed coverage row to a reviewed file only when the full package-relative path has one snapshot match and both files have identical verified content before and after execution
- **AND** it SHALL retain the original native coverage paths and explicit attribution evidence without inventing executed lines or changing native pytest configuration
- **AND** native low coverage and failing test outcomes SHALL remain failing evidence

#### Scenario: Installed coverage cannot credit unrelated or changed source

- **GIVEN** installed source differs from the snapshot, has ambiguous source or distribution ownership, invalid RECORD hashes, unsafe paths, or shares its only coverage directory with a foreign distribution
- **WHEN** coverage is attributed to reviewed source
- **THEN** affected files SHALL receive an actionable incomplete-evidence diagnostic and SHALL NOT receive guessed coverage
- **AND** generated or transformed code SHALL retain its native runtime behavior without claiming line equivalence to different source
- **AND** a current snapshot change or post-execution content mismatch SHALL invalidate earlier attribution
- **AND** namespace ownership SHALL be checked without importing project packages into the controller
- **AND** genuine directly executed snapshot coverage SHALL take precedence over any installed alias, while raw installed evidence remains available; automatically enumerated zero-execution snapshot rows SHALL NOT mask byte-verified installed execution

#### Scenario: Native coverage aliases cannot prove execution origin

- **GIVEN** native Coverage path aliases rewrite installed-package paths to snapshot paths and a selected installed file differs from its reviewed source
- **WHEN** another owned selected file permits measuring that installed package directory
- **THEN** the worker SHALL retain the native Coverage mapping of installed candidate paths alongside untouched raw coverage
- **AND** the controller SHALL retain an actionable incomplete-origin diagnostic for the byte-different source even when its aliased report row has executed lines
- **AND** byte-identical mappings SHALL be reverified before accepting aliased rows
- **AND** unrelated alias groups SHALL NOT reject actual snapshot execution
- **AND** native origin receipts SHALL cover every owned Python file in measured installed directories, including package-renamed files with no matching snapshot suffix
- **AND** a rewritten source path without a controller-verified source correspondence SHALL remain incomplete instead of acquiring execution credit

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

#### Scenario: Native dependency discovery supports sectionless ELF files

- **GIVEN** a valid supported x86-64 ELF object retains bounded PT_LOAD and PT_DYNAMIC segments but has no section-header table
- **WHEN** project runtime preparation inventories its shared-library dependencies
- **THEN** it SHALL discover DT_NEEDED entries from the dynamic program segment and its mapped string table
- **AND** invalid segment ranges, invalid string-table mappings, unterminated dynamic entries or dependency names, and unsupported ELF encodings or platforms SHALL remain explicit diagnostics

#### Scenario: Executable startup hooks cannot substitute analyzer dispatch

- **GIVEN** a target runtime contains executable `.pth` startup hooks and a verified analyzer entry point
- **WHEN** target startup prepares the analyzer execution domain
- **THEN** it SHALL reject substitutions of the analyzer dispatch functions, their execution/code-loading helpers, or the verified built-in entry-point path before invoking analyzer code
- **AND** replacement of `runpy.run_module`, `runpy.run_path`, their internal execution helpers, or their function code SHALL produce one actionable startup-integrity diagnostic instead of a successful counterfeit analyzer run
- **AND** ordinary additive editable import hooks and path mappings SHALL remain supported
- **AND** this protection SHALL describe a startup-integrity boundary, not a general sandbox against arbitrary code sharing the analyzer interpreter

- **AND** startup-integrity failures SHALL use a reserved non-analysis exit status, and analyzer result parsing SHALL retain that failure even when a startup hook writes valid analyzer-shaped JSON to stdout

#### Scenario: Full reviews use native pytest discovery

- **GIVEN** a full project review without explicit test selectors
- **WHEN** the target worker starts pytest
- **THEN** it SHALL delegate collection roots to pytest without converting configured `testpaths` or the repository root into positional selectors
- **AND** pytest's own configured path expansion, warnings and fallback when configured paths are absent, and positional selections in configured options SHALL remain effective
- **AND** explicit-file, mixed source/test, source-only, index and range review selections SHALL retain their existing explicit selection behavior
- **AND** required collection, execution and coverage evidence SHALL remain enforced; an empty selector list for native discovery SHALL NOT itself count as successful test execution

#### Scenario: Setup failures retain incomplete test-body execution

- **GIVEN** selected pytest tests include one setup failure and another test whose call phase executes
- **WHEN** the capsule evaluates the observed test phases
- **THEN** it SHALL retain the genuine setup failure finding and mark the missing test-body execution incomplete
- **AND** an observed failure outside the call phase SHALL NOT by itself prove that the test body executed
- **AND** failures during a completed call or its subsequent teardown SHALL retain genuine failure evidence without incorrectly claiming that the observed call never ran
- **AND** intentional pytest skips SHALL remain visible and preserve existing selection semantics

#### Scenario: Targeted source reviews expand native pytest test paths

- **GIVEN** repository pytest configuration selects test paths as directories, individual files, or glob patterns
- **WHEN** a targeted source-only or mixed source/test review resolves corresponding test files
- **THEN** candidate discovery SHALL expand configured glob paths and include matched individual Python files while retaining native configuration precedence and Python filename patterns
- **AND** when no configured path matches, corresponding-test discovery SHALL use the repository fallback rather than silently treating the configured pattern as a literal directory
- **AND** expanded paths SHALL remain inside the reviewed repository and preserve exclusion/recursion controls; escaping configured or matched paths SHALL remain explicit diagnostics
- **AND** explicit test selections, targeted ambiguity checks, full-review native discovery, and actual collection/execution/coverage requirements SHALL remain effective

#### Scenario: Pip preparation distinguishes configuration from an installable root

- **GIVEN** a Python repository contains tool configuration in `setup.cfg` but has neither a regular `pyproject.toml` nor `setup.py` file
- **WHEN** the pip adapter prepares the selected runtime
- **THEN** it SHALL install the selected requirements and constraints without appending the repository root as a package requirement
- **AND** when no dependency installation is needed it SHALL emit no pip install command
- **AND** it SHALL retain and import the repository's pytest/tool configuration independently of root-package installation
- **AND** a regular `pyproject.toml` or `setup.py` SHALL retain pip's native root-project installation behavior, including selected extras, without independently reimplementing backend metadata decisions

#### Scenario: Build diagnostics cannot redirect controller filesystem access

- **GIVEN** runtime preparation executes untrusted package-manager or build-hook code in its disposable namespace
- **WHEN** the controller captures or retains build diagnostics
- **THEN** it SHALL create a private regular log with an exclusive controller-owned file descriptor outside all builder-writable directory mounts before starting the builder
- **AND** builder and native-manager stdout/stderr SHALL reach the controller through a pipe; only the controller SHALL hold the regular log descriptor, without opening or copying a builder-chosen log path after execution
- **AND** symlink, directory, or FIFO substitutions at the former staging log path or a predictable failure-log path SHALL NOT cause host-file writes, reads, permission changes, or blocking opens
- **AND** failed and timed-out preparation SHALL retain the trusted private diagnostic log, close its descriptor, and remove disposable staging storage
- **AND** successful preparation SHALL close and remove its temporary diagnostic log
- **AND** public errors SHALL identify the private log without publishing raw build output or credentials

#### Scenario: Builder artifacts are validated before controller enrichment

- **GIVEN** the isolated builder has exited and left a candidate runtime artifact
- **WHEN** the controller is about to read inventory JSON, enumerate native extensions, copy or change permissions on libraries, or derive member inventories
- **THEN** it SHALL first validate that the artifact root is a nonsymlink directory and every descendant is a regular directory or regular file, without reading payload contents during this validation
- **AND** symlinks at the artifact root, inventory JSON, native directory or nested files, and FIFO or other special nodes SHALL fail preparation before any host-following read or write
- **AND** final sealing SHALL revalidate the complete tree after controller enrichment
- **AND** ordinary valid artifacts SHALL remain accepted

#### Scenario: Nested project Python preserves caller context

- **GIVEN** a project process already executing inside a verified isolated target worker
- **WHEN** it invokes the attached Python executable with inherited or explicitly replaced environment and a working directory
- **THEN** the nested process SHALL preserve application environment additions, overrides and removals, the caller-selected working directory, and files in the caller's private temporary filesystem
- **AND** the already-attached member dependency domain SHALL remain stable even when an explicit child environment removes runtime marker variables
- **AND** required runtime startup controls SHALL remain enforced and any unsupported execution control SHALL receive an explicit diagnostic
- **AND** nested execution SHALL retain isolation from supervisor output, control state, processes and external networking
- **AND** ordinary first-entry workers SHALL continue to clear the supervisor environment and establish the original isolation boundary
- **AND** an environment marker alone SHALL NOT grant permission to reuse target context or bypass first-entry isolation

#### Scenario: Native verification fixtures preserve supported analyzer syntax
- **GIVEN** the pinned signed Semgrep engine rejects a valid Python fixture construct
- **WHEN** an equivalent fixture setup is used for this repository's native verification
- **THEN** every isolation assertion and callable parameter constraint remains intact
- **AND** the exact engine failure and passing replacement are retained as fixture compatibility evidence
- **AND** unsupported syntax in customer code still yields incomplete analysis rather than a suppressed error or a false PASS.

### Requirement: Pylint preserves attached namespace source roots

The portable Pylint worker SHALL use already verified snapshot import paths as fallback source roots before native Pylint configuration parsing. It SHALL NOT infer import roots merely from analyzed file locations, add undeclared raw source over an installed package, or suppress missing-import diagnostics.

#### Scenario: Editable namespace contains a same-name leaf module
- **GIVEN** an attached editable runtime or explicit runtime source root exposes an implicit namespace package containing a same-name leaf module
- **WHEN** Pylint analyzes source and tests together
- **THEN** Pylint SHALL resolve imports using the verified namespace source root instead of treating the leaf module as the namespace
- **AND** genuinely unavailable imports SHALL retain their findings

#### Scenario: Native Pylint configuration overrides fallback roots
- **GIVEN** verified runtime roots and explicit Pylint source-roots configuration exist
- **WHEN** the worker initializes Pylint
- **THEN** native repository configuration selection and CLI precedence SHALL override the fallback, including an explicitly empty source-roots value
- **AND** a built package without a declared snapshot import root or editable hook SHALL NOT acquire a raw source overlay

#### Scenario: Corpus rejects known namespace import misresolution
- **GIVEN** the pinned Poetry corpus manifest identifies independently verified import statements
- **WHEN** either cold automatic review or warm descriptor attachment reports Pylint E0401/E0611 at one of those statements
- **THEN** corpus acceptance SHALL fail even when all analyzer members ran
- **AND** unrelated findings SHALL remain permitted and retained in the report

#### Scenario: Pylint dispatcher changes invalidate runtime reuse
- **GIVEN** a cached runtime with unchanged project inputs and signed worker identity
- **WHEN** only the trusted Pylint dispatcher implementation changes
- **THEN** its content digest SHALL change the builder cache identity and offline preparation SHALL report a cache miss
- **AND** unchanged dispatcher bytes SHALL retain warm cache reuse

#### Scenario: Runtime payloads cannot retain controller diagnostic hardlinks

- **GIVEN** a builder leaves a regular artifact file sharing an inode with a controller diagnostic log or another file outside the artifact
- **WHEN** the controller validates build output, seals it, or verifies it for reuse
- **THEN** regular files with multiple hardlinks SHALL be rejected before their payload is read or the runtime is attached
- **AND** the controller SHALL retain its private failure log without publishing diagnostic bytes in the runtime or public error
- **AND** ordinary copied package files with a single link SHALL remain accepted, including when the package manager uses hardlinks inside its disposable environment
- **AND** a hardlink introduced after sealing SHALL invalidate attachment even when its bytes still match the recorded digest

#### Scenario: Builder children cannot reopen controller log storage

- **GIVEN** untrusted build hooks execute as descendants of the isolated build driver
- **WHEN** the driver or its children inspect or reopen their stdout/stderr through process descriptors
- **THEN** those descriptors SHALL identify pipes, never the controller's regular diagnostic file
- **AND** the controller SHALL stream diagnostics with bounded buffering, preserve partial timeout/failure output and close all capture descriptors and helpers
- **AND** normal successful and downstream-failure log retention semantics SHALL remain unchanged

#### Scenario: Preparation failures retain safe controller reasons

- **GIVEN** a builder exits unsuccessfully or controller artifact validation rejects its output
- **WHEN** preparation reports the failure to a review or runtime command
- **THEN** the public diagnostic SHALL retain the controller's stable failure code and a numeric builder exit status when available, alongside the private log path
- **AND** arbitrary exception text, selected paths and raw subprocess output SHALL NOT be copied into the public error
- **AND** existing private diagnostic capture and retention SHALL remain unchanged; reporting a controller code SHALL NOT require an extra filesystem operation

#### Scenario: Nested Python preserves caller import paths

- **GIVEN** a process already executing in an isolated target worker supplies inherited or explicit PYTHONPATH entries for customer modules
- **WHEN** it invokes the attached Python executable
- **THEN** the trusted startup directory SHALL remain first and caller import-path entries SHALL retain their order and normal empty/relative path semantics inside the existing namespace
- **AND** member analyzer imports SHALL remain sealed and host-only paths or supervisor state SHALL remain inaccessible
- **AND** empty or omitted caller PYTHONPATH SHALL not weaken trusted startup or member-domain verification

### Requirement: Declare compatible repository development analyzer versions
This repository's Hatch development environment SHALL explicitly select its declared Pylint and basedpyright entry versions in its signed review toolchain. External customer dependency declarations and genuine runtime incompatibility checks SHALL remain unchanged.

#### Scenario: Fresh developer resolution remains compatible
- **GIVEN** the signed analyzer entries and an observed newer incompatible native development resolution
- **WHEN** this repository selects its declared development analyzer versions
- **THEN** production runtime compatibility validation accepts the declared selection for every signed Python ABI
- **AND** the originally incompatible customer package versions remain rejected by the unchanged compatibility contract

#### Scenario: BasedPyright preserves its actual sealed Node distribution
- **GIVEN** the signed BasedPyright dependency is `nodejs-wheel-binaries` and supplies `nodejs_wheel`
- **WHEN** project runtime compatibility and member import mounts are resolved
- **THEN** a matching or absent project distribution preserves the sealed Node dependency graph, mount and import origin
- **AND** an unequal project version produces an explicit BasedPyright incompatibility instead of a missing sealed import or silent substitution
- **AND** changing the controller compatibility policy invalidates offline cache reuse even when the selected signed worker identity is unchanged
- **AND** the obsolete `nodejs-wheel` distribution name does not impose a restriction on an unrelated customer package.

### Requirement: Declare bounded target native tools

Runtime preparation SHALL expose only explicitly declared supported native tools to target workers, preserving the sealed supervisor and the existing offline worker boundary. The initial supported capabilities are `git`, `uname`, and `sed`. Repository declarations use `[tool.specfact.code-review] native_tools`; an explicit project configuration overrides that declaration.

#### Scenario: Declared native tools retain complete controller-owned identity
- **GIVEN** a repository declares supported native tools
- **WHEN** its runtime is prepared
- **THEN** the controller captures the supported executables, required Git helpers, generated launchers, and their complete ELF library closure before a disposable builder can run
- **AND** all captured bytes contribute to cache identity and recorded inventory
- **AND** the controller installs the capture only after the builder exits, rejecting tool destination collisions before writing any tool payload
- **AND** target workers use the private runtime PATH without adding host directories or copying an arbitrary host environment.

#### Scenario: Unsupported or unavailable tools fail precisely
- **GIVEN** an unknown tool, a missing supported executable or helper, or an incompatible native binary
- **WHEN** discovery or preparation reaches that requirement
- **THEN** it reports the exact unsupported or unavailable capability without guessing another executable from PATH
- **AND** empty declarations add no tools.

#### Scenario: Native tool inputs invalidate reuse and remain immutable during building
- **GIVEN** an existing prepared runtime and changed native tool or transitive library bytes
- **WHEN** preparation computes its cache key
- **THEN** offline reuse fails for the changed identity
- **AND** an isolated builder cannot replace captured controller-owned executables or libraries
- **AND** the sealed target shell required by Git is verified as part of the selected capsule identity rather than supplied by a customer artifact.

### Requirement: Sanitized VCS lookup retains declared target Git

The controller's VCS metadata operations SHALL preserve all existing no-global/system-configuration, no-hooks, no-replacements, no-lazy-fetch and protocol restrictions. Within an existing verified read-only target-worker context, they SHALL use the fixed attached Git launcher only when the descriptor declares Git and its controller-generated inventory hash matches contained regular launcher bytes. Host execution SHALL retain the fixed system search path. Ambient PATH entries or forged environment markers SHALL NOT select project executables, and invalid declared target capabilities SHALL fail closed with a precise diagnostic.

#### Scenario: Verified target metadata export uses the declared launcher
- **GIVEN** an authenticated target-worker context with a declared and hash-verified Git launcher outside the system search path
- **WHEN** isolated VCS metadata export executes with a sanitized child environment
- **THEN** it uses that fixed absolute launcher while preserving all existing Git configuration and protocol restrictions
- **AND** missing or tampered capability bytes fail explicitly rather than selecting an ambient executable

#### Scenario: Ambient environment cannot redirect host VCS export
- **GIVEN** ordinary host execution with hostile PATH entries or forged worker environment markers
- **WHEN** VCS metadata export runs
- **THEN** it retains fixed system lookup and never trusts those entries as attached project tools

#### Scenario: Graft isolation is verified without ambient Git templates
- **GIVEN** Git initialized a repository without system templates or an existing `.git/info` directory
- **WHEN** the graft-isolation regression injects unbound ancestry metadata
- **THEN** its fixture explicitly creates the metadata parent before writing grafts
- **AND** the original assertions still prove source identity is unchanged, exported ancestry has both commits, and grafts are absent from the export
- **AND** ordinary template-backed initialization exercises the same assertions.

### Requirement: Target workers retain only signed public default trust data

Automatic runtime preparation SHALL preserve the signed worker's public certificate trust bundle at the conventional target path `/etc/ssl/certs/ca-certificates.crt`, without copying host trust stores, credentials or arbitrary host configuration. The controller SHALL capture verified contained regular certificate bytes before disposable building, bind their identity to cache reuse and runtime inventory, and install them after validating builder output. Builder-created destination or symlink collisions SHALL fail closed. Target analysis SHALL remain offline; certificate availability grants no network capability.

#### Scenario: Offline dependency initialization can read public default certificates
- **GIVEN** an authenticated signed worker containing its public certificate bundle
- **WHEN** an isolated project dependency initializes its TLS context during offline analysis
- **THEN** the target's conventional certificate path contains the exact recorded signed public bytes
- **AND** builder modifications cannot replace those bytes or redirect the destination

### Requirement: The repository declares its runtime registry dependency

This repository's selected Hatch review environment SHALL declare an immutable published SpecFact CLI version providing the registry APIs that its reviewed code imports. Hermetic runtime preparation SHALL acquire that declared dependency through Hatch, without copying an editable host checkout or suppressing genuine missing imports.

#### Scenario: Declared core dependency supplies the actual registry API
- **GIVEN** review code importing the SpecFact CLI module-discovery and installer APIs
- **WHEN** the repository's Hatch default dependencies are inspected and prepared
- **THEN** they explicitly admit the verified published core package and its actual registry API can be imported
- **AND** the separate developer editable-checkout bootstrap does not substitute for this declaration
