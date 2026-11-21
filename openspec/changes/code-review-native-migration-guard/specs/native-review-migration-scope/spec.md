## ADDED Requirements

### Requirement: Enforce native-only implementation scope
The repository SHALL reject additions or edits on classified legacy capsule surfaces after the recorded freeze revision, while allowing unchanged historical content and retirement deletions. The diagnostic SHALL name the native execution owner and approved migration order.

#### Scenario: Reject a capsule workflow repair
- **WHEN** an agent changes a frozen capsule workflow
- **THEN** the mandatory boundary check fails and directs work to native execution

#### Scenario: Reject a capsule runtime repair
- **WHEN** an agent changes a frozen capsule runtime file
- **THEN** the boundary check fails

#### Scenario: Reject capsule test expansion
- **WHEN** an agent changes a frozen capsule test
- **THEN** the boundary check fails

#### Scenario: Reject a new capsule file
- **WHEN** a new tracked or untracked file is added under a classified legacy surface
- **THEN** the boundary check fails

#### Scenario: Preserve native work and retirement
- **WHEN** only native-owned code changes or a legacy file is deleted
- **THEN** the scope check accepts that change without claiming runtime acceptance

#### Scenario: Preserve the exact protected-dev reconciliation
- **GIVEN** the maintainer approved the four exact capsule blobs reconciled from PR #524 and protected dev
- **WHEN** the independent scope checker evaluates them
- **THEN** it accepts those exact identities and rejects a later edit to any of the four files
- **AND** the original freeze ref and legacy path classifications remain in force

### Requirement: Fail closed on invalid migration policy
The checker SHALL enforce the trusted-local-native backend and the reviewed blob manifest. It SHALL bind policy to its reviewed fingerprint and reject changes to the baseline or classified paths. The freeze ref is audit metadata. Invalid policy or a requested historical ref that cannot resolve SHALL fail with an actionable diagnostic. The checker SHALL resolve revision arguments to commit IDs without treating them as Git options.

#### Scenario: Reject policy weakening
- **WHEN** an agent advances the freeze revision to include a repair or removes a classified path
- **THEN** the mandatory boundary check rejects the altered policy

#### Scenario: Reject option-shaped revisions
- **WHEN** a policy or historical revision argument contains a Git option
- **THEN** the checker fails without creating an output file

#### Scenario: Reject an alternative backend
- **WHEN** policy selects capsule execution
- **THEN** the boundary check fails rather than reopening the architecture decision

#### Scenario: Reject an unavailable historical baseline
- **WHEN** an explicitly requested historical freeze revision is unavailable
- **THEN** the boundary check fails and identifies the missing revision

### Requirement: Preserve independent gates and test the correction on real history
The same scope checker SHALL run through local mandatory checks and an independent credential-free CI job. The unit SHALL demonstrate rejection of a real historical capsule repair. It SHALL preserve existing signing, independent security and nonpassing legacy review outcomes.

#### Scenario: Reject a historical recurrence
- **WHEN** the checker compares the pre-diagnostics revision with the actual capsule-diagnostics commit
- **THEN** it rejects the classified workflow edit without executing historical subject code

#### Scenario: Run the native scope gate independently
- **WHEN** a pull request changes repository implementation
- **THEN** CI runs the scope check without depending on capsule review success or granting write credentials, and the existing required quality matrix depends on its successful outcome
