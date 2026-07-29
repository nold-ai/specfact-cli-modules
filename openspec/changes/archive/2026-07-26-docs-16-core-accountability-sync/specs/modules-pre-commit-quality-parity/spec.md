## MODIFIED Requirements

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

## ADDED Requirements

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
