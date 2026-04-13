# Change: CI-Driven Module Signing On PR Approval (specfact-cli-modules)

## Why

`specfact-cli-modules` currently verifies module signatures on every PR (including feature→dev
branches) but has no automated signing step in CI at all. The only path to a signed manifest is
local signing with the private key — which blocks non-interactive development (AI agents, Cursor,
headless CI). This is the modules-repo half of the paired change: it adds the missing CI signing
job (triggered by PR approval) and relaxes the verify gate on dev-targeting PRs, matching the
policy set by `specfact-cli/marketplace-06-ci-module-signing`.

## What Changes

- **NEW**: `sign-modules-on-approval.yml` GitHub Actions workflow — triggers on
  `pull_request_review` (state: `approved`), signs changed module manifests under `packages/`
  via CI secrets, and commits signed manifests back to the PR branch.
- **MODIFY**: `.github/workflows/pr-orchestrator.yml` `verify-module-signatures` job — drop
  `--require-signature` for PRs and pushes targeting `dev`; keep it for `main`-targeting events.
- **NO CHANGE**: `scripts/pre-commit-quality-checks.sh` — the modules pre-commit does not include
  a module-signature verification step; no pre-commit changes are needed.
- **NO CHANGE**: `publish-modules.yml` — handles signing at publish/registry-update time;
  unchanged.
- **NO CHANGE**: Module install-time verification (end users always install from the main registry;
  install-time verification always requires signatures).

## Capabilities

### New Capabilities

- `ci-module-signing-on-approval`: Automated CI workflow that signs changed `packages/*/
  module-package.yaml` manifests using repository secrets when a PR targeting `dev` or `main`
  is approved, and commits the signed manifests back to the PR branch.

### Modified Capabilities

- `ci-integration`: The `verify-module-signatures` job in `pr-orchestrator.yml` applies a
  branch-aware policy — checksum-only for dev-targeting events, full `--require-signature` for
  main-targeting events.

## Impact

- **Affected workflows**: `.github/workflows/pr-orchestrator.yml`
- **New workflow**: `.github/workflows/sign-modules-on-approval.yml`
- **GitHub secrets used** (already configured via publish-modules.yml):
  `SPECFACT_MODULE_PRIVATE_SIGN_KEY`, `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
- **Permissions added**: `contents: write` on the new signing workflow
- **Module manifest paths**: `packages/*/module-package.yaml` (found under `packages/` in this
  repo, not `src/` or `modules/` as in specfact-cli)
- **No Python source changes**: all modifications are to YAML workflows only
- **Paired change**: `specfact-cli/marketplace-06-ci-module-signing` — covers the pre-commit hook,
  `sign-modules.yml`, and pr-orchestrator changes in the core CLI repo
- **Source Tracking**:
  - GitHub Issue: [specfact-cli-modules#185](https://github.com/nold-ai/specfact-cli-modules/issues/185)
  - Paired Core Change: [specfact-cli#500](https://github.com/nold-ai/specfact-cli/issues/500)
  - Parent Feature (core side): [#353 Marketplace Module Distribution](https://github.com/nold-ai/specfact-cli/issues/353)
