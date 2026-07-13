# backlog-adapter Specification

## Purpose
TBD - created by archiving change requirements-02-module-commands. Update Purpose after archive.
## Requirements
### Requirement: Backlog Adapter

The system SHALL expose source-attributed backlog requirement snippets to
requirements import workflows.

#### Scenario: Adapter returns acceptance criteria payload for import

- **GIVEN** a backlog item selected for requirement context import
- **WHEN** requirements import receives adapter source fields
- **THEN** title, description, acceptance-criteria text, and item identity are available
- **AND** normalization proceeds without provider-specific parsing in command handlers.

#### Scenario: Missing acceptance criteria is surfaced explicitly

- **GIVEN** a backlog item with no acceptance criteria
- **WHEN** normalization runs
- **THEN** the item is reported as incomplete input
- **AND** command output includes the backlog item identifier.

