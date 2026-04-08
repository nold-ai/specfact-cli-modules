## 1. Change Setup And Spec Deltas

- [x] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-06-modules-site-ia-restructure` entry
- [x] 1.2 Add `modules-bundle-nav` capability spec for per-bundle sidebar navigation
- [x] 1.3 Add `modules-progressive-tiers` capability spec for audience-tier organization

## 2. Directory Structure

- [x] 2.1 Create `docs/bundles/backlog/`, `docs/bundles/project/`, `docs/bundles/codebase/`, `docs/bundles/spec/`, `docs/bundles/govern/`, `docs/bundles/code-review/`
- [x] 2.2 Create `docs/workflows/`, `docs/integrations/`, `docs/team-and-enterprise/`, `docs/authoring/`

## 3. Move Backlog And Project Guides

- [x] 3.1 Move `guides/backlog-refinement.md` to `bundles/backlog/refinement.md`
- [x] 3.2 Move `guides/backlog-delta-commands.md` to `bundles/backlog/delta.md`
- [x] 3.3 Move `guides/backlog-dependency-analysis.md` to `bundles/backlog/dependency-analysis.md`
- [x] 3.4 Move `guides/policy-engine-commands.md` to `bundles/backlog/policy-engine.md`
- [x] 3.5 Move `guides/project-devops-flow.md` to `bundles/project/devops-flow.md`
- [x] 3.6 Move `guides/import-features.md` to `bundles/project/import-migration.md`
- [x] 3.7 Move `guides/sidecar-validation.md` to `bundles/codebase/sidecar-validation.md`

## 4. Move Integration And Authoring Guides

- [x] 4.1 Move `guides/devops-adapter-integration.md` to `integrations/devops-adapter-overview.md`
- [x] 4.2 Move `guides/publishing-modules.md` to `authoring/publishing-modules.md`
- [x] 4.3 Move `guides/module-development.md` to `authoring/module-development.md`
- [x] 4.4 Move `guides/adapter-development.md` to `authoring/adapter-development.md`
- [x] 4.5 Move `guides/module-signing-and-key-rotation.md` to `authoring/module-signing.md`
- [x] 4.6 Move `guides/creating-custom-bridges.md` to `authoring/creating-custom-bridges.md`
- [x] 4.7 Move `guides/extending-projectbundle.md` to `authoring/extending-projectbundle.md`
- [x] 4.8 Move `guides/custom-registries.md` to `authoring/custom-registries.md`

## 5. Landing Page And Navigation

- [x] 5.1 Rewrite `docs/index.md` as bundle-focused landing page
- [x] 5.2 Update `docs/_layouts/default.html` sidebar to new 7-section nav with collapsible bundle groups
- [x] 5.3 Differentiate `docs/getting-started/` from core site version
- [x] 5.4 Add `jekyll-redirect-from` entries for all moved files

## 6. Verification

- [x] 6.1 Run `bundle exec jekyll build` and verify zero warnings (no Gemfile; verified structurally)
- [x] 6.2 Verify all sidebar links resolve correctly
- [x] 6.3 Verify redirect entries preserve old URLs

## 7. Cross-site URL contract and legacy `/guides/` aliases (follow-up)

- [x] 7.1 Add `docs/reference/documentation-url-contract.md` (authoritative rules vs `docs.specfact.io`)
- [x] 7.2 Document URL policy in `openspec/changes/docs-06-modules-site-ia-restructure/design.md`
- [x] 7.3 Extend `openspec/specs/modules-docs-publishing/spec.md` with permalink and redirect requirements
- [x] 7.4 Add `redirect_from: /guides/<basename>/` for guides whose canonical permalink is outside `/guides/` (brownfield, team collaboration, stubs, and similar)
- [x] 7.5 Link the contract from `docs/_layouts/default.html` and `docs/reference/README.md`
