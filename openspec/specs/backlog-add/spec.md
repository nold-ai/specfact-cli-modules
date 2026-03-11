# backlog-add Specification

## Purpose
TBD - created by archiving change backlog-02-migrate-core-commands. Update Purpose after archive.
## Requirements
### Requirement: Restore backlog add command functionality

`specfact backlog add` SHALL build valid provider payloads for mapped required provider fields.

#### Scenario: map-fields persists required mapped field type metadata
- **WHEN** `specfact backlog map-fields` discovers required ADO fields for a selected work item type
- **THEN** it persists required field type metadata for those field references in provider settings
- **AND** metadata is keyed by work item type so later create commands can resolve field types.

#### Scenario: map-fields clears stale selected-type field metadata
- **WHEN** `specfact backlog map-fields` is rerun for a selected ADO work item type
- **AND** the latest metadata no longer includes persisted field types for that selected type
- **THEN** the stored required field type metadata for that selected work item type is removed
- **AND** metadata for other work item types remains unchanged.

#### Scenario: add coerces mapped required boolean provider fields
- **WHEN** `specfact backlog add` resolves a mapped required field whose persisted metadata type is `boolean`
- **AND** the user passes a provider override such as `--provider-field Custom.Toggle=true`
- **THEN** the outgoing ADO provider payload contains the boolean value `true` (not a string).

#### Scenario: add rejects invalid typed values before provider calls
- **WHEN** `specfact backlog add --non-interactive` resolves a mapped required field whose persisted metadata type is `boolean`
- **AND** the user passes an invalid boolean text value
- **THEN** the CLI exits with a validation error that names the mapped field
- **AND** no provider create call is made.

#### Scenario: add rejects invalid picklist values before provider calls
- **WHEN** `specfact backlog add --non-interactive` resolves a mapped required field whose persisted metadata contains allowed picklist values
- **AND** the user passes a provider override value outside that allowed set
- **THEN** the CLI exits with a validation error that names the mapped field and allowed values
- **AND** no provider create call is made.

