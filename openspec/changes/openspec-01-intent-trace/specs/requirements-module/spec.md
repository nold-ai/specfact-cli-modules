## ADDED Requirements

### Requirement: OpenSpec and Spec Kit Import Runtime

The requirements module SHALL provide runtime command flags that import native
OpenSpec change folders and Spec Kit feature folders into requirement evidence
through the core evidence adapter, and SHALL surface core gate findings in
validation output. The runtime SHALL contain no parsing, hashing, or gate
logic of its own and SHALL never write into upstream artifact directories.

#### Scenario: Import from an OpenSpec change folder

- **GIVEN** a project bundle and an OpenSpec change folder
- **WHEN** `specfact requirements import --from-openspec <path> --bundle <bundle>` runs
- **THEN** the core adapter normalizes the artifacts into requirement records
- **AND** merged records persist to the bundle requirements sidecar exactly like `--from-file` imports
- **AND** the command reports imported counts and diagnostics.

#### Scenario: Import from a Spec Kit feature folder

- **GIVEN** a project bundle and a Spec Kit feature folder
- **WHEN** `specfact requirements import --from-speckit <path> --bundle <bundle>` runs
- **THEN** the core adapter normalizes the artifacts into requirement records
- **AND** merged records persist to the bundle requirements sidecar.

#### Scenario: Omitted source paths auto-detect conventional layouts

- **GIVEN** a project root containing an `openspec/changes/` directory
- **WHEN** `specfact requirements import --from-openspec` runs without an explicit path
- **THEN** the conventional layout is detected and imported
- **AND** a clear error names the expected layouts when detection finds no source.

#### Scenario: Validate surfaces gate findings with CI-usable exit codes

- **GIVEN** a bundle with imported requirements that trigger core gate findings
  (`scenario-unverified`, `stale-import`, `source-missing`, `ambiguous-mapping`)
- **WHEN** `specfact requirements validate --bundle <bundle> --profile <profile>` runs
- **THEN** the report lists each gate finding with its category and affected requirement IDs
- **AND** the command exits non-zero when the profile treats any finding as an error.

#### Scenario: Runtime never writes upstream

- **GIVEN** import and validation runs against OpenSpec and Spec Kit sources
- **WHEN** the commands complete
- **THEN** the upstream source directories are byte-identical to before the run.
