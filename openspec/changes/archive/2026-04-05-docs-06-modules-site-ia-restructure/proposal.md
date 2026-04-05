# Change: Restructure Modules Docs Site Information Architecture

## Why

The modules docs site at modules.specfact.io has a flat structure with 6 sidebar sections (Getting Started, Official Modules, Bundle Workflows, Publishing & Signing, Reference) where 50+ guide files sit in a single guides/ folder. Bundle-specific docs are mixed with authoring guides, workflow patterns, and integration docs. There is no per-bundle organization, no progressive learning path, and no team/enterprise tier. Users of specific bundles (e.g., backlog or govern) cannot quickly find all relevant docs for their bundle.

## What Changes

- Restructure the modules docs sidebar from 6 flat sections to 7 focused sections: Getting Started, Bundles, Workflows, Integrations, Team & Enterprise, Authoring, Reference
- Create a new `bundles/` directory with per-bundle subdirectories: backlog/, project/, codebase/, spec/, govern/, code-review/
- Create new directories: `workflows/`, `integrations/`, `team-and-enterprise/`, `authoring/`
- Move existing guide files from flat `guides/` into their correct bundle, workflow, integration, or authoring directory
- Update `docs/_layouts/default.html` sidebar to the new 7-section structure with collapsible bundle groups
- Rewrite `docs/index.md` as a bundle-focused landing page
- Differentiate getting-started from the core site version
- Add `jekyll-redirect-from` entries for all moved URLs

## Capabilities

### New Capabilities

- `modules-bundle-nav`: per-bundle collapsible sidebar navigation grouping all docs for each official bundle
- `modules-progressive-tiers`: docs organized by audience tier (beginner tutorials, bundle reference, workflows, team/enterprise, authoring)

### Modified Capabilities

- `documentation-alignment`: modules site becomes the canonical home for all bundle-specific deep guidance with clear ownership

## Impact

- New directories: `docs/bundles/{backlog,project,codebase,spec,govern,code-review}/`, `docs/workflows/`, `docs/integrations/`, `docs/team-and-enterprise/`, `docs/authoring/`
- Moved files: 15+ guide files from `guides/` to their correct new locations (see migration map in plan)
- Modified: `docs/_layouts/default.html` (sidebar), `docs/index.md` (landing), `docs/_config.yml` (if needed for redirect plugin)
- User-facing: modules.specfact.io navigation is organized by bundle with clear paths from beginner to advanced

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #95
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/95
- **Last Synced Status**: synced
- **Sanitized**: true
