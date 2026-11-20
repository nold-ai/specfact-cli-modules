## MODIFIED Requirements

### Requirement: pr-orchestrator skips signature requirement for dev-targeting events

The `verify-module-signatures` job in `pr-orchestrator.yml` SHALL enforce full checksum and version verification for `dev` and `main`. It SHALL add `--require-signature` for `main` events. The independent `Verify Module Signatures` check SHALL enforce strict verification for pushes to either branch.

#### Scenario: Feature-to-dev PR with unsigned package manifests

- **WHEN** a pull request targets `dev`
- **AND** the PR contains manifests with checksum-only integrity blocks
- **THEN** the orchestrator checks the manifest payloads and versions without a private key.

#### Scenario: Same-repo PR update re-signs manifests after review fixes

- **WHEN** a same-repository PR receives a `pull_request` `synchronize` event after payload changes
- **THEN** verification checks the updated head without signing manifests or pushing to the branch.

#### Scenario: Fork PR remains verify-only

- **WHEN** a fork PR targets `dev` or `main`
- **THEN** signature verification uses read-only permissions and no private key.

#### Scenario: Dev-to-main PR with unsigned manifests (before approval)

- **WHEN** a pull request targets `main` and has an unsigned manifest outside the frozen cutoff
- **THEN** the required signature check fails even if the PR receives a review approval.

#### Scenario: Dev-to-main PR after CI signing commit

- **WHEN** a pull request targets `main` and has valid signatures or exact cutoff trees
- **THEN** the orchestrator accepts the signatures if the payload and version checks also pass.

#### Scenario: Push to main post-merge

- **WHEN** a change lands on `main`
- **THEN** both verification workflows require valid signatures for packages outside the frozen cutoff.
