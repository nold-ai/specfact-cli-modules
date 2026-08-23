## Why

Three validation workflows can pair a modules branch with the same-named core
branch. That behavior is required for pull-request integration testing, but a
manual workflow run must not use a caller-selected core branch as executable
CI input.

## What Changes

- Preserve same-named paired-core branch resolution for pull-request and other
  non-manual validation runs.
- Restrict manual workflow runs to literal `main` or `dev` paired-core refs.
- Add focused workflow contract tests covering all three affected workflows.

## Capabilities

### New Capabilities

- `paired-core-workflow-ref-trust`: Event-specific trust boundaries for paired
  core source executed by modules validation workflows.

### Modified Capabilities

None.

## Impact

- Affects only `.github/workflows/docs-review.yml`,
  `.github/workflows/pr-orchestrator.yml`,
  `.github/workflows/requirements-evidence.yml`, one focused workflow contract
  test, and this OpenSpec change.
- Does not change module source, manifests, registry metadata, versions,
  signatures, C14 artifacts, dependency lockfiles, or marketplace contents.
- Does not alter the exact-core C14 compatibility job or its immutable core
  identity.
- A separate dependency-only change owns documentation dependency maintenance.

## Tracking

The authoritative findings remain in the repository's private GitHub Security
records. In accordance with `SECURITY.md`, no public vulnerability issue is
created and no alert-specific mechanics are reproduced here.
