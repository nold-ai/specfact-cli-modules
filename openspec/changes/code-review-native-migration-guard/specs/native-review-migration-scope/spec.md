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

### Requirement: Fail closed on invalid migration policy
The checker SHALL accept only the established trusted-local-native execution direction and the committed reviewed baseline manifest. The freeze revision SHALL remain audit metadata rather than a default runtime dependency. An invalid policy or unavailable explicitly requested historical revision SHALL fail with an actionable diagnostic.

The policy SHALL be bound to the reviewed fingerprint in the checker. A policy-only change that alters its baseline or removes a classified surface SHALL fail rather than silently authorizing capsule work. This binding does not authenticate a candidate that also rewrites the checker and its fingerprint. Revision arguments SHALL resolve to commit identities before comparison and SHALL never be interpreted as Git options.

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
