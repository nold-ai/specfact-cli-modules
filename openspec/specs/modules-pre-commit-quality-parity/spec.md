# modules-pre-commit-quality-parity Specification

## Purpose
TBD - created by archiving change modules-pre-commit-quality-parity. Update Purpose after archive.
## Requirements
### Requirement: Modules Repo Pre-Commit Must Verify Bundle Signatures

The modules repo pre-commit configuration SHALL fail a commit when module payload integrity or required version bumps are stale, and SHALL mirror CI branch policy for cryptographic signatures.

#### Scenario: Signature verification hook is configured

- **WHEN** a developer installs and runs the repository pre-commit hooks
- **THEN** the hook set includes an always-run signature verification command
- **AND** that command always enforces filesystem payload checksums and version-bump policy (`--payload-from-filesystem --enforce-version-bump`)
- **AND** when the active Git branch is `main`, or GitHub Actions sets `GITHUB_BASE_REF` to `main` (PR target branch), that command also enforces `--require-signature`
- **AND** on any other branch (for example `dev` or a feature branch), that command SHALL NOT pass `--require-signature` and SHALL NOT pass `--metadata-only`, matching `pr-orchestrator` behavior for PRs whose base is not `main` (full payload checksum + version bump without cryptographic signature on the branch head)

### Requirement: Modules Repo Pre-Commit Must Catch Formatting And Quality Drift Early

The modules repo pre-commit configuration SHALL run a consolidated local quality hook before commit so common CI failures are caught locally.

#### Scenario: Quality hook enforces formatter safety and repo gates
- **WHEN** a commit includes modules repo code or config changes
- **THEN** the pre-commit configuration runs a local quality helper script
- **AND** that helper script performs formatter safety checks
- **AND** it invokes the relevant modules repo validation commands for yaml, import boundaries, and fast test coverage.

### Requirement: Docs-only pre-commit changes SHALL run docs validation before safe bypass

The modules repo pre-commit helper SHALL run deterministic docs validation,
generated command-overview freshness, command-contract validation, prompt
command validation when applicable, and core documentation accountability for
staged documentation-relevant changes before skipping code-specific review and
contract-test stages. Any `packages/**` or `registry/**` change is
documentation-relevant for generated command artifacts and accountability.

#### Scenario: Docs-only commit with broken link fails pre-commit

- **WHEN** only docs files are staged and one staged docs page introduces a
  broken published-route link
- **THEN** pre-commit runs docs validation
- **AND** pre-commit fails before reporting the change as safe

#### Scenario: Docs-only commit with valid docs skips code-specific checks

- **WHEN** only docs files are staged and docs validation passes
- **THEN** pre-commit may skip code review and contract-test stages
- **AND** pre-commit reports that docs validation passed before applying the
  safe-change bypass

#### Scenario: Manifest-only commit cannot bypass documentation gates

- **WHEN** only a module manifest or registry record is staged
- **THEN** pre-commit regenerates and verifies the generated command artifacts
- **AND** runs the core-accountability gate before the safe-change decision
- **AND** fails if the generated artifacts or core documentation are stale.

### Requirement: Pre-commit and CI docs gates SHALL share validation categories

The local pre-commit docs gate and CI docs review workflow SHALL report the same docs validation categories for matching defects.

#### Scenario: Same broken docs route reports same category locally and in CI

- **WHEN** a docs change introduces a broken generated public route
- **THEN** local pre-commit reports a `published-link` finding
- **AND** the docs review CI workflow reports a `published-link` finding for the same defect category

### Requirement: Non-main module-signature remediation SHALL be deterministic and staged-only

The non-main module signature hook SHALL validate payload checksums and
version policy without rewriting manifests solely because an existing optional
signature cannot be verified locally. If checksum/version remediation is
needed, it SHALL target only module payloads staged for the pending commit.
Unchanged, unstaged, or unrelated failed manifests SHALL not be passed as
explicit repair inputs. Staged-only payload checksums and manifest/version
inputs SHALL be derived from the staged Git index, not unstaged working-tree
content.

#### Scenario: Docs-only commit has no module manifest mutation

- **WHEN** a commit stages only docs, workflow, OpenSpec, or gate files
- **AND** optional manifest signatures cannot be cryptographically verified
  because no local public key is configured
- **THEN** the non-main signature hook does not rewrite, version-bump, or stage
  any `packages/*/module-package.yaml` file
- **AND** it continues with checksum validation and downstream docs gates.

#### Scenario: Staged module payload repair is scoped

- **WHEN** a staged module payload causes checksum or version drift on a
  non-main branch
- **THEN** automatic checksum/version repair may update only that staged
  module's manifest
- **AND** the hook re-verifies without repairing unrelated manifests.

#### Scenario: Staged repair ignores unstaged payload edits

- **WHEN** a module has staged payload changes and different unstaged edits in
  the same module
- **THEN** staged-only repair computes the integrity checksum from the staged
  snapshot
- **AND** it fails rather than overwriting an unstaged manifest edit.

