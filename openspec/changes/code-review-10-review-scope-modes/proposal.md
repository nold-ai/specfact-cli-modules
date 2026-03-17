# Change: Reapply code-review-10 review scope modes in modules repo

## Why

The upstream `specfact-cli` change `code-review-10-review-scope-modes` defines
the governed contract for explicit changed-only vs. full review modes plus
repo-relative path filtering. The modules repository needs a matching active
change because the bundle-owned `specfact code review run` implementation,
runtime fixtures, and cli-val scenarios live here.

Without this derived change, the upstream contract would exist only on paper:
the installed `specfact-code-review` bundle would still lack the runtime
behavior needed to review a full repo or a limited subtree in a controlled way.

## What Changes

- Extend the `specfact-code-review` bundle command to support `--scope changed`
  and `--scope full`.
- Add repeatable `--path` filtering for repo-relative files and subfolders in
  auto-discovery mode.
- Keep changed-only auto-discovery as the default behavior when users do not
  pass positional files or an explicit scope.
- Treat explicit `--path tests/...` filters as an intentional opt-in for those
  matched test files without changing the default auto-scope exclusion of tests.
- Add targeted tests, fixtures, and cli-val scenarios for changed-only reviews,
  full reviews, filtered subtree reviews, and invalid scope combinations.
- Update bundle docs, changelog, and signed package metadata to describe the
  new review-scope controls.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review-run-command`: add explicit review-scope selection and repo-relative
  path filtering to the bundle command
- `review-cli-contracts`: extend review-run scenario coverage for changed-only,
  full-review, and subtree-limited invocations

## Impact

- Affects `packages/specfact-code-review/src/specfact_code_review/run/` command
  parsing and target-file resolution
- Expands runtime validation in `tests/unit/`, `tests/e2e/`, and
  `tests/cli-contracts/`
- Requires documentation, changelog, and module metadata updates for the
  `specfact-code-review` bundle

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli -->
- **Source Change**: `code-review-10-review-scope-modes`
- **Repository**: nold-ai/specfact-cli
- **Last Synced Status**: re-applied in modules repo
