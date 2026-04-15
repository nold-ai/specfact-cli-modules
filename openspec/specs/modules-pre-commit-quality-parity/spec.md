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

