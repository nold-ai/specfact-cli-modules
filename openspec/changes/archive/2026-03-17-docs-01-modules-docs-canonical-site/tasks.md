## 1. Change Setup And Discovery

- [x] 1.1 Create worktree `../specfact-cli-modules-worktrees/feature/docs-01-modules-docs-canonical-site` with branch `feature/docs-01-modules-docs-canonical-site` from `origin/dev`
- [x] 1.2 Inventory modules docs pages that are currently duplicated in `specfact-cli` and identify the pages that should become the canonical module-owned destinations
- [x] 1.3 Confirm the public-domain cutover assumptions so docs wording stays accurate before Cloudflare routing is live

## 2. Spec Deltas First

- [x] 2.1 Add the `modules-docs-publishing` spec delta for canonical publication, site identity, and cross-site navigation
- [x] 2.2 Map the required changes to docs configuration, landing copy, and top navigation before implementation begins

## 3. Validation First

- [x] 3.1 Add failing docs validation checks or assertions for canonical site identity, shared top-level navigation, and stable public-domain readiness
- [x] 3.2 Add failing docs validation checks or assertions proving module-specific deep guidance is presented as canonically owned by the modules site
- [x] 3.3 Record the failing validation evidence in `openspec/changes/docs-01-modules-docs-canonical-site/TDD_EVIDENCE.md`

## 4. Modules Site Realignment

- [x] 4.1 Update `docs/_config.yml` and `docs/index.md` so the site is ready for a first-class public docs domain and canonical modules-site positioning
- [x] 4.2 Update `docs/_layouts/default.html` and any related navigation content to expose `Docs Home`, `Core CLI`, and `Modules`
- [x] 4.3 Update bundle-focused landing and navigation copy so the site clearly serves as the canonical destination for official bundle/module deep docs

## 5. Validation And Delivery

- [x] 5.1 Re-run the targeted docs validation checks and record passing evidence in `openspec/changes/docs-01-modules-docs-canonical-site/TDD_EVIDENCE.md`
- [x] 5.2 Run `openspec validate docs-01-modules-docs-canonical-site --strict`
- [x] 5.3 Run the relevant repo quality gates for touched docs/test files
- [x] 5.4 Open PR to `dev` from `feature/docs-01-modules-docs-canonical-site`
