## ADDED Requirements

### Requirement: Customer standards remain authoritative
Customer-standard checks SHALL use customer-selected tools, versions, native configuration and plugins. Selection SHALL prefer explicit invocation or configuration, then an explicitly selected organizational profile, then native project discovery. SpecFact supplemental analysis SHALL remain separately attributed without rewriting project lint policy.

#### Scenario: Project standards disagree with SpecFact development defaults
- **GIVEN** the customer configures different lint rules, exclusions, formatting or coverage thresholds
- **WHEN** customer-standard checks run
- **THEN** their effective configuration follows the customer project and no universal SpecFact coverage floor or style requirement is injected

#### Scenario: All selected diagnostic identifiers survive
- **GIVEN** Ruff or another supported analyzer emits a customer-selected rule outside a historical hardcoded family
- **WHEN** the adapter normalizes its result
- **THEN** the report retains the rule identifier and diagnostic instead of dropping it

#### Scenario: Unknown custom check output
- **GIVEN** a named customer check has no structured diagnostic adapter
- **WHEN** its configured argv runs
- **THEN** the report retains command completion, exit status and bounded output without inventing source positions or discarding a nonzero result

### Requirement: Explicit declarative profile contribution
ProjectProfileProvider SHALL be a narrow explicitly selected entrypoint in specfact.project_profiles installed in the external CLI environment. It SHALL return declarative selection preferences, configuration references, and named check commands. Runtime ownership and finding severity SHALL remain with the runtime service and review respectively.

#### Scenario: Explicit organizational profile
- **GIVEN** a compatible provider is installed outside the customer repository and explicitly selected
- **WHEN** review resolves its contribution
- **THEN** the contribution is validated once and native project tools retain their own plugin and configuration semantics

#### Scenario: Unavailable or incompatible provider
- **GIVEN** the selected provider is missing or its contribution version is unsupported
- **WHEN** review loads the profile
- **THEN** it reports an actionable profile failure without importing arbitrary project providers into the controller or silently choosing another profile

### Requirement: Analyzer dependencies do not alter customer environments
Project-defined checks SHALL run in the selected project environment. Source-only supplemental tools SHALL run in separate external tool environments. Import-dependent supplemental checks SHALL use a compatible project tool or an independently prepared same-interpreter environment preserving the complete selected project dependency graph and origins.

#### Scenario: Compatible project-installed tool
- **GIVEN** the selected environment already supplies the configured analyzer and its plugins
- **WHEN** the relevant check runs
- **THEN** it uses that installation and records its version without installing or upgrading packages

#### Scenario: Conflicting supplemental analyzer
- **GIVEN** an import-dependent analyzer conflicts with a project dependency, package origin, Python version or build requirement
- **WHEN** its compatible environment cannot be prepared faithfully
- **THEN** the affected check is unavailable with a remedy, other checks continue, and customer dependencies are neither replaced nor added to the controller import path

### Requirement: Existing contracts are checked without mandatory decoration
The initial contract adapter SHALL analyze existing supported icontract contracts through CrossHair. Absence of such contracts SHALL be not applicable. A violated contract, an unsupported requested mechanism, and an execution failure SHALL remain distinct outcomes. It SHALL not require missing decorators or synthesize customer contracts.

#### Scenario: Actual contract violation
- **GIVEN** a project uses a supported icontract contract that the configured analysis can falsify
- **WHEN** the contract check executes in faithful project context
- **THEN** the violation becomes an attributed finding with actual analyzer provenance

#### Scenario: No contracts or unsupported contract mechanism
- **GIVEN** the project has no supported contracts or explicitly requests an unsupported mechanism
- **WHEN** applicability is resolved
- **THEN** absence is not applicable and unsupported requested analysis is incomplete rather than a missing-icontract finding or clean pass

### Requirement: Explicit pytest targets retain native semantics
Explicit test-file selection SHALL remain distinct from automatic source-to-test discovery. The selected pytest file SHALL not be silently replaced or omitted because its basename fails automatic python_files patterns.

#### Scenario: Nonstandard failing test filename
- **GIVEN** tests/checks.py contains a failing test and tests/test_checks.py passes
- **WHEN** the customer explicitly selects tests/checks.py
- **THEN** that file is collected and executed and its failure appears in the review result

#### Scenario: Custom patterns and mixed sources
- **GIVEN** the project has custom python_files patterns and the review selects both production source and an explicit test file
- **WHEN** pytest selection is assembled
- **THEN** the explicit test target is preserved and production-source mapping does not indiscriminately execute source files as tests
