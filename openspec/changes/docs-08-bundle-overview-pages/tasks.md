## 1. Change Setup

- [ ] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-08-bundle-overview-pages` entry
- [ ] 1.2 Add `bundle-overview-pages` capability spec

## 2. Write Overview Pages

- [ ] 2.1 Write `bundles/backlog/overview.md`: ceremony, daily, refine, add, analyze-deps, sync, diff, promote, verify-readiness, delta, policy, init-config, map-fields, plus bundled template/bootstrap notes
- [ ] 2.2 Write `bundles/project/overview.md`: link-backlog, health-check, snapshot, regenerate, export-roadmap, version, sync bridge, devops-flow, plan init, import, migrate, add-feature, add-story, plan review, plan harden, plan compare, plus bundled prompt notes
- [ ] 2.3 Write `bundles/codebase/overview.md`: import, analyze contracts, drift detect, validate sidecar, repro, plus bundled prompt notes
- [ ] 2.4 Write `bundles/spec/overview.md`: contract (init/validate/coverage/serve/verify/test), generate, sdd, plus bundled prompt notes where relevant
- [ ] 2.5 Write `bundles/govern/overview.md`: enforce (stage/sdd), patch, plus bundled prompt notes
- [ ] 2.6 Write `bundles/code-review/overview.md`: run, ledger, rules

## 3. Verification

- [ ] 3.1 Validate every command example against `--help` output
- [ ] 3.2 Verify bundle overview pages do not describe migrated prompts/templates as core-owned assets
- [ ] 3.3 Verify all internal links resolve
- [ ] 3.4 Run `bundle exec jekyll build` with zero warnings
