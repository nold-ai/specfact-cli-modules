---
layout: default
title: Core and modules docs URL contract
permalink: /reference/documentation-url-contract/
description: Ownership boundaries and published URL rules between docs.specfact.io and modules.specfact.io.
---

# Core and modules documentation URL contract

This page is the **authoritative** reference for how published URLs work across the two public documentation sites. **Contributors must read this before adding cross-site links or changing `permalink` / `redirect_from` metadata.**

## Sites and repositories

| Site | Repository | Published URL |
| --- | --- | --- |
| Core CLI docs | `nold-ai/specfact-cli` (`docs/`) | `https://docs.specfact.io/` |
| Modules docs | `nold-ai/specfact-cli-modules` (`docs/`) | `https://modules.specfact.io/` |

## Ownership (what lives where)

- **Core (`specfact-cli`)** owns: lean-core CLI topology, installation/upgrade, registry and marketplace *as a platform*, architecture of the runtime, debug/modes, authentication *as used by core*, migration topics that are release-line wide, and **handoff pages** that summarize bundle workflows while pointing to modules for depth.
- **Modules (`specfact-cli-modules`)** owns: official bundle deep guides, adapter runbooks, module authoring, bundle-specific command examples, and the **canonical** URL for any migrated guide that previously lived only under core `docs/guides/`.

Do not assume the **same path** on both sites points to the same page. Path shape differs after IA restructures (for example bundle paths under `/bundles/.../` on modules).

## Modules permalink rules (this site)

1. **Default** (`docs/_config.yml`): pages default to `permalink: /:basename/` (filename stem at site root), unless overridden.
2. **Explicit `permalink`** in front matter always wins. Many guides use `permalink: /guides/<name>/` so the published URL stays under `/guides/`.
3. **Bundle and integration moves** (OpenSpec change `docs-06-modules-site-ia-restructure`): canonical URLs live under `/bundles/.../`, `/integrations/.../`, `/authoring/.../`, etc. Each moved page **must** include `redirect_from` for the **previous** modules URL (typically `/guides/<old-filename>/`).
4. **Legacy `/guides/<slug>/` aliases**: If a page’s canonical URL is **not** under `/guides/` (for example `/brownfield-engineer/` or `/contract-testing-workflow/`), the page **must** include:

   ```yaml
   redirect_from:
     - /guides/<same-basename-as-filename-without-md>/
   ```

   so bookmarks and older links keep working.

5. **Core handoff links**: When `specfact-cli` links to this site, authors **must** use the **actual** `permalink` (or the default-derived path) for the target page—**not** mirror core’s `/guides/...` path unless this site’s target also uses `/guides/...`.

## Core site obligations (`specfact-cli`)

- Internal links on `docs.specfact.io` must match **core** published routes (see `tests/unit/docs/test_release_docs_parity.py` and docs review gate).
- Any `https://modules.specfact.io/...` link in core docs must target a **real** modules path. When in doubt, open the target file in `specfact-cli-modules` and copy its `permalink` (or infer `/<basename>/` from defaults).
- Prefer linking to **`/reference/documentation-url-contract/`** on this site from core’s [Documentation URL contract](https://docs.specfact.io/reference/documentation-url-contract/) page for the full table mindset; keep core’s page as a short summary so the contract does not drift.

## Related OpenSpec changes

- **Modules**: `docs-06-modules-site-ia-restructure` — IA, moves, redirects for moved pages.
- **Core**: `docs-07-core-handoff-conversion` — thin handoff pages on core with canonical links to modules.

## Change process

- **URL or redirect changes** on this site: update front matter, run `bundle exec jekyll build` locally, and ensure `redirect_from` covers prior public URLs.
- **Cross-repo**: if a canonical target moves again, update both repos in the same release window when possible, and extend `redirect_from` on modules before updating core links.
