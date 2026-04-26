# Backlog add requirements

## ADDED Requirements

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
