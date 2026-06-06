# Modules Docs Command Validation

## Purpose

Define requirements for CI-based validation of command examples and resource references across the modules documentation site.
## Requirements
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

### Requirement: Module docs command examples are validated

Module documentation command examples SHALL be validated against the generated module command overview.

#### Scenario: Legacy flat sync command fails validation

- **GIVEN** module docs, help examples, prompts, Jinja2 templates, YAML/JSON resources, or text guidance contain `specfact sync bridge`
- **WHEN** docs command validation runs
- **THEN** validation fails unless the reference is explicitly marked as historical migration material
- **AND** the finding identifies `specfact project sync bridge` as the canonical command when appropriate.

#### Scenario: Prompt validators do not whitelist removed flat mounts

- **GIVEN** a validator scans module prompt resources
- **WHEN** it builds the command contract
- **THEN** it uses generated module command overview data
- **AND** it does not accept removed flat mounts such as `specfact import`, `specfact sync`, `specfact plan`, or `specfact migrate` as canonical command groups.

#### Scenario: Invalid option ordering fails validation

- **GIVEN** docs or prompts contain `specfact code import <bundle> --repo .`
- **WHEN** validation runs
- **THEN** the validator rejects the example if the command contract does not support that order
- **AND** the finding includes the canonical supported command form.

### Requirement: Docs validation SHALL validate published-route body links

The modules docs validation command SHALL validate internal links in authored page bodies using the page's published permalink route as the URL base, and SHALL fail when a link resolves to a route that is not backed by a published page or an accepted redirect route.

#### Scenario: Overview relative link fails under published route semantics

- **WHEN** a page with permalink `/bundles/code-review/overview/` contains a body link `run/`
- **THEN** docs validation resolves the link as `/bundles/code-review/overview/run/`
- **AND** docs validation reports a `published-link` finding when that route is not published or redirected
- **AND** the validation command exits non-zero

#### Scenario: Published-route-safe link passes

- **WHEN** a page with permalink `/bundles/code-review/overview/` links to `/bundles/code-review/run/`
- **THEN** docs validation resolves the link to the published Code Review run page
- **AND** no `published-link` finding is emitted for that link

### Requirement: Docs validation SHALL reject incomplete published page front matter

The modules docs validation command SHALL reject published Markdown pages whose front matter is missing required route and display metadata, including `layout`, `title`, and `permalink`, unless the page has an explicit documented exemption recognized by the validator.

#### Scenario: Redirect page missing title fails

- **WHEN** a published Markdown redirect page has `layout` and `permalink` but no `title`
- **THEN** docs validation reports a `frontmatter` finding for the missing `title`
- **AND** the validation command exits non-zero

#### Scenario: Complete published page passes front matter validation

- **WHEN** a published Markdown page defines `layout`, `title`, and `permalink`
- **THEN** docs validation accepts the page front matter
- **AND** no `frontmatter` finding is emitted for that page

### Requirement: Docs validation SHALL expose stable finding categories

The modules docs validation command SHALL emit stable category names for each class of documentation defect so CI logs, pre-commit output, and tests can assert category coverage without matching brittle prose.

#### Scenario: Multiple docs defect categories are reported together

- **WHEN** docs validation finds an unknown command example, a broken published route link, and incomplete front matter
- **THEN** the output includes `command`, `published-link`, and `frontmatter` categories
- **AND** the validation command exits non-zero after reporting all discovered docs findings

### Requirement: Docs validation SHALL detect docs build dependency drift

The modules docs validation workflow SHALL include a docs build dependency health check that fails when the checked-in Jekyll dependency lock cannot be installed for the docs site.

#### Scenario: Stale Gemfile lock fails docs dependency validation

- **WHEN** the docs dependency install command cannot resolve a locked gem version from the configured sources
- **THEN** the docs workflow reports a `docs-build-dependency` failure
- **AND** Pages publication does not proceed as healthy

### Requirement: Bundle permalink pages SHALL validate parent-segment links against browser routes

For pages whose canonical published route is under `/bundles/`, docs validation SHALL treat Markdown links whose path contains parent-directory segments (`..`) as unsafe unless the filesystem-resolved target file matches the target resolved from the page permalink using browser URL rules.

#### Scenario: Deep bundle overview rejects filesystem-only match for `../../` links

- **WHEN** a bundle overview page is published under `/bundles/<bundle>/overview/` (or another deep `/bundles/` permalink)
- **AND** its body uses a `../` or `../../` link that reaches a markdown file on disk but resolves to a different or missing public route
- **THEN** docs validation reports a `published-link` finding (missing route or route mismatch)
- **AND** the validation command exits non-zero

