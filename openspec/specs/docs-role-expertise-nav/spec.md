# docs-role-expertise-nav Specification

## Purpose
TBD - created by archiving change docs-13-nav-search-theme-roles. Update Purpose after archive.
## Requirements
### Requirement: Expertise level filter in sidebar
A compact dropdown or pill filter SHALL be rendered in the sidebar between the search input and the navigation sections via `docs/_includes/expertise-filter.html`. Options: All, Beginner, Intermediate, Advanced.

#### Scenario: Filter defaults to All
- **WHEN** a user visits the site for the first time
- **THEN** the expertise filter SHALL be set to "All" and all nav items SHALL be visible

#### Scenario: Filter hides non-matching items
- **WHEN** the user selects "Beginner" from the expertise filter
- **THEN** nav items whose `expertise` field does not include "beginner" SHALL be hidden via CSS
- **AND** bundle `<details>` sections with no visible items SHALL also be hidden

#### Scenario: Filter persists across pages
- **WHEN** the user selects "Advanced" and navigates to another page
- **THEN** the filter SHALL still be set to "Advanced" (stored in `localStorage` under key `specfact-expertise`)

#### Scenario: Filtered count indicator
- **WHEN** the expertise filter is set to a value other than "All"
- **THEN** a small indicator SHALL show how many items are visible vs total (e.g., "12 of 45")

### Requirement: Front matter expertise and audience fields
All documentation pages SHALL have `keywords`, `audience`, and `expertise_level` fields in their front matter. These fields are arrays of strings.

#### Scenario: Getting started pages are tagged as beginner
- **WHEN** a page under `getting-started/` is inspected
- **THEN** its front matter SHALL include `expertise_level: [beginner]`

#### Scenario: Authoring pages are tagged as advanced
- **WHEN** a page under `authoring/` is inspected
- **THEN** its front matter SHALL include `expertise_level: [advanced]`

#### Scenario: Team & Enterprise pages target team and enterprise audiences
- **WHEN** a page under `team-and-enterprise/` is inspected
- **THEN** its front matter SHALL include `audience: [team, enterprise]`

### Requirement: Homepage role-based entry cards
The `index.md` homepage SHALL include a "Find Your Path" section with four role-based entry cards: Solo Developer, Small Team (Startup), Corporate Team, and Enterprise. Each card SHALL link to 3-4 curated pages most relevant to that profile.

#### Scenario: Solo developer card content
- **WHEN** the homepage is rendered
- **THEN** the Solo Developer card SHALL link to getting started, first steps, and a bundle quickstart tutorial

#### Scenario: Enterprise card content
- **WHEN** the homepage is rendered
- **THEN** the Enterprise card SHALL link to enterprise configuration, module signing, custom registries, and module security

### Requirement: Nav items carry expertise data attribute
Each nav item rendered in the sidebar SHALL have a `data-expertise` HTML attribute containing the comma-separated expertise levels from `nav.yml`, enabling CSS-based filtering.

#### Scenario: Nav item data attribute
- **WHEN** a nav item with `expertise: [beginner, intermediate]` is rendered
- **THEN** the `<li>` element SHALL have `data-expertise="beginner,intermediate"`

