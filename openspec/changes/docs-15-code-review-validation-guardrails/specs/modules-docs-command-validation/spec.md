# ADDED Requirements

## Requirement: Docs validation SHALL validate published-route body links

The modules docs validation command SHALL validate internal links in authored page bodies using the page's published permalink route as the URL base, and SHALL fail when a link resolves to a route that is not backed by a published page or an accepted redirect route.

### Scenario: Overview relative link fails under published route semantics

- **WHEN** a page with permalink `/bundles/code-review/overview/` contains a body link `run/`
- **THEN** docs validation resolves the link as `/bundles/code-review/overview/run/`
- **AND** docs validation reports a `published-link` finding when that route is not published or redirected
- **AND** the validation command exits non-zero

### Scenario: Published-route-safe link passes

- **WHEN** a page with permalink `/bundles/code-review/overview/` links to `/bundles/code-review/run/`
- **THEN** docs validation resolves the link to the published Code Review run page
- **AND** no `published-link` finding is emitted for that link

## Requirement: Docs validation SHALL reject incomplete published page front matter

The modules docs validation command SHALL reject published Markdown pages whose front matter is missing required route and display metadata, including `layout`, `title`, and `permalink`, unless the page has an explicit documented exemption recognized by the validator.

### Scenario: Redirect page missing title fails

- **WHEN** a published Markdown redirect page has `layout` and `permalink` but no `title`
- **THEN** docs validation reports a `frontmatter` finding for the missing `title`
- **AND** the validation command exits non-zero

### Scenario: Complete published page passes front matter validation

- **WHEN** a published Markdown page defines `layout`, `title`, and `permalink`
- **THEN** docs validation accepts the page front matter
- **AND** no `frontmatter` finding is emitted for that page

## Requirement: Docs validation SHALL expose stable finding categories

The modules docs validation command SHALL emit stable category names for each class of documentation defect so CI logs, pre-commit output, and tests can assert category coverage without matching brittle prose.

### Scenario: Multiple docs defect categories are reported together

- **WHEN** docs validation finds an unknown command example, a broken published route link, and incomplete front matter
- **THEN** the output includes `command`, `published-link`, and `frontmatter` categories
- **AND** the validation command exits non-zero after reporting all discovered docs findings

## Requirement: Docs validation SHALL detect docs build dependency drift

The modules docs validation workflow SHALL include a docs build dependency health check that fails when the checked-in Jekyll dependency lock cannot be installed for the docs site.

### Scenario: Stale Gemfile lock fails docs dependency validation

- **WHEN** the docs dependency install command cannot resolve a locked gem version from the configured sources
- **THEN** the docs workflow reports a `docs-build-dependency` failure
- **AND** Pages publication does not proceed as healthy
