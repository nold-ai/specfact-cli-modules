## ADDED Requirements

### Requirement: Docs validation SHALL reject stale command and resource references
The modules-side docs validation workflow SHALL reject command examples that do not match implemented bundle commands and SHALL also reject stale references to migrated core-owned resource paths.

#### Scenario: Valid command example passes
- **GIVEN** a docs page references `specfact backlog ceremony standup`
- **WHEN** the validation runs
- **THEN** it finds a matching registration in the backlog package source
- **AND** the check passes

#### Scenario: Invalid command example fails
- **GIVEN** a docs page references `specfact backlog nonexistent`
- **WHEN** the validation runs
- **THEN** it reports the mismatch
- **AND** the check fails

#### Scenario: Legacy core-owned resource path reference fails
- **GIVEN** a docs page instructs users to fetch a migrated prompt or template from a legacy core-owned path
- **WHEN** the validation runs
- **THEN** it reports the stale resource reference
- **AND** the check fails
