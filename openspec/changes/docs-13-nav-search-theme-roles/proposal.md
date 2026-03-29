## Why

The docs-06 through docs-12 changes created per-bundle command pages, overview pages, workflow consolidation, and team/enterprise documentation, but the sidebar navigation in `default.html` was never updated to link to these new pages. Three bundles (Code Review, Spec, Govern) still point to a generic `/reference/commands/` page, Codebase is missing three command pages, Team & Enterprise links to stale paths, and the Workflows section omits four new guides. The homepage `index.md` has the same stale-link problem. Beyond broken navigation, the site lacks a light/dark mode toggle, client-side search, and role/expertise-based navigation that would help different user profiles (solo developer through enterprise) find relevant content quickly.

## What Changes

- **Fix all broken sidebar links**: update Code Review, Spec, Govern, and Codebase bundle sections to link to their actual command pages instead of `/reference/commands/`; add Overview links to every bundle; fix Team & Enterprise stale paths; add missing Workflow pages (cross-module-chains, daily-devops-routine, ci-cd-pipeline, brownfield-modernization)
- **Fix homepage stale links**: update `index.md` bundle table deep-dive links for Spec, Govern, and Code Review
- **Add module changelog visibility on the homepage**: expose recent module release history on the modules overview from a canonical structured release-history source that is updated as part of each module publish
- **Extract navigation into data file**: move hardcoded sidebar HTML into `_data/nav.yml` rendered via `_includes/sidebar-nav.html` to prevent future drift
- **Add light/dark mode toggle**: dual CSS theme with `[data-theme]` attribute, localStorage persistence, theme-aware Mermaid re-rendering, and light-mode Rouge syntax highlighting
- **Add client-side search**: Lunr.js-powered search with a Jekyll-generated index from front matter metadata (title, keywords, audience, expertise_level); keyboard shortcuts (Ctrl+K / Cmd+K); dropdown results with snippets
- **Add role/expertise navigation**: sidebar expertise-level filter (beginner / intermediate / advanced); homepage "Find Your Path" section with role-based entry cards (solo, startup, corporate, enterprise)
- **Enrich front matter metadata**: add `keywords`, `audience`, and `expertise_level` fields to all doc pages
- **Refine theme**: cleaner sidebar visual weight, improved code block contrast, active-page highlighting, breadcrumbs for orientation, support for both light and dark modes

## Capabilities

### New Capabilities
- `docs-nav-data-driven`: data-driven sidebar navigation via `_data/nav.yml` with correct links for all bundles, workflows, team/enterprise, and reference pages
- `docs-theme-toggle`: light/dark mode toggle with localStorage persistence, dual CSS theme, theme-aware Mermaid and syntax highlighting
- `docs-client-search`: Lunr.js client-side search powered by front matter metadata index, keyboard shortcuts, and result snippets
- `docs-role-expertise-nav`: expertise-level sidebar filter and homepage role-based entry cards for solo/startup/corporate/enterprise profiles
- `docs-module-changelog`: homepage or overview surfaces recent per-module release history from a canonical publish-driven release-history source

### Modified Capabilities
- `bundle-overview-pages`: sidebar links updated to point to actual overview and command pages instead of generic commands reference
- `modules-homepage-overview`: bundle overview section enhanced to expose recent per-module release history instead of only bundle links
- `cross-module-workflow-docs`: sidebar Workflows section updated to include all docs-10 deliverables
- `team-setup-docs`: sidebar Team & Enterprise section updated to use correct `/team-and-enterprise/` paths and include all docs-11 deliverables
- `modules-docs-command-validation`: CI validation script may need updates to cover new `_data/nav.yml` link targets and enriched front matter fields

## Impact

- **Files modified**: `docs/_layouts/default.html`, `docs/assets/main.scss`, `docs/_config.yml`, `docs/index.md`, ~50+ `docs/**/*.md` (front matter only)
- **New files**: `docs/_data/nav.yml`, `docs/_includes/{sidebar-nav,search,theme-toggle,expertise-filter,breadcrumbs}.html`, `docs/assets/js/{theme,search,filters}.js`, `docs/assets/js/search-index.json`, plus a structured release-history data source if required
- **Dependencies**: Lunr.js loaded from CDN (~8 KB gzipped)
- **No URL changes**: all existing `redirect_from` entries preserved; cross-site links from `docs.specfact.io` unaffected
- **Cross-site**: `docs/reference/documentation-url-contract.md` unchanged
