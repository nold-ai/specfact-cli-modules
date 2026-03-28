## Context

The modules documentation site (`modules.specfact.io`) is a Jekyll 4.3 static site using the Minima 2.5 theme with heavy CSS customization. The sidebar navigation is hardcoded in `docs/_layouts/default.html` (265 lines). Six OpenSpec changes (docs-06 through docs-12) created ~24 new markdown pages across bundles, workflows, and team/enterprise sections, but the sidebar HTML was never updated to link to them. Three bundle sections (Code Review, Spec, Govern) link to a generic `/reference/commands/` placeholder. The homepage `index.md` has the same stale links.

The site is dark-mode-only (despite `skin: auto` in minima config), has no search functionality, and offers no way for users to filter content by their role or expertise level. The current styling, while functional, is visually heavy with high-contrast cyan accents that can be distracting for extended reading.

Key constraints: Jekyll static site (no server-side rendering), existing `redirect_from` entries must be preserved, cross-site links from `docs.specfact.io` must not break, and the SpecFact brand identity (cyan/teal accent on dark navy) must be maintained.

## Goals / Non-Goals

**Goals:**
- Fix every broken or stale sidebar and homepage link
- Make navigation data-driven to prevent future sidebar drift
- Add professional light/dark mode toggle with SpecFact brand colors
- Add client-side keyword search over front matter metadata
- Add expertise-level filtering and role-based homepage entry points
- Improve overall readability and reduce visual distraction
- Active-page highlighting and breadcrumbs for orientation

**Non-Goals:**
- Changing any existing page URLs or permalink structures
- Server-side search or external search service integration (Algolia, etc.)
- Restructuring the information architecture (already done in docs-06)
- Adding new documentation content beyond navigation/UX improvements
- Modifying the specfact-cli docs site (`docs.specfact.io`)

## Decisions

### D1: Data-driven navigation via `_data/nav.yml`

**Choice**: Extract all sidebar links into `docs/_data/nav.yml` and render via `docs/_includes/sidebar-nav.html` using Liquid loops.

**Why over hardcoded HTML**: The root cause of the broken links is that docs-09/10/11 created pages but nobody updated the hardcoded sidebar. A data file is easier to review, diff, and validate in CI. The `check-docs-commands.py` script can be extended to verify nav.yml targets exist.

**Why over Jekyll's built-in collection navigation**: Minima's auto-nav doesn't support the nested bundle `<details>` structure we need. A data file gives full control over grouping, ordering, and collapsible sections.

**Structure**:
```yaml
- section: Getting Started
  items:
    - title: Installation
      url: /getting-started/installation/
- section: Bundles
  bundles:
    - name: Backlog
      items:
        - title: Overview
          url: /bundles/backlog/overview/
```

### D2: Theme toggle via `[data-theme]` attribute on `<html>`

**Choice**: Use `data-theme="light"` / `data-theme="dark"` attribute on the `<html>` element, with a `theme.js` script loaded in `<head>` (before body renders) to prevent flash of wrong theme (FOUC).

**Why over CSS `prefers-color-scheme` only**: Users want explicit control. `skin: auto` in minima config provides system-preference fallback, but a toggle button gives direct control. `localStorage` persists the choice.

**Why over class-based toggling**: `[data-theme]` works natively with CSS `color-scheme` property and is the modern standard pattern.

**Color palette**:
- Dark mode: Current colors with slightly subdued cyan (`#57e6c4` instead of `#64ffda`) for reduced eye strain
- Light mode: `#ffffff` background, `#1a1a2e` text, `#0d9488` (teal-600) as accent — retains SpecFact brand identity in a readable light context

### D3: Lunr.js for client-side search

**Choice**: Lunr.js loaded from CDN (~8 KB gzipped), with a Jekyll Liquid-generated `search-index.json` that includes `url`, `title`, `keywords`, `audience`, `expertise_level`, and a content snippet per page.

