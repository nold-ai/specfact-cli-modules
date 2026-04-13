# ci-integration Delta Specification (specfact-cli-modules)

## ADDED Requirements

### Requirement: pr-orchestrator skips signature requirement for dev-targeting events

The `verify-module-signatures` job in `pr-orchestrator.yml` SHALL NOT enforce `--require-signature`
for pull requests or pushes targeting `dev`; it SHALL enforce `--require-signature` only for
`main`-targeting events.

#### Scenario: Feature-to-dev PR with unsigned package manifests

- **WHEN** a pull request targets `dev`
- **AND** the PR contains package manifest changes with checksum-only integrity blocks
- **THEN** the `verify-module-signatures` job SHALL pass without `--require-signature`
- **AND** all downstream jobs (`quality`, `contract-tests`, etc.) SHALL not be blocked

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
