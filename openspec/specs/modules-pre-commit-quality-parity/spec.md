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

The modules repo pre-commit helper SHALL run deterministic docs validation for staged docs-only changes before skipping code-specific review and contract-test stages.

#### Scenario: Docs-only commit with broken link fails pre-commit

- **WHEN** only docs files are staged and one staged docs page introduces a broken published-route link
- **THEN** pre-commit runs docs validation
- **AND** pre-commit fails before reporting the change as safe

#### Scenario: Docs-only commit with valid docs skips code-specific checks

- **WHEN** only docs files are staged and docs validation passes
- **THEN** pre-commit may skip code review and contract-test stages
- **AND** pre-commit reports that docs validation passed before applying the safe-change bypass

### Requirement: Pre-commit and CI docs gates SHALL share validation categories

The local pre-commit docs gate and CI docs review workflow SHALL report the same docs validation categories for matching defects.

#### Scenario: Same broken docs route reports same category locally and in CI

- **WHEN** a docs change introduces a broken generated public route
- **THEN** local pre-commit reports a `published-link` finding
- **AND** the docs review CI workflow reports a `published-link` finding for the same defect category

