# backlog-add Specification

## Purpose
TBD - created by archiving change backlog-02-migrate-core-commands. Update Purpose after archive.
## Requirements
### Requirement: Restore backlog add command functionality

The system SHALL provide `specfact backlog add` command that creates backlog items with the same functionality as the deleted backlog-core implementation. For Azure DevOps, the command SHALL use `work_item_type_mappings` from the field mapping configuration to resolve canonical types to provider-specific work item types.

#### Scenario: Add command creates GitHub issue
- **WHEN** the user runs `specfact backlog add --adapter github --project-id <owner/repo> --type story --title "Test" --body "Body"`
- **THEN** a GitHub issue is created with the specified title, body, and type
- **AND** the command outputs the created issue ID, key, and URL

#### Scenario: Add command creates ADO work item with custom type mapping
- **WHEN** the user runs `specfact backlog add --adapter ado --project-id <org/project> --type story --title "Test"`
- **AND** `.specfact/templates/backlog/field_mappings/ado_custom.yaml` contains `work_item_type_mappings.story: "Product Backlog Item"`
- **THEN** an ADO work item of type "Product Backlog Item" is created
- **AND** the command outputs the created work item ID, key, and URL

#### Scenario: Add command creates ADO work item with fallback type mapping
- **WHEN** the user runs `specfact backlog add --adapter ado --project-id <org/project> --type story --title "Test"`
- **AND** no custom `work_item_type_mappings` is configured
- **THEN** an ADO work item of type "User Story" is created (backward compatible fallback)
- **AND** the command outputs the created work item ID, key, and URL

#### Scenario: Interactive mode prompts for missing fields
- **WHEN** the user runs `specfact backlog add` without required fields
- **THEN** interactive prompts request title, body, type, and parent
- **AND** validation ensures parent exists before create

#### Scenario: DoR validation before create
- **WHEN** the user runs `specfact backlog add --check-dor`
- **THEN** the item is validated against `.specfact/dor.yaml` rules
- **AND** creation proceeds only if DoR criteria are met

#### Scenario: Ceremony alias works
- **WHEN** the user runs `specfact backlog ceremony add`
- **THEN** the command forwards to `specfact backlog add`
- **AND** all add options are available

### Requirement: Backlog add config updates SHALL preserve unrelated `.specfact` settings

Any `specfact backlog add` helper flow that updates `.specfact/backlog-config.yaml` or related field-mapping config SHALL preserve unrelated user-managed settings while updating only the declared SpecFact-managed subtree.

#### Scenario: Provider settings merge keeps unrelated config intact

- **WHEN** a backlog-add helper updates provider settings in `.specfact/backlog-config.yaml`
- **AND** the file already contains unrelated provider settings or user-managed metadata
- **THEN** the command SHALL preserve the unrelated settings
- **AND** SHALL update only the targeted provider settings subtree

#### Scenario: Mapping update preserves unrelated config state

- **WHEN** `specfact backlog map-fields` refreshes mapping metadata under `.specfact/templates/backlog/`
- **AND** the corresponding `.specfact/backlog-config.yaml` already contains unrelated settings
- **THEN** the command SHALL keep the unrelated settings intact
- **AND** SHALL NOT silently replace the full config file

