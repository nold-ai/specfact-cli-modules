# speckit-backlog-extension-sync Specification

## Purpose
TBD - created by archiving change speckit-03-change-proposal-bridge. Update Purpose after archive.
## Requirements
### Requirement: Detect spec-kit backlog extension issue mappings

The system SHALL detect when spec-kit backlog extensions (Jira, ADO, Linear, GitHub Projects, Trello) have created issues from feature specs, and import those issue references.

#### Scenario: Detect Jira issue references from spec-kit

- **GIVEN** a spec-kit repository with the `jira` extension detected in `ToolCapabilities.extension_commands`
- **AND** feature `tasks.md` contains references matching pattern `[A-Z]+-\d+` (e.g., `PROJ-123`)
- **WHEN** `SpecKitBacklogSync.detect_issue_mappings(feature_path)` is called
- **THEN** returns a list of issue mapping objects with `tool="jira"`, `issue_ref="PROJ-123"`, and `source="speckit-extension"`

#### Scenario: Detect Azure DevOps work item references

- **GIVEN** a spec-kit repository with the `azure-devops` extension detected
- **AND** feature `tasks.md` contains references matching pattern `AB#\d+` (e.g., `AB#456`)
- **WHEN** `SpecKitBacklogSync.detect_issue_mappings(feature_path)` is called
- **THEN** returns issue mapping objects with `tool="ado"` and `issue_ref="AB#456"`

#### Scenario: Detect Linear issue references

- **GIVEN** a spec-kit repository with the `linear` extension detected
- **AND** feature `tasks.md` contains references matching pattern `[A-Z]+-\d+` (e.g., `ENG-789`)
- **WHEN** `SpecKitBacklogSync.detect_issue_mappings(feature_path)` is called
- **THEN** returns issue mapping objects with `tool="linear"` and matched references

#### Scenario: No backlog extension present

- **GIVEN** a spec-kit repository where `ToolCapabilities.extension_commands` does not contain any backlog extension
- **WHEN** `SpecKitBacklogSync.detect_issue_mappings(feature_path)` is called
- **THEN** returns an empty list
- **AND** no issue reference scanning is performed

### Requirement: Prevent duplicate issue creation during backlog sync

The system SHALL skip issue creation for items that already have spec-kit backlog extension mappings.

#### Scenario: Skip duplicate Jira issue creation

- **GIVEN** a SpecFact backlog sync targeting Jira
- **AND** spec-kit backlog extension has already created `PROJ-123` for a feature task
- **AND** the issue mapping has been imported via `detect_issue_mappings()`
- **WHEN** SpecFact backlog sync processes the same task
- **THEN** the sync skips issue creation for that task
- **AND** logs that the issue already exists via spec-kit extension
- **AND** links the existing issue reference in SpecFact's tracking

#### Scenario: Create issue when no spec-kit mapping exists

- **GIVEN** a SpecFact backlog sync targeting Jira
- **AND** no spec-kit backlog extension mapping exists for a given task
- **WHEN** SpecFact backlog sync processes that task
- **THEN** the sync creates a new issue as normal

