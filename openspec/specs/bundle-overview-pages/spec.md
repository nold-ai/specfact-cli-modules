# bundle-overview-pages Specification

## Purpose

Define requirements for official bundle overview pages on the modules documentation site: each official bundle has a single landing page that lists commands, prerequisites, quick examples, and bundle-owned resource setup guidance aligned with the mounted SpecFact CLI surface.
## Requirements
### Requirement: Bundle overview pages SHALL provide complete bundle entry points

Each official bundle SHALL have a single overview page that lists its commands, prerequisites, examples, and relevant bundle-owned resource setup guidance. The sidebar navigation SHALL link to each bundle's overview page as the first item in that bundle's collapsible section, and all command deep-dive pages SHALL be listed below the overview.

#### Scenario: Overview page lists all bundle commands

- **GIVEN** a bundle overview page such as `bundles/backlog/overview.md`
- **WHEN** a user reads the page
- **THEN** every registered command and subcommand for that bundle is listed
- **AND** each command has a brief description

#### Scenario: Overview page includes quick examples

- **GIVEN** a bundle overview page
- **WHEN** a user reads the page
- **THEN** at least one practical example is shown for each major command group

#### Scenario: Overview page explains bundle-owned resource setup when relevant

- **GIVEN** a bundle overview page for a bundle that ships prompts or workspace templates
- **WHEN** a user reads the page
- **THEN** the page explains which resources are bundled with that package
- **AND** it points to the supported setup flow such as `specfact init ide` or bundle-specific template/bootstrap commands

#### Scenario: Command examples match actual CLI

- **GIVEN** a command example in an overview page
- **WHEN** compared against the actual `specfact <command> --help` output
- **THEN** the command name, arguments, and key options match
- **AND** `tests/unit/docs/test_bundle_overview_cli_examples.py::test_validate_bundle_overview_cli_help_examples` exercises each quick-example line by invoking the corresponding bundle Typer app with `--help` (or an explicit `--help` normalization for lines that include runnable flags), failing when help output cannot be produced

#### Scenario: Sidebar links to overview and all command pages

- **GIVEN** the sidebar navigation for any bundle (Backlog, Project, Codebase, Spec, Govern, Code Review)
- **WHEN** the bundle section is expanded
- **THEN** the first link SHALL be the bundle's overview page
- **AND** subsequent links SHALL point to each command deep-dive page under that bundle's directory
- **AND** no link SHALL point to the generic `/reference/commands/` placeholder

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

