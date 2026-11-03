## ADDED Requirements

### Requirement: Execute exact native Hatch acceptance in mandatory CI
CI SHALL execute change 17's mapped pytest cases on Linux against the event-selected pull-request head, using separate Python 3.12.13 controller and Python 3.11.15 project installations and native Hatch 1.18.1. It SHALL configure the native acceptance cell and retain JUnit and the native workflow receipt outside the checkout. The job SHALL use read-only repository permissions without persisted credentials and SHALL run independently of capsule jobs.

#### Scenario: Native acceptance has explicit inputs and source
- **WHEN** a pull request schedules verification
- **THEN** the native job checks out its exact head and supplies every native proof prerequisite with the two independent Python installations

### Requirement: Incomplete mapped execution cannot pass
The native job SHALL derive executable pytest selectors from the existing change-17 mapping and require each selector exactly once in JUnit. Empty or duplicate mappings, nonzero pytest exits, missing reports, absent or additional selectors, duplicate results, skips, errors and failures SHALL be nonaccepting. Inspection-only planning entries SHALL not be represented as executed tests.

The mapping SHALL remain usable after normal OpenSpec archival. Prefer the active mapping; when it is absent, require exactly one archived mapping for that change identity. An ambiguous archived source SHALL fail rather than selecting an arbitrary history entry.

#### Scenario: Mapping survives OpenSpec archival
- **WHEN** the active change mapping has moved into one dated OpenSpec archive directory
- **THEN** native acceptance executes the same mapped cases from that archive
- **AND** multiple matching archived mappings are rejected with an explicit diagnostic

#### Scenario: Complete mapped execution passes
- **WHEN** every mapped selector appears once with a passing result
- **THEN** acceptance succeeds and pytest receives precisely the mapped selectors

#### Scenario: Adverse or incomplete execution fails
- **WHEN** pytest fails or the report is absent, skipped, failed, erroneous, duplicated or does not match the mapping
- **THEN** native acceptance fails

### Requirement: Preserve existing independently owned gates
The existing required quality matrix SHALL require the native result while preserving module-signature and customer-capsule prerequisites. This additional native acceptance SHALL not promote local evidence to protected review, replace independent security or claim the later public reviewer cutover.

#### Scenario: Native acceptance is a required prerequisite
- **WHEN** the native job does not pass
- **THEN** the quality prerequisite refuses and the existing signature and independent-review requirements remain present
