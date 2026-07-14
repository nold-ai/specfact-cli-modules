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

#### Scenario: Omitted source paths auto-detect active conventional layouts

- **GIVEN** a project root containing one active OpenSpec change and an
  `openspec/changes/archive/` directory
- **WHEN** `specfact requirements import --from-openspec` runs without an explicit path
- **THEN** the active conventional change layout is detected and imported
- **AND** the archive directory is not considered an import source
- **AND** a clear error names the expected layouts when detection finds no source.

#### Scenario: Validate surfaces gate findings with CI-usable exit codes

- **GIVEN** a bundle with imported requirements that trigger core gate findings
  (`scenario-unverified`, `stale-import`, `source-missing`, `ambiguous-mapping`)
- **WHEN** `specfact requirements validate --bundle <bundle> --profile <profile>` runs
- **THEN** the report lists each gate finding with its category and affected requirement IDs
- **AND** the command exits non-zero when the profile treats any finding as an error.

#### Scenario: Runtime preserves core required-field advisories

- **GIVEN** core validation returns an `unsupported-profile-field` advisory
  for a profile field not represented by `RequirementInput`
- **WHEN** `specfact requirements validate` renders the validation report
- **THEN** the advisory is present in the machine-readable and human-readable
  output unchanged
- **AND** the module does not add owner, risk, or exception metadata to the
  imported record.

#### Scenario: Runtime blocks unsupported source profiles

- **GIVEN** an OpenSpec schema or Spec Kit template profile rejected by the
  core adapter with `unsupported-source-schema`
- **WHEN** an import command delegates to core
- **THEN** the command surfaces that diagnostic unchanged
- **AND** it does not create or persist partial requirement records
- **AND** it does not attempt version detection or fallback parsing.

#### Scenario: Runtime never writes upstream

- **GIVEN** import and validation runs against OpenSpec and Spec Kit sources
- **WHEN** the commands complete
- **THEN** the upstream source directories are byte-identical to before the run.
