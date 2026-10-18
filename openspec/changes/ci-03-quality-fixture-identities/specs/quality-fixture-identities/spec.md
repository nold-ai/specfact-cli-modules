## ADDED Requirements

### Requirement: Full suite selects the declared core baseline

The quality workflow SHALL retain the dynamic paired core for its existing integration checks and SHALL give only the existing full suite an independent immutable core 0.55.4 checkout. The baseline checkout SHALL occur after candidate formatting and lint gates. The workflow SHALL verify that checkout's commit and tree before use and SHALL retain the exact `hatch run test` command and unconditional declared dependency assertion.

#### Scenario: Full suite overrides the paired default

- **GIVEN** a quality job with a dynamically selected paired core
- **WHEN** the Full Test Suite step executes
- **THEN** its step-scoped dependency path selects verified core 0.55.4 and preceding paired checks retain the paired core path.

### Requirement: Installed smoke selects the reviewed modules fixture

The workflow SHALL read the paired core smoke fixture lock, require repository `nold-ai/specfact-cli-modules` and full commit/tree SHA identities, and check out the fixture into a clean sibling directory with credentials disabled. It SHALL verify commit, tree and clean status before the existing smoke command receives the absolute fixture path. The verified smoke checkout SHALL move outside the candidate workspace before candidate formatting and lint gates. All six launchers SHALL remain enabled.

#### Scenario: Valid lock supplies the smoke checkout

- **GIVEN** a paired core with a valid smoke fixture lock
- **WHEN** fixture preparation and smoke execution run
- **THEN** the checkout uses the lock commit and the smoke receives the verified relocated path outside the candidate workspace with direct, hatch-source, pip-editable, pipx, uv-run and uvx launchers.

#### Scenario: Invalid lock is rejected

- **GIVEN** malformed JSON, a wrong repository, a missing identity or a non-full commit/tree identity
- **WHEN** fixture identity is read
- **THEN** preparation fails before emitting checkout outputs.

#### Scenario: Unauthenticated fixture is rejected

- **GIVEN** a checkout with a wrong commit, wrong tree or dirty status
- **WHEN** fixture verification runs
- **THEN** verification fails before exporting a smoke fixture path.

### Requirement: Approved orchestrator candidates retain guarded local deferral

The local quality hook SHALL include `.github/workflows/pr-orchestrator.yml` in its existing candidate-path eligibility check for an explicitly approved local ARM64 Darwin feature-worktree review deferral. It SHALL preserve all existing guard conditions, every other Block 2 check and the DEFERRED warning. Mandatory blocking exact-head Linux candidate and independent signed review SHALL remain required before merge.

#### Scenario: Orchestrator-only candidate defers local review

- **GIVEN** an explicitly approved local ARM64 Darwin feature worktree with indexed blocking candidate and independent review jobs
- **WHEN** the staged candidate delta against origin/dev changes the orchestrator workflow with accompanying regression tests and change evidence
- **THEN** the hook reports DEFERRED, never PASS, and executes the remaining Block 2 checks, including contracts.

#### Scenario: Orchestrator eligibility preserves rejection guards

- **GIVEN** an orchestrator candidate in CI, on Linux, with invalid opt-in, or without indexed independent review, including an unstaged restoration
- **WHEN** the local deferral is requested
- **THEN** the hook rejects the deferral; an unrelated workflow candidate also remains ineligible even if origin/dev advanced.
