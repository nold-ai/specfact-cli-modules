## MODIFIED Requirements

### Requirement: Restore backlog add command functionality

`specfact backlog add` must build valid provider payloads for mapped required provider fields.

#### Scenario: map-fields persists required mapped field type metadata
- **WHEN** `specfact backlog map-fields` discovers required ADO fields for a selected work item type
- **THEN** it persists required field type metadata for those field references in provider settings
- **AND** metadata is keyed by work item type so later create commands can resolve field types.

#### Scenario: add coerces mapped required boolean provider fields
- **WHEN** `specfact backlog add` resolves a mapped required field whose persisted metadata type is `boolean`
- **AND** the user passes a provider override such as `--provider-field Custom.Toggle=true`
- **THEN** the outgoing ADO provider payload contains the boolean value `true` (not a string).

#### Scenario: add rejects invalid typed values before provider calls
- **WHEN** `specfact backlog add --non-interactive` resolves a mapped required field whose persisted metadata type is `boolean`
- **AND** the user passes an invalid boolean text value
- **THEN** the CLI exits with a validation error that names the mapped field
- **AND** no provider create call is made.
