## MODIFIED Requirements

### Requirement: Restore backlog sync command functionality
The system SHALL provide `specfact backlog sync` command for bidirectional backlog synchronization, and related governance workflows SHALL be able to resolve current Epic and Feature planning metadata from the repo-local hierarchy cache before performing manual GitHub lookups.

#### Scenario: Sync from OpenSpec to backlog

- **WHEN** the user runs `specfact backlog sync --adapter github --project-id <repo>`
- **THEN** OpenSpec changes are exported to GitHub issues
- **AND** state mapping preserves status semantics

#### Scenario: Bidirectional sync with cross-adapter
- **WHEN** the user runs sync with cross-adapter configuration
- **THEN** state is mapped between adapters using canonical status
- **AND** lossless round-trip preserves content

#### Scenario: Sync with bundle integration
- **WHEN** sync is run within an OpenSpec bundle context
- **THEN** synced items update bundle state and source tracking

#### Scenario: Ceremony alias works
- **WHEN** the user runs `specfact backlog ceremony sync`
- **THEN** the command forwards to `specfact backlog sync`

#### Scenario: Cache-first hierarchy lookup for parent issue assignment
- **GIVEN** a contributor needs a parent Feature or Epic while preparing GitHub sync metadata
- **WHEN** the local hierarchy cache is present and current
- **THEN** the contributor can resolve the parent relationship from the cache without an additional GitHub lookup
- **AND** the sync script is rerun only when the cache is stale or missing

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
