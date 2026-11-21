## MODIFIED Requirements

### Requirement: Sign packages manifests on PR approval

Approval events SHALL leave module signatures and contributor branches untouched. The public verifier SHALL run independently of the protected V2 signing environment.

#### Scenario: PR to dev approved with package module changes

- **WHEN** a reviewer approves a PR to `dev` with package changes
- **THEN** the approval leaves the branch untouched and the required checks assess the submitted head.

#### Scenario: PR to main approved with package module changes

- **WHEN** a reviewer approves a PR to `main` with package changes
- **THEN** the approval leaves the branch untouched and strict verification still requires valid signatures.

#### Scenario: PR approved with no package changes

- **WHEN** a reviewer approves a PR without package changes
- **THEN** approval makes no manifest commit.

#### Scenario: Approval workflow does not trigger on PR synchronize events

- **WHEN** a PR head changes after approval
- **THEN** the signature check verifies the new head without signing it.

#### Scenario: Missing signing secret

- **WHEN** the verification job runs without a private key
- **THEN** it verifies the submitted manifests using the tracked public key.

#### Scenario: Fork PR is out of scope for automated signing

- **WHEN** a fork PR receives an approval
- **THEN** the approval consumes no signing secret and makes no manifest commit.

### Requirement: Manifest discovery covers packages directory

Public verification and protected reproducibility SHALL discover manifests under `packages/`. The reproducibility check SHALL preserve the bytes of every manifest.

#### Scenario: Sign only changed packages manifests

- **WHEN** the protected reproducibility job runs
- **THEN** it checks existing replacement signatures and validates frozen trees without changing either.

#### Scenario: Sign workflow produces idempotent output

- **WHEN** the protected job repeats verification of the same checkout
- **THEN** the signature checks produce the same verdict and leave the manifests untouched.
