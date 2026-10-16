## ADDED Requirements

### Requirement: Versioned local evidence has explicit consumers
The producer SHALL emit schema 2.0 with local execution provenance, actual tool versions, effective configuration references, source and dependency identity, and per-check completion. Consumers SHALL dispatch explicitly by supported schema version. Historical schema 1.6 SHALL retain its original meaning without synthesized capsule fields.

#### Scenario: New major version is not legacy evidence
- **GIVEN** a schema 2.0 report reaches a helper that historically used a schema-at-least-1.6 test
- **WHEN** the updated consumer selects its interpretation
- **THEN** it selects the explicit local schema handler and does not invoke capsule-profile validation

#### Scenario: Unknown major or malformed required evidence
- **GIVEN** a report has an unsupported major version or malformed completion facts
- **WHEN** a consumer evaluates the report
- **THEN** it rejects or reports incomplete evidence and never falls back to score-based or fabricated legacy acceptance

### Requirement: Findings and execution completeness are separate
A failed test or detected defect SHALL remain a completed check with findings. Preparation failure, timeout, malformed output and missing required checks SHALL remain incomplete. Existing changed, full and shadow selection semantics SHALL be retained subject to explicit local-schema handling, without introducing C15 calibration or waiver authority.

#### Scenario: Completed failing test
- **GIVEN** pytest collects and executes the selected test and its assertion fails
- **WHEN** the review aggregates results
- **THEN** the test failure remains observed evidence and is not relabeled as infrastructure uncertainty

#### Scenario: Incomplete required analysis in shadow
- **GIVEN** a required analyzer times out or cannot execute
- **WHEN** review runs in shadow and then in a non-shadow enforcement mode
- **THEN** both reports retain adverse truth and incomplete status while shadow may exit zero and non-shadow enforcement remains nonaccepting

### Requirement: Execution binds the reviewed source
Worktree review SHALL verify relevant source stability during execution. Index and range execution SHALL prepare project context against the corresponding materialized source snapshots. Editable imports, generated code and native artifacts from another checkout SHALL not establish snapshot-bound evidence.

#### Scenario: Live editable import points outside snapshot
- **GIVEN** a range snapshot differs from the live checkout used by an existing editable installation
- **WHEN** a dynamic check is requested for the snapshot
- **THEN** review prepares faithful snapshot context or marks that check incomplete instead of reporting live-checkout execution as snapshot evidence

#### Scenario: Source changes during worktree review
- **GIVEN** a relevant input changes while checks execute
- **WHEN** review finalizes its source identity
- **THEN** it reports stale or incomplete evidence rather than attributing all results to one unchanged source

### Requirement: Local evidence cannot grant protected authority
Local execution SHALL not emit effective protected pr_range authority. Immutable source selection, an installed signed module, or a caller-supplied PR context SHALL not manufacture capsule attestation or satisfy the existing protected C14 consumer contract.

#### Scenario: Caller supplies PR context
- **GIVEN** a local range invocation supplies matching base/head references and a claimed PR context
- **WHEN** the producer emits schema 2.0
- **THEN** the report remains local evidence and a protected consumer cannot promote it using the old capsule contract

#### Scenario: Historical differential behavior
- **GIVEN** compatible base and head local analyses use the same supported check and policy identities
- **WHEN** findings are compared
- **THEN** existing identity, multiplicity, differential and suppression semantics are preserved, and incompatible identities remain unknown

### Requirement: Public cutover removes capsule execution
The public cutover SHALL route all review scopes through one local orchestrator and remove both native macOS and Linux OCI/Bubblewrap capsule paths and the parallel legacy host orchestrator. It SHALL remove callable capsule fallback switches while preserving module signatures, source integrity, bounded subprocess execution, and independent security gates.

#### Scenario: No capsule prerequisite or fallback
- **GIVEN** a customer invokes review on a supported ordinary host without a capsule, native broker or user namespaces
- **WHEN** the local release executes
- **THEN** it uses the selected project and analyzer contexts without acquiring or launching any capsule backend

#### Scenario: Capsule capability is removed without false completion
- **GIVEN** the replacement is implemented and integrated
- **WHEN** legacy catalogs, native builds, capsule-only release jobs and capability declarations are reconciled
- **THEN** obsolete guarantees are removed by the owning implementation deltas and historical signed artifacts remain immutable
