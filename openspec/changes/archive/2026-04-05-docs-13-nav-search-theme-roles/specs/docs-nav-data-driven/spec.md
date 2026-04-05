## ADDED Requirements

### Requirement: Navigation data file
The sidebar navigation structure SHALL be defined in `docs/_data/nav.yml` as a YAML data file. Each top-level entry SHALL have a `section` name and either an `items` array (flat list) or a `bundles` array (collapsible groups). Each item SHALL have `title`, `url`, and optionally `expertise` fields.

#### Scenario: Nav data file defines all sections
- **WHEN** the `_data/nav.yml` file is loaded
- **THEN** it SHALL contain entries for all seven sections: Getting Started, Bundles, Workflows, Integrations, Team & Enterprise, Authoring, Reference

#### Scenario: Bundle section uses collapsible groups
- **WHEN** the Bundles section is defined in `nav.yml`
- **THEN** it SHALL use a `bundles` array with entries for Backlog, Project, Codebase, Code Review, Spec, and Govern, each containing an `items` array

### Requirement: Sidebar nav rendered from data
The sidebar navigation in `docs/_layouts/default.html` SHALL render navigation by including `docs/_includes/sidebar-nav.html` which iterates over `site.data.nav` using Liquid loops. Hardcoded navigation HTML SHALL be removed.

#### Scenario: Sidebar renders all nav items
- **WHEN** a page loads with the default layout
- **THEN** the sidebar SHALL display all sections and items defined in `nav.yml`

#### Scenario: Bundle sections render as collapsible details
- **WHEN** a bundle group is rendered
- **THEN** it SHALL use `<details>` HTML elements with the bundle name as `<summary>`

### Requirement: All bundle links point to actual pages
Every bundle navigation link SHALL point to an existing page URL, not to the generic `/reference/commands/` placeholder.

#### Scenario: Code Review bundle links
- **WHEN** the Code Review bundle section is expanded
- **THEN** it SHALL contain links to Overview, Run, Ledger, and Rules pages at their `/bundles/code-review/` paths

#### Scenario: Spec bundle links
- **WHEN** the Spec bundle section is expanded
- **THEN** it SHALL contain links to Overview, Validate, Generate Tests, and Mock pages at their `/bundles/spec/` paths

#### Scenario: Govern bundle links
- **WHEN** the Govern bundle section is expanded
- **THEN** it SHALL contain links to Overview, Enforce, and Patch pages at their `/bundles/govern/` paths

#### Scenario: Codebase bundle links
- **WHEN** the Codebase bundle section is expanded
- **THEN** it SHALL contain links to Overview, Sidecar Validation, Analyze, Drift, and Repro pages at their `/bundles/codebase/` paths

### Requirement: Active page highlighting
The sidebar SHALL highlight the currently active page by matching `page.url` against nav item URLs and applying a CSS active class.

#### Scenario: Current page is highlighted
- **WHEN** a user visits `/bundles/spec/validate/`
- **THEN** the Validate link in the Spec bundle section SHALL have the active CSS class applied
- **AND** the Spec bundle `<details>` element SHALL be in the open state

### Requirement: Team & Enterprise links use correct paths
The Team & Enterprise section SHALL link to pages under `/team-and-enterprise/` with all four deliverables from docs-11.

#### Scenario: Team & Enterprise navigation completeness
- **WHEN** the Team & Enterprise section is rendered
- **THEN** it SHALL contain links to Team Collaboration, Agile & Scrum Setup, Multi-Repo Setup, and Enterprise Configuration at their `/team-and-enterprise/` paths

### Requirement: Workflows section includes all docs-10 pages
The Workflows section SHALL include links to all workflow pages created in docs-10.

#### Scenario: Workflows navigation completeness
- **WHEN** the Workflows section is rendered
- **THEN** it SHALL contain links to Cross-Module Chains, Daily DevOps Routine, CI/CD Pipeline, and Brownfield Modernization in addition to existing workflow links

### Requirement: Breadcrumb navigation above content
Each page SHALL display a breadcrumb trail above the content area, derived from the page URL segments, to provide orientation and allow quick navigation to parent sections.

#### Scenario: Bundle command page shows breadcrumb trail
- **WHEN** a user visits `/bundles/spec/validate/`
- **THEN** a breadcrumb trail SHALL be displayed showing: Home > Bundles > Spec > Validate
- **AND** each breadcrumb segment except the current page SHALL be a clickable link
