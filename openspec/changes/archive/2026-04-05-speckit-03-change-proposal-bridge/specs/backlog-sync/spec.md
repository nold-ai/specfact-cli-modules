## ADDED Requirements

### Requirement: Backlog sync checks for existing external issue mappings before creation

The backlog sync system SHALL check for existing issue mappings from external tools (including spec-kit extensions) before creating new backlog issues, to prevent duplicates.

#### Scenario: Backlog sync with spec-kit extension mappings available

- **GIVEN** a project with both SpecFact backlog sync and spec-kit backlog extensions active
- **AND** `SpecKitBacklogSync.detect_issue_mappings()` has returned mappings for some tasks
- **WHEN** `specfact backlog sync` runs for the project
- **THEN** for each task, the sync checks imported issue mappings first
- **AND** skips creation for tasks with existing mappings
- **AND** creates new issues only for unmapped tasks
- **AND** the sync summary reports both skipped (already-mapped) and newly-created issues

#### Scenario: Backlog sync without spec-kit extensions

- **GIVEN** a project without spec-kit or without backlog extensions
- **WHEN** `specfact backlog sync` runs
- **THEN** the sync creates issues for all tasks as before (no behavior change)
- **AND** no spec-kit extension detection is attempted
