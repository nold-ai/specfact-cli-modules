# Change: Requirements dogfooding evidence gate

## Why

The Requirements module can import native OpenSpec context, validate its
usefulness, and report coverage. This repository does not yet run those checks
as a single, auditable PR gate. Contributors therefore cannot distinguish a
green evidence result from a merely successful test suite, and a failed import
or incomplete requirement linkage has no durable red artifact.

## What Changes

- **NEW**: a deterministic Requirements evidence adapter that evaluates changed
  active OpenSpec changes in isolated temporary project bundles.
- **NEW**: a machine-readable `requirements-evidence.json` artifact with a
  per-source and aggregate `passed`, `failed`, or `skipped` verdict.
- **NEW**: a GitHub Actions `requirements-evidence` job that publishes the
  artifact and concise summary on every applicable pull request.
- Bootstrap the adapter from repository-local module source roots rather than
  treating an individual module bundle directory as a Python distribution.
- Retain deterministic failed JSON and Markdown evidence when setup fails
  before the adapter can run.
- **NEW**: an optional per-change `requirements-evidence.yaml` sidecar that
  maps imported stable requirement IDs to repository-relative test targets.
- **NEW**: explicit failure reasons for import diagnostics, validation failures,
  zero imported requirements, incomplete test-link coverage, and requirements
  gate findings.

## Non-Goals

- Do not claim that requirements are behaviorally met merely because their
  source, validation, and traceability evidence passes.
- Do not execute, parse, or infer test results in this phase. A future
  test-result adapter will require a stable mapping from requirement IDs to
  executed test evidence.
- Do not add a new requirements authoring workflow, dashboard, or change
  lifecycle orchestration.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #352
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/352>
- **Parent Feature**: #161
- **Follow-up To**: #346
- **Last Synced Status**: open
- **Sanitized**: false
