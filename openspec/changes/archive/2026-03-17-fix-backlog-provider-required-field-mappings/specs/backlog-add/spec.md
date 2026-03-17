## MODIFIED Requirements

### Requirement: Restore backlog add command functionality

The system SHALL provide `specfact backlog add` command that creates backlog items with the same functionality as the deleted backlog-core implementation.

#### Scenario: Add command creates GitHub issue
- **WHEN** the user runs `specfact backlog add --adapter github --project-id <owner/repo> --type story --title "Test" --body "Body"`
- **THEN** a GitHub issue is created with the specified title, body, and type
- **AND** the command outputs the created issue ID, key, and URL

#### Scenario: Add command creates ADO work item
- **WHEN** the user runs `specfact backlog add --adapter ado --project-id <org/project> --type story --title "Test"`
- **THEN** an ADO work item is created with the specified title and resolved provider work item type
- **AND** required mapped provider fields are resolved from persisted `specfact backlog map-fields` configuration before payload assembly

#### Scenario: Explicit command-line values override resolved provider mapping defaults
- **WHEN** persisted `specfact backlog map-fields` configuration resolves a mapped provider field for `specfact backlog add`
- **AND** the user supplies an explicit canonical or provider-field override on the command line
- **THEN** the explicit command-line value overrides the resolved default for the outgoing provider payload

#### Scenario: Interactive mode prompts for unresolved required mapped provider fields
- **WHEN** the user runs `specfact backlog add` interactively for a provider whose persisted mapping config declares required mapped fields
- **AND** a required mapped value is still unresolved after applying config defaults and explicit overrides
- **THEN** the command prompts for the missing value before calling the provider API

#### Scenario: Non-interactive mode fails before provider call when required mapped fields are unresolved
- **WHEN** the user runs `specfact backlog add --non-interactive`
- **AND** a required mapped provider field remains unresolved after applying config defaults and explicit overrides
- **THEN** the command exits with a validation error that identifies the missing mapped field
- **AND** no provider create call is attempted

#### Scenario: Interactive and non-interactive provider create flows stay equivalent
- **WHEN** the user runs `specfact backlog add` with the same effective inputs in interactive and non-interactive modes
- **THEN** both flows resolve the same provider work item type
- **AND** both flows emit the same required mapped provider fields needed for create

#### Scenario: DoR validation before create
- **WHEN** the user runs `specfact backlog add --check-dor`
- **THEN** the item is validated against `.specfact/dor.yaml` rules
- **AND** creation proceeds only if DoR criteria are met

#### Scenario: Ceremony alias works
- **WHEN** the user runs `specfact backlog ceremony add`
- **THEN** the command forwards to `specfact backlog add`
- **AND** all add options are available
