# docs-13 Validation Evidence

Date: 2026-03-28T21:57:34+01:00

## Implementation state recovered from Claude session

- Claude session `fff31fcf-cd55-4952-896b-638cb0e8958f` worked in git worktree `/home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles`
- Session artifacts showed completed implementation across `docs/_layouts/default.html`, `docs/assets/main.scss`, new `_data`, `_includes`, `assets/js`, and bulk front matter enrichment
- Remaining incomplete scope at handoff was validation task group `7`

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
Configuration file: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles/docs/_config.yml
            Source: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles/docs
       Destination: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-13-nav-search-theme-roles/docs/_site
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
