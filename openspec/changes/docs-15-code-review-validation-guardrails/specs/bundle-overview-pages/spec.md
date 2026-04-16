# Bundle overview pages

## MODIFIED Requirements

### Requirement: Bundle overview links SHALL resolve as published URLs

Bundle overview pages SHALL use links that resolve correctly from the published overview permalink route, including "See also", prerequisite, deep-dive, and related-bundle links.

#### Scenario: Code Review overview links to run page

- **WHEN** the Code Review overview page is published at `/bundles/code-review/overview/`
- **THEN** its "Code review run" link resolves to `/bundles/code-review/run/`
- **AND** the link does not resolve to `/bundles/code-review/overview/run/`

#### Scenario: Cross-bundle overview link resolves

- **WHEN** a bundle overview page links to another bundle overview page
- **THEN** the link resolves to the target bundle's canonical published overview route
- **AND** docs validation fails if the link resolves to a route nested under the source overview page

### Requirement: Bundle overview-related links SHALL be covered by docs validation tests

The bundle overview docs test suite SHALL include coverage that fails when any overview page contains a body link that is valid by source-file path but broken under published permalink semantics.

#### Scenario: Source-valid but published-broken link is rejected

- **WHEN** an overview page links to a sibling page using a source-file-relative shorthand that would publish below the overview permalink
- **THEN** the overview link test reports the generated public route mismatch
- **AND** the test fails before the docs can be published
