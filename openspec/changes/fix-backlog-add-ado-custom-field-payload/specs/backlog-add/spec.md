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
- **AND** mapped required custom fields from the configured ADO field-mapping file are included in the create payload

#### Scenario: Interactive mode prompts for missing fields
- **WHEN** the user runs `specfact backlog add` without required fields
- **THEN** interactive prompts request title, body, type, and parent
- **AND** validation ensures parent exists before create

#### Scenario: Interactive and non-interactive ADO create flows stay equivalent
- **WHEN** the user runs `specfact backlog add` for Azure DevOps with the same effective inputs in interactive and non-interactive modes
- **THEN** both flows resolve the same provider work item type
- **AND** both flows emit the same mapped required custom fields needed for create

#### Scenario: DoR validation before create
- **WHEN** the user runs `specfact backlog add --check-dor`
- **THEN** the item is validated against `.specfact/dor.yaml` rules
- **AND** creation proceeds only if DoR criteria are met

#### Scenario: Ceremony alias works
- **WHEN** the user runs `specfact backlog ceremony add`
- **THEN** the command forwards to `specfact backlog add`
- **AND** all add options are available
