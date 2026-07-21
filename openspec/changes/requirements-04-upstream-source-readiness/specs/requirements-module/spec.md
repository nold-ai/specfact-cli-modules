## ADDED Requirements

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
