# ci-module-signing-on-approval Specification (specfact-cli-modules)

## ADDED Requirements

### Requirement: Sign packages manifests on PR approval

The system SHALL automatically sign changed `packages/*/module-package.yaml` manifests using CI
secrets when a pull request targeting `dev` or `main` is approved, and SHALL commit the signed
manifests back to the PR branch.

#### Scenario: PR to dev approved with package module changes

- **WHEN** a pull request targeting `dev` is approved by a reviewer
- **AND** the PR contains changes to one or more files under `packages/`
- **THEN** the CI signing workflow SHALL discover all `packages/*/module-package.yaml` manifests
  whose payload changed relative to `origin/dev`
- **AND** SHALL sign them using `SPECFACT_MODULE_PRIVATE_SIGN_KEY` and
  `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
- **AND** SHALL commit the updated manifests back to the PR branch

#### Scenario: PR to main approved with package module changes

- **WHEN** a pull request targeting `main` is approved
- **AND** the PR contains changes to one or more files under `packages/`
- **THEN** the CI signing workflow SHALL sign all changed manifests relative to `origin/main`
- **AND** SHALL commit the signed manifests back to the PR branch before merge

#### Scenario: PR approved with no package changes

- **WHEN** a pull request is approved
- **AND** no files under `packages/` have changed relative to the base branch
- **THEN** the CI signing workflow SHALL exit cleanly with no commit

#### Scenario: Missing signing secret

- **WHEN** the signing workflow triggers on approval
- **AND** `SPECFACT_MODULE_PRIVATE_SIGN_KEY` is empty or unset
- **THEN** the workflow SHALL fail with a clear error naming the missing secret
- **AND** SHALL NOT commit partial changes

### Requirement: Manifest discovery covers packages directory

The signing workflow SHALL discover module manifests from the `packages/` directory tree, not only
from `src/specfact_cli/modules/` or `modules/` (which do not exist in this repository).

#### Scenario: Sign only changed packages manifests

- **WHEN** the signing workflow runs with changes across multiple packages
- **AND** only a subset of packages have payload changes
- **THEN** only the changed `packages/*/module-package.yaml` files SHALL be signed and committed
- **AND** unchanged package manifests SHALL NOT be modified

#### Scenario: Sign workflow produces idempotent output

- **WHEN** the signing workflow runs twice on the same package payload
- **THEN** the resulting `integrity:` block SHALL be byte-for-byte identical
- **AND** the second run SHALL produce no git diff and SHALL skip the commit
