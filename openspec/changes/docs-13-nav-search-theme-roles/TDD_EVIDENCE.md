# docs-13 Validation Evidence

Date: 2026-03-28T21:57:34+01:00

## Implementation state recovered from Claude session

- Claude session `fff31fcf-cd55-4952-896b-638cb0e8958f` worked in git worktree `<repo-root>/../specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles`
- Session artifacts showed completed implementation across `docs/_layouts/default.html`, `docs/assets/main.scss`, new `_data`, `_includes`, `assets/js`, and bulk front matter enrichment
- Remaining incomplete scope at handoff was validation task group `7`

## Red phase

### 1. Failing markdown lint review on OpenSpec docs artifacts

Command:

```bash
markdownlint openspec/changes/docs-13-nav-search-theme-roles/**/*.md
```

Result:

```text
openspec/changes/docs-13-nav-search-theme-roles/tasks.md:1 MD041/first-line-heading/first-line-h1 First line in a file should be a top-level heading
openspec/changes/docs-13-nav-search-theme-roles/specs/docs-client-search/spec.md:1 MD041/first-line-heading/first-line-h1 First line in a file should be a top-level heading
openspec/changes/docs-13-nav-search-theme-roles/specs/docs-client-search/spec.md:3 MD022/blanks-around-headings Headings should be surrounded by blank lines
openspec/changes/docs-13-nav-search-theme-roles/specs/docs-nav-data-driven/spec.md:1 MD041/first-line-heading/first-line-h1 First line in a file should be a top-level heading
openspec/changes/docs-13-nav-search-theme-roles/specs/modules-docs-command-validation/spec.md:1 MD041/first-line-heading/first-line-h1 First line in a file should be a top-level heading
```

### 2. Failing docs robustness review before hardening fixes

Command:

```bash
review-check docs/_includes/breadcrumbs.html docs/_layouts/default.html docs/assets/js/search.js docs/assets/js/filters.js scripts/check-docs-commands.py
```

Result:

```text
- breadcrumbs current-page detection depends on forloop.last and breaks for trailing-slash URLs
- mermaid rerender targets nested svg elements instead of only .mermaid containers
- search rendering injects unescaped doc data via innerHTML and assumes fetch/lunr always succeed
- expertise persistence uses unguarded localStorage.getItem/setItem
- _validate_nav_data_links can raise yaml.YAMLError instead of emitting a validation finding
```

## Validation commands

### 1. Docs command + nav validation

Command:

```bash
python3 scripts/check-docs-commands.py
```

Result:

```text
Docs command validation passed with no findings.
```

Notes:

- Extended validator to check `_data/nav.yml` URLs against actual docs routes
- Excluded `docs/vendor/**` and `docs/_site/**` from markdown validation set

### 2. Jekyll build

Command:

```bash
cd docs && bundle exec jekyll build
```

Result:

```text
Configuration file: <repo-root>/../specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles/docs/_config.yml
            Source: <repo-root>/../specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles/docs
       Destination: <repo-root>/../specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles/docs/_site
      Generating...
                    done in 0.924 seconds.
 Auto-regeneration: disabled. Use --watch to enable.
```

## Manual browser verification against built site

Served local build:

```bash
cd docs/_site && python3 -m http.server 4013
```

Verified in browser at `http://127.0.0.1:4013/`:

- Sidebar rendered all sections and bundle groups from `_data/nav.yml`
- Sidebar links resolved to generated local routes including:
  - `/bundles/govern/overview/`
  - `/bundles/code-review/overview/`
  - `/guides/cross-module-chains/`
  - `/team-and-enterprise/enterprise-config/`
  - `/reference/commands/`
- Search query `govern` returned 10 results including:
  - `Govern enforce`
  - `Govern bundle overview`
  - `Govern patch apply`
- Expertise filter `advanced` reduced visible nav items from `67` to `43` and persisted in `localStorage` as `specfact-expertise=advanced`
- Theme toggle switched to `light` and persisted across reload via `localStorage` as `specfact-theme=light`

## Additional notes

- Search widget was hardened to fetch the search index from a `relative_url`-aware attribute rather than a hard-coded absolute path
- Legitimate in-content references to `/reference/commands/` remain in docs body content; validation for task `7.3` refers to the sidebar navigation replacing stale placeholder bundle links, which is satisfied

## Final quality gates

Date: 2026-03-28T22:28:03+01:00

Commands:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run check-bundle-imports
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
hatch run contract-test
hatch run smart-test
hatch run test
openspec validate docs-13-nav-search-theme-roles --strict
```

Result summary:

- `format`: passed
- `type-check`: `0 errors, 0 warnings, 0 notes`
- `lint`: passed, `pylint` rated `10.00/10`
- `yaml-lint`: passed, validated `6` manifests plus `registry/index.json`
- `check-bundle-imports`: passed
- `verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`: passed for all `6` module manifests
- `contract-test`: `462 passed, 1 warning`
- `smart-test`: `462 passed, 1 warning`
- `test`: `462 passed, 1 warning`
- `openspec validate docs-13-nav-search-theme-roles --strict`: passed

Warnings:

- The docs review suite still reports `7` pre-existing authored-link warnings in non-restructured legacy pages under `docs/adapters/` and `docs/reference/`; these are warning-only and did not block any gate

Fixes completed during gate run:

- Restored `/guides/ide-integration/` as a redirect page to `/ai-ide-workflow/` so restructured bundle pages no longer point at a missing published route
- Updated the modules docs layout markup to keep the sidebar section scope explicit for the contract test while preserving the rendered data-driven navigation
