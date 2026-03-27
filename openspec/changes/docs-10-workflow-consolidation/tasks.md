## 1. Change Setup

- [x] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-10-workflow-consolidation` entry
- [x] 1.2 Add `cross-module-workflow-docs` and `daily-devops-routine-docs` capability specs

## 2. Brownfield Consolidation

- [x] 2.1 Merge brownfield-engineer + brownfield-journey into `docs/guides/brownfield-modernization.md`
- [x] 2.2 Merge brownfield-faq + brownfield-roi into `docs/guides/brownfield-faq-and-roi.md`
- [x] 2.3 Consolidate brownfield example flows into `docs/guides/brownfield-examples.md`

## 3. New Workflow Docs

- [x] 3.1 Write `docs/guides/cross-module-chains.md`: backlog -> code -> spec -> govern end-to-end flow
- [x] 3.2 Write `docs/guides/daily-devops-routine.md`: morning standup -> refine -> commit -> review cycle
- [x] 3.3 Write `docs/guides/ci-cd-pipeline.md`: CI integration with pre-commit hooks, GitHub Actions
- [x] 3.4 Add bundle-owned prompt/template bootstrap steps where workflows depend on migrated resources

## 4. Update Existing

- [x] 4.1 Validate and update `docs/guides/command-chains.md` against current command surface
- [x] 4.2 Add redirects from old brownfield file paths to new merged locations

## 5. Verification

- [x] 5.1 Verify all command examples in workflow docs match actual `--help` output
- [x] 5.2 Verify workflow docs do not reference legacy core-owned prompt/template paths
- [x] 5.3 Verify all internal links resolve
- [x] 5.4 Run `bundle exec jekyll build` with zero warnings
