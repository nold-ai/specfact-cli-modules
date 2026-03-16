# Change: Reapply code-review-08 review run integration in modules repo

## Why

The upstream `specfact-cli` change `code-review-08-review-run-integration`
defines the end-to-end `specfact code review run` workflow, but this modules
repository never received a matching active OpenSpec change. The bundle already
contains the internal runner orchestration and the ledger/rules command groups,
yet `specfact code review run` is still a stub and cannot be validated through
the dedicated modules worktree flow.

This change rehydrates the upstream scope locally so the modules repository can
implement the missing command integration, add contract fixtures and scenarios,
and verify runtime behavior under the same governed workflow used for earlier
code-review changes.

## What Changes

- Complete the `specfact code review run` command surface in the
  `specfact-code-review` bundle.
- Add clean/dirty review fixtures and end-to-end tests that exercise the
  governed `ReviewReport` output.
- Add cli-val scenario YAML files for the `run`, `ledger`, and `rules` command
  groups.
- Extend bundle documentation, changelog, and signed module metadata for the
  new command behavior.
- Record TDD and validation evidence for the modules-repo implementation.

## Impact

- Depends on bundle-side functionality from `code-review-02` through
  `code-review-07` already present in this repository.
- Produces the missing bundle-side command integration needed for actual
  runtime validation of `specfact code review run`.
- Aligns bundle docs and CLI contract coverage with the upstream change intent.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli -->
- **Source Change**: `code-review-08-review-run-integration`
- **Repository**: nold-ai/specfact-cli
- **Last Synced Status**: re-applied in modules repo
