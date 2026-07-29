# requirements-dogfood-evidence Specification

## Purpose
TBD - created by archiving change requirements-05-dogfood-evidence-gate. Update Purpose after archive.
## Requirements
### Requirement: Requirements evidence verdict

The system SHALL evaluate each changed active OpenSpec change with the existing
Requirements import, validation, coverage, and gate-finding operations, and
SHALL emit a machine-readable aggregate verdict without modifying the source.

#### Scenario: Produce a green evidence verdict

- **GIVEN** a changed active OpenSpec source imports one or more requirements
  without error diagnostics
- **AND** validation does not fail, every imported requirement has a test link,
  and there are no error-level gate findings
- **WHEN** the requirements evidence adapter runs
- **THEN** it writes `requirements-evidence.json` with aggregate verdict
  `passed`
- **AND** the source entry preserves the import, validation, coverage, and
  gate-finding evidence
- **AND** the process exits zero.

#### Scenario: Apply declared test-link evidence without mutating OpenSpec

- **GIVEN** a changed active OpenSpec source has a
  `requirements-evidence.yaml` sidecar mapping each imported stable requirement
  ID to existing repository-relative test targets
- **WHEN** the requirements evidence adapter runs
- **THEN** it applies the test links only to its isolated temporary bundle
- **AND** Requirements validation and coverage include those links
- **AND** the OpenSpec source Markdown and sidecar remain unchanged.

#### Scenario: Reject an invalid evidence sidecar

- **GIVEN** an evidence sidecar references an unknown imported requirement ID
  or a missing test target
- **WHEN** the requirements evidence adapter runs
- **THEN** it produces a failed verdict with a deterministic sidecar reason
- **AND** it does not claim test-link coverage is complete.

#### Scenario: Produce a red evidence verdict and retain its causes

- **GIVEN** a changed active OpenSpec source has an import error, no imported
  requirements, failed validation, incomplete test-link coverage, or an
  error-level gate finding
- **WHEN** the requirements evidence adapter runs
- **THEN** it writes `requirements-evidence.json` with aggregate verdict
  `failed`
- **AND** the affected source contains a deterministic reason for each failed
  condition
- **AND** the process exits non-zero only after the report is written.

#### Scenario: Skip when no active OpenSpec source changed

- **GIVEN** the evaluated branch changes no active OpenSpec source path beneath
  `openspec/changes/` outside `archive/`
- **WHEN** the requirements evidence adapter runs
- **THEN** it writes `requirements-evidence.json` with aggregate verdict
  `skipped`
- **AND** it exits zero
- **AND** it does not describe the skipped result as proof that requirements
  are met.

#### Scenario: A newly added active source is evaluated

- **GIVEN** the evaluated branch adds a source beneath
  `openspec/changes/<change-id>/`
- **WHEN** the requirements evidence adapter runs
- **THEN** it evaluates that source rather than returning a skipped verdict.

#### Scenario: Preserve shipped-source regression coverage after archival

- **GIVEN** a shipped OpenSpec change is present either as an active change or
  in OpenSpec's date-prefixed archive location
- **WHEN** the permanent dogfood regression suite evaluates its source
- **THEN** it resolves the source by its stable change ID in either location
- **AND** normal `openspec archive <change-id>` finalization does not make the
  regression suite fail because an active-change path disappeared.

### Requirement: Pull-request evidence publication

The pull-request workflow SHALL run the requirements evidence adapter after the
paired core CLI and Requirements module are available, publish a concise
requirements-evidence summary, and upload the JSON report regardless of the
verdict.

#### Scenario: Publish green or red evidence for review

- **GIVEN** a pull request changes an active OpenSpec source
- **WHEN** the requirements evidence job completes
- **THEN** GitHub Actions uploads `requirements-evidence.json` for both passed
  and failed verdicts
- **AND** the job summary shows the aggregate verdict, source count, and
  whether execution-level test proof is included
- **AND** a failed verdict fails the job.

#### Scenario: Retain setup-failure evidence

- **GIVEN** the workflow cannot bootstrap the paired core CLI or local
  Requirements module source before the adapter runs
- **WHEN** the setup step fails
- **THEN** the workflow still writes and uploads a machine-readable failed
  `requirements-evidence.json` and a concise Markdown summary
- **AND** the failure report identifies setup as the unavailable evidence stage
- **AND** the job remains failed.

#### Scenario: Publish a complete fallback artifact pair

- **GIVEN** the workflow needs fallback evidence because its adapter artifacts
  are missing, incomplete, or the JSON report is unparsable
- **WHEN** the fallback writer runs
- **THEN** it prepares the JSON report and Markdown summary before publishing
  either final artifact
- **AND** the workflow treats fallback evidence as complete only when both
  final artifacts exist and the JSON report parses successfully.
- **AND** generated artifact text uses LF line endings
- **AND** a failed artifact replacement restores the prior published pair.

#### Scenario: Reject aliased fallback artifact destinations

- **GIVEN** the fallback JSON output path and Markdown summary path resolve to
  the same filesystem destination
- **WHEN** the fallback writer runs
- **THEN** it fails with a clear configuration error before creating parent
  directories or writing either artifact.

#### Scenario: Use local module source roots in CI

- **GIVEN** the workflow runs from this modules repository checkout
- **WHEN** it prepares the Requirements evidence adapter
- **THEN** it exposes the Requirements module and its direct local bundle
  dependency through repository source roots
- **AND** it does not attempt to install a bundle directory that lacks Python
  packaging metadata.
