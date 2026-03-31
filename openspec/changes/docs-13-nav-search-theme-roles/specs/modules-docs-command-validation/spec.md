## MODIFIED Requirements

### Requirement: Docs validation SHALL reject stale command and resource references

The modules-side docs validation workflow SHALL reject command examples across published module docs that do not match implemented bundle commands and SHALL also reject stale references to migrated core-owned resource paths.

#### Scenario: Valid command example passes

- **GIVEN** a docs page references `specfact backlog ceremony standup`
- **WHEN** the validation runs
- **THEN** it finds a matching registration in the backlog package source
- **AND** the check passes

#### Scenario: Published non-bundle docs are validated too

- **GIVEN** a published module docs page outside `docs/bundles/` contains a command example
- **WHEN** the validation runs
- **THEN** the command example is checked against the implemented mounted command tree
- **AND** stale former command forms are rejected the same way as bundle reference pages

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

### Requirement: Published module docs SHALL stay warning-free in docs review

Published module docs SHALL include Jekyll front matter and valid internal links so the modules docs review run does not rely on warning allowlists for stale pages.

#### Scenario: Previously tolerated stale docs warnings are removed

- **GIVEN** a published modules docs page was previously missing front matter or linked to a removed former docs target
- **WHEN** the docs review suite runs
- **THEN** the page is published with required front matter
- **AND** its internal links resolve to current canonical modules docs routes
- **AND** the docs review run completes without warnings

### Requirement: Nav data file link targets SHALL be validated

The docs validation script SHALL verify that every URL in `_data/nav.yml` corresponds to an existing page with a matching permalink.

#### Scenario: Nav link to non-existent page fails validation

- **GIVEN** `_data/nav.yml` contains a link to `/bundles/spec/nonexistent/`
- **WHEN** the validation runs
- **THEN** it reports that no page exists with permalink `/bundles/spec/nonexistent/`
- **AND** the check fails

#### Scenario: All nav links resolve to existing pages

- **GIVEN** `_data/nav.yml` contains all current navigation links
- **WHEN** the validation runs
- **THEN** every URL in the nav file matches an existing page's permalink
- **AND** the check passes
