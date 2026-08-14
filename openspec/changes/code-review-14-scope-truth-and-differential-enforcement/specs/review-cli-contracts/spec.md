## ADDED Requirements

### Requirement: Truthful Review Assurance Status

The governed review report schema `1.6` SHALL expose authoritative `assurance_status` as `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE`. `WAIVED` SHALL be a governance overlay, not a verifier-produced status. A mandatory UNKNOWN SHALL prevent PASS. NOT_APPLICABLE SHALL require successfully resolved no-governed-impact evidence.

#### Scenario: Mandatory evidence is unknown

- **GIVEN** scope or a mandatory analyzer is unknown
- **WHEN** enforce-mode reporting completes
- **THEN** assurance is UNKNOWN and process exit is non-zero
- **AND** partial facts/findings remain available
- **AND** the human summary does not say all validations passed.

#### Scenario: Schema 1.6 dual-writes a conservative legacy projection

- **GIVEN** a schema 1.6 report has assurance PASS, FAIL, UNKNOWN, or NOT_APPLICABLE
- **WHEN** compatibility fields are serialized
- **THEN** PASS writes legacy PASS or PASS_WITH_ADVISORY according to remaining advisories
- **AND** FAIL writes legacy FAIL
- **AND** UNKNOWN writes legacy FAIL rather than a green verdict
- **AND** NOT_APPLICABLE writes PASS_WITH_ADVISORY plus explicit no-governed-impact text
- **AND** strict/full/range exit codes are 0, 1, 1, and 0 respectively.

#### Scenario: Legacy enforcement mode is policy, not scope

- **GIVEN** schema 1.6 dual-writing is enabled
- **WHEN** enforcement and scope are serialized
- **THEN** request mode enforce normalizes to legacy enforcement_mode full
- **AND** full, changed, and shadow retain their legacy values
- **AND** changed mode is accepted only with the deprecated changed/worktree compatibility path
- **AND** range plus changed mode is rejected
- **AND** strict range writes enforcement_mode full, shadow range writes shadow, and scope_evidence alone identifies range.

#### Scenario: Versioned readers never infer new truth from old fields

- **GIVEN** a report older than schema 1.6
- **WHEN** compatibility reading completes
- **THEN** legacy PASS or PASS_WITH_ADVISORY may yield only PASS and legacy FAIL may yield only FAIL
- **AND** UNKNOWN or NOT_APPLICABLE is never inferred
- **AND** schema 1.6 or newer with missing/invalid assurance_status is invalid/unknown and cannot pass.

#### Scenario: Shadow preserves unknown while exiting zero

- **GIVEN** the same unknown evidence under shadow mode
- **WHEN** reporting completes
- **THEN** process exit may be zero for rollout
- **AND** report assurance remains UNKNOWN
- **AND** no field rewrites the unknown claim to pass.

### Requirement: Review CLI Contracts Cover Explicit Scope and Differential Evidence

CLI contract fixtures SHALL cover worktree, index, range, full, positional files, deprecated changed alias, full-ref validation, staged-versus-unstaged index content, merge-base selection with an advanced base-ref tip, changed-test inclusion, empty range, Git failure, merge-base/head classifications, analyzer coverage, and invalid option combinations.

#### Scenario: Range contract requires base and head

- **GIVEN** range scope is requested without one required ref or together with positional files
- **WHEN** the CLI parses the request
- **THEN** it fails with a bounded error and a supported invocation example.

#### Scenario: Positional files cannot satisfy pull-request assurance

- **GIVEN** positional files are supplied to a consumer or policy that requires pull-request range assurance
- **WHEN** the request is validated
- **THEN** it is rejected before analysis because base, head, and merge-base evidence is absent
- **AND** the supported alternative is `--scope range --base-ref <full-ref> --head-ref <full-ref>`
- **AND** positional files remain valid for explicitly labelled non-PR `assurance_kind=explicit_files` runs.

