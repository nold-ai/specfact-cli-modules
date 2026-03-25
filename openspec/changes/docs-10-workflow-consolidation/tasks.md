## 1. Change Setup

- [ ] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-10-workflow-consolidation` entry
- [ ] 1.2 Add `cross-module-workflow-docs` and `daily-devops-routine-docs` capability specs

## 2. Brownfield Consolidation

- [ ] 2.1 Merge brownfield-engineer + brownfield-journey into `workflows/brownfield-modernization.md`
- [ ] 2.2 Merge brownfield-faq + brownfield-roi into `workflows/brownfield-faq-and-roi.md`
- [ ] 2.3 Merge 3 brownfield example files into `workflows/brownfield-examples.md`

## 3. New Workflow Docs

- [ ] 3.1 Write `workflows/cross-module-chains.md`: backlog -> code -> spec -> govern end-to-end flow
- [ ] 3.2 Write `workflows/daily-devops-routine.md`: morning standup -> refine -> commit -> review cycle
- [ ] 3.3 Write `workflows/ci-cd-pipeline.md`: CI integration with pre-commit hooks, GitHub Actions
- [ ] 3.4 Add bundle-owned prompt/template bootstrap steps where workflows depend on migrated resources

## 4. Update Existing

- [ ] 4.1 Validate and update `workflows/command-chains.md` against current command surface
- [ ] 4.2 Add redirects from old brownfield file paths to new merged locations

## 5. Verification

- [ ] 5.1 Verify all command examples in workflow docs match actual `--help` output
- [ ] 5.2 Verify workflow docs do not reference legacy core-owned prompt/template paths
- [ ] 5.3 Verify all internal links resolve
- [ ] 5.4 Run `bundle exec jekyll build` with zero warnings
