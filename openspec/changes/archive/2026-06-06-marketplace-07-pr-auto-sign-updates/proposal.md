# Change: Auto-Sign Module Manifest Updates On Every PR Sync

## Why

`specfact-cli-modules` currently remediates manifest checksum and signature drift on pull requests
only after trusted approval via `sign-modules-on-approval.yml`. That leaves same-repo PRs exposed
to checksum mismatch failures on every earlier review-fix push, because `sign-modules.yml` verifies
PRs on `pull_request` events but does not repair them.

This is a poor fit for iterative code review where a PR can receive many `synchronize` pushes
before the final approval. Review agents and humans should not need a local signing key or a fresh
approval just to repair manifest integrity after each update.

## What Changes

- **MODIFY**: `.github/workflows/sign-modules.yml` to auto-sign changed same-repo PR heads for
  every `pull_request` event targeting `dev` or `main`, then verify the updated manifests in the
  same run.
- **MODIFY**: `.github/workflows/sign-modules-on-approval.yml` to remain approval-only so PR-update
  remediation lives in one workflow and does not overlap.
- **MODIFY**: Workflow tests under `tests/unit/workflows/` to cover same-repo PR remediation,
  bot-loop avoidance, and approval-only triggering.
- **MODIFY**: OpenSpec CI signing specs so the new PR-update remediation behavior is explicit.

## Capabilities

### Modified Capabilities

- `ci-integration`: same-repo PRs targeting `dev` or `main` auto-repair changed
  `packages/*/module-package.yaml` manifests on every update before verification completes.
- `ci-module-signing-on-approval`: approval-triggered signing remains available as an approval
  workflow, but PR-update remediation no longer depends on approval state.

## Impact

- **Affected workflows**: `.github/workflows/sign-modules.yml`,
  `.github/workflows/sign-modules-on-approval.yml`
- **Affected tests**: `tests/unit/workflows/test_sign_modules_hardening.py`,
  `tests/unit/workflows/test_sign_modules_on_approval.py`
- **Affected specs**: `openspec/specs/ci-integration/spec.md`,
  `openspec/specs/ci-module-signing-on-approval/spec.md`
- **GitHub secrets used**: `SPECFACT_MODULE_PRIVATE_SIGN_KEY`,
  `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
- **Repository scope**: same-repo PR branches only; fork PRs remain out of scope because the
  default `GITHUB_TOKEN` cannot push to contributor forks
