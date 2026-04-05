# Design: Modules docs IA restructure — URL policy

## Context

Jekyll defaults in `docs/_config.yml` set `permalink: /:basename/` for pages unless front matter overrides. Guides may therefore publish at `/guides/<name>/` **or** at root `/<basename>/` depending on explicit `permalink`. After moving bundle content to `bundles/` and `integrations/`, **canonical** URLs changed; `redirect_from` preserves old `/guides/...` modules URLs.

Core docs (`docs.specfact.io`) often use `/guides/<name>/` for handoff pages. **Modules paths are not guaranteed to mirror core**; authors must use each page’s real `permalink` on the modules site.

## Decisions

1. **Authoritative contract page**: `docs/reference/documentation-url-contract.md` on the modules site is the single source of truth for cross-site URL rules. Core docs link to it from a short summary page.
2. **Legacy `/guides/` on modules**: For any guide whose canonical URL is not under `/guides/`, add `redirect_from: /guides/<filename-without-md>/` so older links keep working.
3. **Status tracking**: `openspec/CHANGE_ORDER.md` reflects lifecycle; completed IA work is paired with redirect hygiene tasks in the same change folder until archive.

## Non-goals

- Unifying all modules URLs under `/guides/` (would break bundle-first IA).
- Building combined Jekyll sites in CI for every PR (see docs-12 on core for cross-site HTTP checks).
