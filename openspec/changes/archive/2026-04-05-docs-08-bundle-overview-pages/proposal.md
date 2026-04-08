# Change: Write Bundle Overview Pages For All 6 Official Bundles

## Why

Users of specific bundles cannot quickly find all available commands, understand prerequisites, or see quick examples. Each bundle needs a single landing page that provides a complete at-a-glance view of everything the bundle offers.

## What Changes

- Write 6 new bundle overview pages, one per official bundle: backlog, project, codebase, spec, govern, code-review
- Each overview page contains: bundle purpose, prerequisites, bundle-owned resource/setup notes where relevant, full command listing with brief descriptions, quick example for each major command group, and links to deep-dive guides
- All command examples validated against actual `--help` output

## Capabilities

### New Capabilities

- `bundle-overview-pages`: each official bundle has a single overview page listing all commands, prerequisites, and quick examples

## Impact

- New files: `docs/bundles/backlog/overview.md`, `docs/bundles/project/overview.md`, `docs/bundles/codebase/overview.md`, `docs/bundles/spec/overview.md`, `docs/bundles/govern/overview.md`, `docs/bundles/code-review/overview.md`
- Depends on: `docs-06-modules-site-ia-restructure` (bundles/ directory structure must exist)
- Aligns with: `packaging-01-bundle-resource-payloads` for bundle-owned prompts/templates and `specfact init ide` resource ownership
- User-facing: each bundle has a clear entry point for discovering all available commands

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #96
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/96
- **Last Synced Status**: synced
- **Sanitized**: true
