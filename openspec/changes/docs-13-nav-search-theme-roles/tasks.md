# docs-13 Tasks

## 1. Data-Driven Navigation

- [x] 1.1 Create `docs/_data/nav.yml` with all seven sections, correct bundle links (Overview + command pages for all 6 bundles), correct Team & Enterprise paths, and complete Workflows section
- [x] 1.2 Create `docs/_includes/sidebar-nav.html` Liquid partial that renders nav from `site.data.nav` with `<details>` for bundles, active-page highlighting via `page.url`, and `data-expertise` attributes on `<li>` elements
- [x] 1.3 Update `docs/_layouts/default.html` to replace hardcoded sidebar nav with `{% include sidebar-nav.html %}`
- [x] 1.4 Fix `docs/index.md` homepage table: update Spec, Govern, Code Review, and Codebase deep-dive links to point to actual bundle command pages
- [x] 1.5 Add "Find Your Path" role-based entry cards section to `docs/index.md` with Solo Developer, Startup, Corporate, and Enterprise profiles

## 2. Light/Dark Theme Toggle

- [x] 2.1 Create `docs/assets/js/theme.js` — reads `localStorage` key `specfact-theme`, sets `data-theme` on `<html>`, provides toggle function
- [x] 2.2 Create `docs/_includes/theme-toggle.html` — toggle button with sun/moon SVG icons
- [x] 2.3 Update `docs/_layouts/default.html` to load `theme.js` in `<head>` and include theme toggle in header
- [x] 2.4 Refactor `docs/assets/main.scss` — replace single `:root` block with `[data-theme="dark"]` and `[data-theme="light"]` variable definitions; add `@media (prefers-color-scheme)` fallback
- [x] 2.5 Add light-mode Rouge syntax highlighting overrides to `main.scss`
- [x] 2.6 Refactor Mermaid initialization in `default.html` into theme-aware `initMermaid(theme)` function with separate `themeVariables` for light/dark

## 3. Client-Side Search

- [x] 3.1 Create `docs/assets/js/search-index.json` as Liquid template that generates JSON array from all pages with title, url, keywords, audience, expertise_level, and truncated content
- [x] 3.2 Create `docs/assets/js/search.js` — Lunr.js integration with lazy index loading, debounced input, field boosting (title:10, keywords:5, content:1), dropdown results with snippets and metadata pills
- [x] 3.3 Create `docs/_includes/search.html` — search input UI with placeholder and keyboard shortcut hint
- [x] 3.4 Update `docs/_layouts/default.html` to load Lunr.js CDN, include search partial in sidebar above nav, and load search.js

## 4. Expertise Filter

- [x] 4.1 Create `docs/_includes/expertise-filter.html` — compact dropdown with All/Beginner/Intermediate/Advanced options and visible-count indicator
- [x] 4.2 Create `docs/assets/js/filters.js` — reads `localStorage` key `specfact-expertise`, applies CSS filtering via `data-expertise` attributes, updates count indicator
- [x] 4.3 Update `docs/_layouts/default.html` to include expertise filter partial between search and nav, and load filters.js

## 5. Front Matter Enrichment

- [x] 5.1 Add `keywords`, `audience`, and `expertise_level` fields to all Getting Started pages (~7 files)
- [x] 5.2 Add front matter fields to all Bundle pages (~24 files across 6 bundles)
- [x] 5.3 Add front matter fields to all Workflow/Guide pages (~10 active workflow files)
- [x] 5.4 Add front matter fields to all Integration pages (~6 files)
- [x] 5.5 Add front matter fields to all Team & Enterprise pages (4 files)
- [x] 5.6 Add front matter fields to all Authoring pages (~7 files)
- [x] 5.7 Add front matter fields to all Reference pages (~14 files)

## 6. Theme Refinement & Breadcrumbs

- [x] 6.1 Create `docs/_includes/breadcrumbs.html` — derive breadcrumb trail from `page.url` segments
- [x] 6.2 Update `docs/_layouts/default.html` to include breadcrumbs above content area
- [x] 6.3 Refine `main.scss` — reduce sidebar visual weight, improve code block contrast with subtle left-border accent, cleaner `<details>` chevron animation, better table borders, search/filter/toggle styling for both themes

## 7. Validation & CI

- [x] 7.1 Extend `scripts/check-docs-commands.py` to validate all `_data/nav.yml` URL targets resolve to existing pages
- [x] 7.2 Verify Jekyll build succeeds locally with `cd docs && bundle exec jekyll build`
- [x] 7.3 Verify all sidebar links render correctly (no `/reference/commands/` placeholders remain)
- [x] 7.4 Verify light/dark toggle works and persists across page loads
- [x] 7.5 Verify search returns results for known keywords
- [x] 7.6 Verify expertise filter hides/shows nav items correctly
