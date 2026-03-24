# Change: Write Missing Command Reference Docs For Spec, Govern, Code-Review, And Codebase

## Why

The spec, govern, code-review, and codebase bundles have minimal or no documentation for their individual commands. Users cannot find guidance on how to use `specfact spec validate`, `specfact govern enforce`, `specfact code review run`, or `specfact code drift detect` beyond the basic `--help` output.

## What Changes

- Write 11 new command reference pages covering all undocumented commands across 4 bundles
- Each page contains: command purpose, prerequisites, full option reference, practical examples, common patterns, and links to related commands
- All examples validated against actual implementations

## Capabilities

### New Capabilities

- `spec-command-docs`: reference docs for spec validate, generate-tests, and mock commands
- `govern-command-docs`: reference docs for govern enforce and patch commands
- `code-review-command-docs`: reference docs for code review run, ledger, and rules commands
- `codebase-command-docs`: reference docs for code analyze, drift, and repro commands

## Impact

- New files (11): `bundles/spec/validate.md`, `bundles/spec/generate-tests.md`, `bundles/spec/mock.md`, `bundles/govern/enforce.md`, `bundles/govern/patch.md`, `bundles/code-review/run.md`, `bundles/code-review/ledger.md`, `bundles/code-review/rules.md`, `bundles/codebase/analyze.md`, `bundles/codebase/drift.md`, `bundles/codebase/repro.md`
- Depends on: `docs-06-modules-site-ia-restructure` (bundles/ directory structure must exist)

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #97
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/97
- **Last Synced Status**: synced
- **Sanitized**: true
