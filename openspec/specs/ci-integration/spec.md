# ci-integration Specification

## Purpose
TBD - created by archiving change marketplace-06-ci-module-signing. Update Purpose after archive.
## Requirements
### Requirement: pr-orchestrator skips signature requirement for dev-targeting events

The `verify-module-signatures` job in `pr-orchestrator.yml` SHALL NOT enforce `--require-signature`
for pull requests or pushes targeting `dev`; it SHALL enforce `--require-signature` only for
`main`-targeting events.

#### Scenario: Feature-to-dev PR with unsigned package manifests

- **WHEN** a pull request targets `dev`
- **AND** the PR contains package manifest changes with checksum-only integrity blocks
- **THEN** the CI signing workflow SHALL repair changed same-repo
  `packages/*/module-package.yaml` manifests on the PR branch before verification completes
- **AND** the `verify-module-signatures` job SHALL pass without `--require-signature`
- **AND** all downstream jobs (`quality`, `contract-tests`, etc.) SHALL not be blocked

#### Scenario: Same-repo PR update re-signs manifests after review fixes

- **WHEN** a same-repo pull request targets `dev` or `main`
- **AND** a later `pull_request` `synchronize` event adds review-fix commits that change module
  payloads
- **THEN** the CI signing workflow SHALL re-sign the changed manifests on the PR head branch
- **AND** SHALL commit `chore(modules): ci sign changed modules` only when the manifests changed
- **AND** the workflow SHALL skip this remediation for its own bot-authored signing commit

#### Scenario: Fork PR remains verify-only

- **WHEN** a pull request targets `dev` or `main`
- **AND** the head branch lives in a fork
- **THEN** the CI signing workflow SHALL NOT attempt to push repaired manifests to that branch
- **AND** verification SHALL remain read-only

#### Scenario: Dev-to-main PR with unsigned manifests (before approval)

- **WHEN** a pull request targets `main`
- **AND** one or more `packages/*/module-package.yaml` files lack a valid signature
- **THEN** the `verify-module-signatures` job SHALL fail with `--require-signature`
- **AND** the PR SHALL be blocked from merging

#### Scenario: Dev-to-main PR after CI signing commit

- **WHEN** a pull request targets `main`
- **AND** the CI `sign-modules-on-approval` workflow has committed signed manifests to the PR branch
- **THEN** the `verify-module-signatures` job SHALL pass with `--require-signature`
- **AND** the PR SHALL be unblocked (subject to other required checks)

#### Scenario: Push to main post-merge

- **WHEN** a commit is pushed to `main` (post-merge)
- **THEN** the `verify-module-signatures` job SHALL run with `--require-signature`
- **AND** fail if any `packages/*/module-package.yaml` lacks a valid signature

### Requirement: pre-commit verify mirrors pr-orchestrator signature policy

The repository pre-commit hook that runs `verify-modules-signature.py` SHALL apply the same branch rule as the `verify-module-signatures` CI job: omit `--require-signature` unless the integration target is `main` (local branch `main`, or `GITHUB_BASE_REF=main` on pull request events in Actions).

#### Scenario: Commit on a feature branch without a signing key

- **WHEN** a developer commits on a branch other than `main`
- **AND** manifests satisfy checksum and version-bump policy but lack a valid signature
- **THEN** the pre-commit signature hook SHALL pass (no `--require-signature`)
- **AND** the developer SHALL remain unblocked until a `main`-targeting flow enforces signatures in CI

#### Scenario: Commit on main requires signatures

- **WHEN** a developer commits on branch `main`
- **AND** any `packages/*/module-package.yaml` lacks a valid signature under `--require-signature`
- **THEN** the pre-commit signature hook SHALL fail
