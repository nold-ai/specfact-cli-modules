## 1. Change Setup And Spec Deltas

- [ ] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-06-modules-site-ia-restructure` entry
- [ ] 1.2 Add `modules-bundle-nav` capability spec for per-bundle sidebar navigation
- [ ] 1.3 Add `modules-progressive-tiers` capability spec for audience-tier organization

## 2. Directory Structure

- [ ] 2.1 Create `docs/bundles/backlog/`, `docs/bundles/project/`, `docs/bundles/codebase/`, `docs/bundles/spec/`, `docs/bundles/govern/`, `docs/bundles/code-review/`
- [ ] 2.2 Create `docs/workflows/`, `docs/integrations/`, `docs/team-and-enterprise/`, `docs/authoring/`

## 3. Move Backlog And Project Guides

- [ ] 3.1 Move `guides/backlog-refinement.md` to `bundles/backlog/refinement.md`
- [ ] 3.2 Move `guides/backlog-delta-commands.md` to `bundles/backlog/delta.md`
- [ ] 3.3 Move `guides/backlog-dependency-analysis.md` to `bundles/backlog/dependency-analysis.md`
- [ ] 3.4 Move `guides/policy-engine-commands.md` to `bundles/backlog/policy-engine.md`
- [ ] 3.5 Move `guides/project-devops-flow.md` to `bundles/project/devops-flow.md`
- [ ] 3.6 Move `guides/import-features.md` to `bundles/project/import-migration.md`
- [ ] 3.7 Move `guides/sidecar-validation.md` to `bundles/codebase/sidecar-validation.md`

## 4. Move Integration And Authoring Guides

- [ ] 4.1 Move `guides/devops-adapter-integration.md` to `integrations/devops-adapter-overview.md`
- [ ] 4.2 Move `guides/publishing-modules.md` to `authoring/publishing-modules.md`
- [ ] 4.3 Move `guides/module-development.md` to `authoring/module-development.md`
- [ ] 4.4 Move `guides/adapter-development.md` to `authoring/adapter-development.md`
- [ ] 4.5 Move `guides/module-signing-and-key-rotation.md` to `authoring/module-signing.md`
- [ ] 4.6 Move `guides/creating-custom-bridges.md` to `authoring/creating-custom-bridges.md`
- [ ] 4.7 Move `guides/extending-projectbundle.md` to `authoring/extending-projectbundle.md`
- [ ] 4.8 Move `guides/custom-registries.md` to `authoring/custom-registries.md`

## 5. Landing Page And Navigation

- [ ] 5.1 Rewrite `docs/index.md` as bundle-focused landing page
- [ ] 5.2 Update `docs/_layouts/default.html` sidebar to new 7-section nav with collapsible bundle groups
- [ ] 5.3 Differentiate `docs/getting-started/` from core site version
- [ ] 5.4 Add `jekyll-redirect-from` entries for all moved files

## 6. Verification

- [ ] 6.1 Run `bundle exec jekyll build` and verify zero warnings
- [ ] 6.2 Verify all sidebar links resolve correctly
- [ ] 6.3 Verify redirect entries preserve old URLs
