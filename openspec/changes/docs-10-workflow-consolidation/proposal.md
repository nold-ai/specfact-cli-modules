# Change: Consolidate Overlapping Workflow Docs And Write Cross-Module Workflows

## Why

Multiple brownfield guides overlap (brownfield-engineer, brownfield-journey, brownfield-faq, brownfield-roi, plus 3 example files). The command-chains guide is marked legacy. There are no docs showing how to chain commands across modules (backlog -> code -> spec -> govern) or how to set up a daily DevOps routine with SpecFact.

## What Changes

- Merge brownfield-engineer + brownfield-journey into a single `workflows/brownfield-modernization.md`
- Merge brownfield-faq + brownfield-roi into `workflows/brownfield-faq-and-roi.md`
- Merge 3 brownfield example files into `workflows/brownfield-examples.md`
- Write new `workflows/cross-module-chains.md`: end-to-end flow from backlog -> code -> spec -> govern
- Write new `workflows/daily-devops-routine.md`: morning standup -> refine -> commit -> review cycle
- Write new `workflows/ci-cd-pipeline.md`: CI integration patterns with SpecFact commands
- Validate and update existing `command-chains.md` against current command surface
- Fold bundle-owned prompt/template setup into the workflow docs where IDE export or workspace-template bootstrap is a prerequisite, so resource migration does not require a separate follow-up docs change

## Capabilities

### New Capabilities

- `cross-module-workflow-docs`: documented end-to-end flows showing how to chain commands across multiple bundles
- `daily-devops-routine-docs`: practical daily routine guide for DevOps teams

### Modified Capabilities

- `documentation-alignment`: brownfield docs consolidated from 7 overlapping files to 3 focused guides

## Impact

- New files: `workflows/cross-module-chains.md`, `workflows/daily-devops-routine.md`, `workflows/ci-cd-pipeline.md`
- Merged files: brownfield-engineer + brownfield-journey -> brownfield-modernization, brownfield-faq + brownfield-roi -> brownfield-faq-and-roi, 3 examples -> brownfield-examples
- Updated: `workflows/command-chains.md` (validated against current commands)
- Aligns with: `packaging-01-bundle-resource-payloads` for module-owned prompt/template setup steps
- Depends on: `docs-06-modules-site-ia-restructure`

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #98
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/98
- **Last Synced Status**: synced
- **Sanitized**: true
