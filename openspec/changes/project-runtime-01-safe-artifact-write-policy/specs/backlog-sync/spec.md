# Backlog sync requirements

## ADDED Requirements

### Requirement: Backlog sync SHALL distinguish managed `.specfact` state from external output targets

Any `specfact backlog sync` local artifact path SHALL distinguish between fully owned managed state under `.specfact` and explicit output targets outside `.specfact`.

#### Scenario: Default managed baseline state updates deterministically

- **WHEN** backlog sync updates its default baseline state under `.specfact`
- **THEN** the command MAY rewrite that managed artifact deterministically
- **AND** SHALL treat it as SpecFact-managed state rather than a user-owned external file

#### Scenario: Explicit external baseline target is not silently overwritten

- **WHEN** backlog sync is configured to write a baseline or comparable output path outside `.specfact`
- **AND** the target file already exists
- **THEN** the command SHALL fail safe, merge safely, or require explicit replacement according to the declared ownership mode
- **AND** SHALL NOT silently overwrite the existing user-owned file
