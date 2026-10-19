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

The local quality hook SHALL include `.github/workflows/pr-orchestrator.yml` in its existing candidate-path eligibility check for an explicitly approved local ARM64 Darwin feature-worktree review deferral. It SHALL preserve all existing guard conditions, every other Block 2 check and the DEFERRED warning. Mandatory blocking exact-head Linux candidate and independent signed review SHALL remain required before merge. Deferral eligibility SHALL require the indexed orchestrator to preserve the supported pull-request trigger, capsule path detection and output, mandatory reusable workflow call, and blocking quality prerequisite. Unsupported routing SHALL reject local deferral. Workflow-level defaults SHALL be absent from the supported contract, including run shell and working-directory overrides.

#### Scenario: Orchestrator-only candidate defers local review

- **GIVEN** an explicitly approved local ARM64 Darwin feature worktree with indexed blocking candidate and independent review jobs
- **WHEN** the staged candidate delta against origin/dev changes the orchestrator workflow with accompanying regression tests and change evidence
- **THEN** the hook reports DEFERRED, never PASS, and executes the remaining Block 2 checks, including contracts.

#### Scenario: Orchestrator eligibility preserves rejection guards

- **GIVEN** an orchestrator candidate in CI, on Linux, with invalid opt-in, or without indexed independent review, including an unstaged restoration
- **WHEN** the local deferral is requested
- **THEN** the hook rejects the deferral; an unrelated workflow candidate also remains ineligible even if origin/dev advanced.

#### Scenario: Indexed orchestration preserves mandatory review scheduling

- **GIVEN** an otherwise eligible orchestrator or capsule-payload candidate
- **WHEN** indexed orchestration removes or disables the pull-request trigger, capsule filter/output, customer workflow call, or blocking quality prerequisite, or introduces workflow-level run defaults
- **THEN** the hook rejects deferral, including when an unstaged restoration repairs the working copy; only the indexed scheduling contract permits DEFERRED.

#### Scenario: Exact reviewed orchestration bytes authorize deferral

- **GIVEN** an otherwise eligible local worktree
- **WHEN** the indexed orchestrator differs by any byte from the reviewed workflow, including comments, quality containers, root or job environment, runners or defaults, or is absent
- **THEN** local deferral fails even if the working copy restores the reviewed bytes; a literal reviewed SHA-256 pin must be updated through review before any changed workflow is eligible.

### Requirement: Bash fixture proofs execute on the host

The default Hatch full test command SHALL explicitly execute the quality fixture identity host proof before the ordinary test suite. All seven lock validation cases and five checkout verification cases SHALL remain mandatory. Static workflow and host scheduling assertions SHALL remain in the unit suite. Capsule capabilities SHALL remain unchanged.

#### Scenario: Full tests retain the host proof

- **GIVEN** the default Hatch test entrypoint
- **WHEN** the quality fixture identity proofs run
- **THEN** the twelve Bash cases run on the host and the static unit assertion rejects removal of their explicit schedule.

### Requirement: Indexed schedule validation has capsule-safe coverage

The declared coverage sources SHALL include the qualified `scripts.validate_capsule_ci_schedule` module. Capsule-safe unit tests SHALL execute its byte validator and command entrypoint with the external Git read mocked. Reviewed bytes SHALL succeed; changed bytes and missing index entries SHALL return a refusal. Existing real Git index host proofs, coverage thresholds, exclusions and hosted review requirements SHALL remain intact.

#### Scenario: The native coverage adapter observes the schedule validator

- **GIVEN** the repository coverage policy and capsule-safe schedule unit tests
- **WHEN** pytest executes the tests and the portable coverage adapter evaluates the validator
- **THEN** coverage contains the validator and satisfies the existing per-source threshold without enabling subprocess capabilities.


### Requirement: Structured review failures retain bounded diagnostic observations

The independent review failure projector SHALL publish the existing allowlisted analyzer snapshot sides and CrossHair failure classes for complete structured reports as well as oversized reports. It SHALL derive these observations from the existing validated evidence source and preserve complete JSON validation, duplicate-key rejection, input bounds, private output handling, review status and exit behavior. It SHALL NOT publish raw messages, paths, tokens, command arguments or arbitrary analyzer identifiers.

#### Scenario: Structured contracts evidence identifies its incomplete side

- **GIVEN** a complete structured report with contracts error or UNKNOWN evidence
- **WHEN** the independent failure projector executes
- **THEN** it publishes only allowlisted incomplete snapshot sides and recognized CrossHair tool-error classes, with private canaries absent from stdout and stderr.

#### Scenario: Invalid or unrelated evidence cannot supply diagnostic classes

- **GIVEN** malformed or duplicate-key JSON, an unrelated tool or category, or an unknown failure message
- **WHEN** the independent failure projector executes
- **THEN** validation and allowlists prevent unsupported classifications and private output, while the existing oversized-report behavior remains bounded.


### Requirement: Local deferral executes caller-selected immutable policy

The existing local deferral hook SHALL require the trusted local caller to provide `SPECFACT_CODE_REVIEW_POLICY_COMMIT` as a full lowercase 40-character commit SHA and `SPECFACT_CODE_REVIEW_POLICY_PYTHON` as an absolute executable host Python path selected outside the candidate environment. It SHALL extract the existing schedule checker from that exact commit with Git replacement objects disabled, execute the nonempty blob from a private temporary directory with Python `-I -S`, preserve the candidate repository as working directory, and propagate refusal or execution failure. Missing or invalid selection, a non-commit object, unavailable checker blob, and Git or Python failure SHALL refuse deferral without falling back to candidate code, HEAD, repository configuration or candidate Hatch Python. The temporary directory SHALL be cleaned after execution.

This is an explicit trusted-caller approval boundary, not protected-branch policy or hostile-code isolation. Caller edits or hook bypass are outside this local check; candidate hook/control changes still require independent review. Existing platform, worktree, branch, CI, eligible-path and blocking-job guards and mandatory hosted exact-head acceptance SHALL remain intact.

#### Scenario: Candidate policy cannot approve changed indexed orchestration

- **GIVEN** a caller-selected reviewed policy commit and external host Python
- **WHEN** the candidate changes indexed orchestration and updates its checker pin or replaces its working-copy checker with a successful canary, including an unstaged workflow restoration
- **THEN** immutable policy refuses the changed indexed bytes and the candidate checker never executes.

#### Scenario: Explicit immutable selection fails closed

- **GIVEN** an otherwise eligible local candidate
- **WHEN** the commit or Python selection is missing or invalid, the selected object is not a commit, the checker is absent or empty, or Git or Python fails
- **THEN** the hook refuses deferral without executing candidate policy; Git replacement objects cannot substitute an approving checker.

#### Scenario: Reviewed indexed bytes retain local deferral

- **GIVEN** exact reviewed indexed orchestration and explicit valid caller selections
- **WHEN** the existing local eligibility checks execute
- **THEN** the hook reports DEFERRED and retains contracts and all other checks, while cleaning its temporary checker.
