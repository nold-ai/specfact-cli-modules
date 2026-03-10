# registry-publish-consistency Specification

## Purpose
TBD - created by archiving change registry-republish-outdated-bundles. Update Purpose after archive.
## Requirements
### Requirement: Publish Workflow Must Include Registry-Outdated Bundles

The modules publish workflow SHALL include any bundle whose manifest version is newer than the selected registry baseline, even if that bundle was not part of the current push diff.

#### Scenario: Changed bundle is published as before
- **WHEN** a push changes files under `packages/specfact-backlog/`
- **THEN** the workflow includes `specfact-backlog` in the publish candidate set.

#### Scenario: Outdated bundle is added even when absent from diff
- **WHEN** a bundle manifest version is greater than the version in the target registry baseline
- **AND** that bundle is not present in the current push diff
- **THEN** the workflow still includes that bundle in the publish candidate set
- **AND** the existing automated registry publish PR is prepared for it.

### Requirement: Version Comparison Must Use An Explicit Registry Baseline

The modules publish workflow SHALL compare bundle manifest versions against an explicit registry baseline instead of assuming the current checkout reflects the exposed registry state.

#### Scenario: Default baseline uses exposed branch registry
- **WHEN** the workflow runs without an override
- **THEN** it compares bundle manifest versions against the configured exposed-branch registry baseline
- **AND** the comparison result drives whether a bundle is considered outdated.

#### Scenario: Bundle at registry version is not republished
- **WHEN** a bundle manifest version is equal to the version in the target registry baseline
- **THEN** the workflow does not add that bundle solely from the outdated-bundle scan
- **AND** it remains excluded unless it is otherwise selected by direct change handling.

#### Scenario: Dev publish compares against dev registry state
- **WHEN** the workflow runs from the `dev` branch
- **THEN** it uses `dev` as the effective registry baseline for the outdated-bundle scan
- **AND** it does not reopen an automated publish PR solely because `main` is behind `dev`.

### Requirement: Automated Publish PR Must Report Why A Bundle Was Included

The automated registry publish PR flow SHALL distinguish bundles selected from the current diff from bundles selected to repair stale registry state.

#### Scenario: Workflow logs inclusion reason
- **WHEN** the workflow resolves the final publish bundle set
- **THEN** it records whether each bundle was selected because it changed in the push, because the registry was outdated, or both
- **AND** maintainers can see why the auto publish PR was opened.

