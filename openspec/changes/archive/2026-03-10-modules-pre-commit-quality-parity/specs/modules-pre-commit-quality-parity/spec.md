## ADDED Requirements

### Requirement: Modules Repo Pre-Commit Must Verify Bundle Signatures

The modules repo pre-commit configuration SHALL fail a commit when bundle signatures or required version bumps are stale.

#### Scenario: Signature verification hook is configured
- **WHEN** a developer installs and runs the repository pre-commit hooks
- **THEN** the hook set includes an always-run signature verification command
- **AND** that command enforces both required signatures and version-bump policy.

### Requirement: Modules Repo Pre-Commit Must Catch Formatting And Quality Drift Early

The modules repo pre-commit configuration SHALL run a consolidated local quality hook before commit so common CI failures are caught locally.

#### Scenario: Quality hook enforces formatter safety and repo gates
- **WHEN** a commit includes modules repo code or config changes
- **THEN** the pre-commit configuration runs a local quality helper script
- **AND** that helper script performs formatter safety checks
- **AND** it invokes the relevant modules repo validation commands for yaml, import boundaries, and fast test coverage.
