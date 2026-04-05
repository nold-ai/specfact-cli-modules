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