**Why Lunr.js over alternatives**:
- No server required (pure client-side, works offline)
- Standard for Jekyll sites (well-documented integration)
- Small footprint, lazy-loaded on first search focus
- Supports field boosting (title: 10x, keywords: 5x, content: 1x)

**Why not Algolia/Pagefind**: Algolia requires external service account and API keys. Pagefind requires a build step binary. Both are overkill for ~100 pages.

**Search index**: Generated at build time as `docs/assets/js/search-index.json` using Liquid template with Jekyll frontmatter.

### D4: Expertise filter as single dropdown, not dual filters

**Choice**: Single expertise-level dropdown (All / Beginner / Intermediate / Advanced) in the sidebar, above the navigation sections. No separate audience filter in the sidebar.

**Why single filter**: Two dropdowns (expertise + audience) make the sidebar cluttered. The audience dimension (solo/team/enterprise) is better served by the homepage "Find Your Path" cards which link to curated page sets. The expertise filter directly controls sidebar visibility using `data-expertise` attributes on nav items.

**Implementation**: Each nav item in `nav.yml` carries an `expertise` field. The filter JS adds/removes a CSS class on the sidebar that hides non-matching items. Stored in `localStorage`.

### D5: Front matter enrichment strategy

**Choice**: Add three new optional fields to all doc page front matter:
```yaml
keywords: [search, terms, here]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate, advanced]
```

**Assignment logic**:
- Getting Started pages: `expertise_level: [beginner]`, `audience: [solo, team, enterprise]`
- Bundle overviews: `expertise_level: [beginner, intermediate]`, `audience: [solo, team, enterprise]`
- Command deep dives: `expertise_level: [intermediate, advanced]`, `audience: [solo, team, enterprise]`
- Workflows: `expertise_level: [intermediate]`, `audience: [solo, team]`
- Team & Enterprise: `expertise_level: [intermediate]`, `audience: [team, enterprise]`
- Authoring: `expertise_level: [advanced]`, `audience: [solo, team, enterprise]`
- Reference: `expertise_level: [advanced]`, `audience: [solo, team, enterprise]`

### D6: Mermaid theme-awareness

**Choice**: Refactor the inline `mermaid.initialize()` call into a `initMermaid(theme)` function. On theme toggle, re-initialize mermaid with appropriate `themeVariables` for light or dark mode. Light mode uses mermaid's `default` theme with SpecFact teal accents.

### D7: File organization

**New directories and files**:
```
docs/
├── _data/nav.yml                       # navigation data
├── _includes/
│   ├── sidebar-nav.html                # nav renderer
│   ├── search.html                     # search UI
│   ├── theme-toggle.html               # toggle button
│   ├── expertise-filter.html           # filter dropdown
│   └── breadcrumbs.html                # page breadcrumbs
└── assets/js/
    ├── theme.js                        # theme toggle + persistence
    ├── search.js                       # Lunr.js integration
    ├── search-index.json               # Liquid-generated index
    └── filters.js                      # expertise filter logic
```

## Risks / Trade-offs

- **[Mermaid re-rendering on theme toggle]** → Mermaid.js re-init can cause a brief flash. Mitigation: wrap diagrams in a container that fades out/in during re-render.
- **[Search index size]** → With ~100 pages and content snippets, index could be 50-100 KB. Mitigation: truncate content to first 200 words per page; lazy-load on first search focus.
- **[Front matter bulk update risk]** → Touching ~50 files increases merge conflict surface. Mitigation: front matter additions are purely additive (new keys only); no existing keys changed.
- **[Light mode readability of existing content]** → Some pages may have inline color references or assumptions about dark backgrounds. Mitigation: audit all pages with embedded HTML/style tags during implementation.
- **[Expertise filter hiding content]** → Users might not realize content is filtered. Mitigation: show count of visible/total items and a "showing filtered results" indicator.
