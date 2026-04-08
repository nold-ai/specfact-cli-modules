# docs-client-search Specification

## Purpose
TBD - created by archiving change docs-13-nav-search-theme-roles. Update Purpose after archive.
## Requirements
### Requirement: Search index generation
A Jekyll Liquid template at `docs/assets/js/search-index.json` SHALL generate a JSON array at build time containing one entry per page with fields: `url`, `title`, `keywords` (from front matter), `audience`, `expertise_level`, and `content` (page content truncated to the first 200 words with HTML tags stripped).

#### Scenario: Search index contains all pages
- **WHEN** the Jekyll site is built
- **THEN** the generated `search-index.json` SHALL contain entries for every page that has a `title` in its front matter

#### Scenario: Search index includes front matter metadata
- **WHEN** a page has `keywords: [backlog, refinement, sprint]` in its front matter
- **THEN** its search index entry SHALL include those keywords in the `keywords` field

### Requirement: Search UI in sidebar
A search input field SHALL be rendered in the sidebar above the navigation sections via `docs/_includes/search.html`. The search input SHALL have placeholder text "Search docs... (Ctrl+K)".

#### Scenario: Search input is visible
- **WHEN** any page loads
- **THEN** a search input field SHALL appear at the top of the sidebar, above all navigation sections

#### Scenario: Keyboard shortcut focuses search
- **WHEN** the user presses Ctrl+K (or Cmd+K on macOS)
- **THEN** the search input SHALL receive focus

### Requirement: Lunr.js search integration
The search SHALL use Lunr.js loaded from CDN. The search index SHALL be lazy-loaded on first search input focus. Lunr SHALL be configured with field boosting: title at 10x, keywords at 5x, content at 1x.

#### Scenario: First search triggers index load
- **WHEN** the user focuses the search input for the first time
- **THEN** the `search-index.json` SHALL be fetched and a Lunr index SHALL be built

#### Scenario: Search results appear on input
- **WHEN** the user types at least 2 characters in the search input
- **THEN** a dropdown SHALL appear below the search input showing matching results with page title and a content snippet

#### Scenario: No results message
- **WHEN** the user's query matches no pages
- **THEN** the dropdown SHALL show "No results found"

### Requirement: Search result navigation
The search results dropdown SHALL support keyboard navigation with arrow keys and Enter to follow a link. Clicking a result SHALL navigate to that page.

#### Scenario: Arrow key navigation
- **WHEN** the search dropdown is open and the user presses the down arrow
- **THEN** the next result SHALL be highlighted

#### Scenario: Enter navigates to result
- **WHEN** a result is highlighted and the user presses Enter
- **THEN** the browser SHALL navigate to that result's URL

### Requirement: Search results show metadata tags
Each search result SHALL display matching front matter tags (audience, expertise_level) as small pills/badges alongside the title.

#### Scenario: Result shows audience tag
- **WHEN** a search result is for a page with `audience: [team, enterprise]`
- **THEN** the result SHALL display "team" and "enterprise" as tag pills

