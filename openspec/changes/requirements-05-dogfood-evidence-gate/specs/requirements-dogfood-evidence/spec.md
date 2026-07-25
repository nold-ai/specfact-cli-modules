## ADDED Requirements

### Requirement: Requirements evidence verdict

The system SHALL evaluate each changed active OpenSpec change with the existing
Requirements import, validation, coverage, and gate-finding operations, and
SHALL emit a machine-readable aggregate verdict without modifying the source.

#### Scenario: Produce a green evidence verdict

- **GIVEN** a changed active OpenSpec source imports one or more requirements
  without error diagnostics
- **AND** validation does not fail, every imported requirement has a test link,
  and gate-finding counts are zero
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

- **GIVEN** the evaluated branch changes no existing directory beneath
  `openspec/changes/` outside `archive/`
- **WHEN** the requirements evidence adapter runs
- **THEN** it writes `requirements-evidence.json` with aggregate verdict
  `skipped`
- **AND** it exits zero
- **AND** it does not describe the skipped result as proof that requirements
  are met.

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
