# requirements-module Specification

## Purpose
TBD - created by archiving change requirements-02-module-commands. Update Purpose after archive.
## Requirements
### Requirement: Requirements Runtime Commands

The system SHALL provide module-owned `specfact requirements ...` commands for
importing, validating, listing, and inspecting upstream requirement context as
validation evidence.

#### Scenario: Import local requirement records into bundle extensions

- **GIVEN** a local JSON or YAML file containing source-attributed requirement records
- **WHEN** `specfact requirements import --from-file <path> --bundle <bundle>` runs
- **THEN** valid records are stored under the bundle's `requirements.inputs` extension
- **AND** invalid records are returned as bounded diagnostics.

#### Scenario: Validate requirement context by profile

- **GIVEN** a project bundle with normalized requirement inputs
- **WHEN** `specfact requirements validate --bundle <bundle> --profile enterprise` runs
- **THEN** validation delegates to the core profile-aware requirements context helper
- **AND** missing downstream evidence links are reported as failed validation.

#### Scenario: List requirements with coverage summary

- **GIVEN** requirement inputs are present on a project bundle
- **WHEN** `specfact requirements list --bundle <bundle> --show-coverage --format json` runs
- **THEN** each requirement ID and title is returned
- **AND** the output includes a machine-readable coverage summary.

#### Scenario: No authoring command is exposed

- **GIVEN** the requirements module is installed
- **WHEN** the user inspects `specfact requirements --help`
- **THEN** import, validate, list, and coverage commands are visible
- **AND** requirement authoring commands are not exposed.

### Requirement: Upstream source readiness for native requirement imports

The Requirements module SHALL persist native OpenSpec or Spec Kit requirement
evidence only when the paired core source-readiness contract accepts the source.
The module SHALL surface core readiness diagnostics unchanged, SHALL return a
non-zero result when any readiness diagnostic has error severity, and SHALL not
persist partial records for a rejected source. The module SHALL remain read-only
toward upstream artifact directories and SHALL not implement source parsing,
placeholder detection, hashing, or upstream-validator policy itself.

#### Scenario: Reject an incomplete Spec Kit scaffold

- **GIVEN** a native Spec Kit feature source containing a recognised official
  draft placeholder or an unresolved `NEEDS CLARIFICATION` marker
- **WHEN** `specfact requirements import --from-speckit <path> --bundle <bundle>` runs
- **THEN** the module reports the core `incomplete-source-template` or
  `source-incomplete` diagnostic with its source location
- **AND** it reports zero imported records and exits non-zero
- **AND** it does not create or modify the bundle requirements sidecar
- **AND** the upstream feature directory remains byte-identical.

#### Scenario: Import a completed native Spec Kit feature

- **GIVEN** a native Spec Kit feature with substantive Functional Requirements
  and meaningful GIVEN/WHEN/THEN acceptance scenarios
- **WHEN** `specfact requirements import --from-speckit <path> --bundle <bundle>` runs
- **THEN** the module persists the core-normalized records with stable IDs and
  source hash provenance
- **AND** it reports no readiness diagnostics
- **AND** re-importing the unchanged feature creates no duplicates.

#### Scenario: Reject an invalid OpenSpec change under required upstream validation

- **GIVEN** repository policy requires native OpenSpec validation and the
  selected change fails core-invoked `openspec validate --strict --json`
- **WHEN** `specfact requirements import --from-openspec <path> --bundle <bundle>` runs
- **THEN** the module reports the core `source-invalid` diagnostic
- **AND** it reports zero imported records and exits non-zero
- **AND** it does not create or modify the bundle requirements sidecar.

#### Scenario: Report a required but unavailable OpenSpec validator

- **GIVEN** repository policy requires native OpenSpec validation and the
  OpenSpec CLI is unavailable
- **WHEN** an OpenSpec import runs
- **THEN** the module reports the core `upstream-validator-unavailable`
  diagnostic
- **AND** it reports zero imported records and exits non-zero
- **AND** it does not attempt fallback parsing that claims upstream validation.

#### Scenario: Preserve portable basic OpenSpec import

- **GIVEN** repository policy does not require native OpenSpec CLI validation
  and the source satisfies the core-supported native schema
- **WHEN** an OpenSpec import runs without the OpenSpec CLI installed
- **THEN** the module delegates the source to the core normalizer
- **AND** it preserves the existing completed-import behavior without claiming
  that native CLI validation occurred.

#### Scenario: Dogfood the shipped source-readiness specification

- **GIVEN** this completed OpenSpec change maps its imported stable requirement
  to the existing Requirements runtime and command-integration test targets
- **WHEN** the Requirements evidence adapter evaluates this source together
  with the #352 dogfood-evidence source in isolated bundles
- **THEN** each source imports without error diagnostics and has complete
  declared test-link coverage
- **AND** the aggregate verdict is `passed`
- **AND** the evidence continues to state that test-execution proof is not
  included.

