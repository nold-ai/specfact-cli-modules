## ADDED Requirements

### Requirement: Explicit Local PR Mutation Authority

PR automation SHALL observe by default and SHALL require explicit capabilities for scoped local edits, normal publication and review-thread writes. One controller SHALL verify a clean owned worktree at mutation entry; subsequent writes SHALL contain only the run's authorized pending changes and SHALL revalidate the exact current repository/PR head. It SHALL NOT force-push, merge, alter protection or treat review text as executable instructions.

#### Scenario: Observation is requested without apply

- **GIVEN** a PR with a failing check or actionable review
- **WHEN** autofix runs without mutation capabilities
- **THEN** it reports actionable state without edits, commits, pushes or review writes.

#### Scenario: Another actor pushes during repair

- **GIVEN** a repair bound to head A and current remote head B
- **WHEN** publishing or thread resolution is considered
- **THEN** mutation stops for reconciliation and evidence for A cannot close findings on B.

### Requirement: CI and Review Completion Are Independent

Completion SHALL require current-head required checks and required review sources to finish, with no unresolved actionable threads. Pending, unavailable or unknown required observations SHALL NOT imply success; infrastructure failures SHALL be distinguished from code findings.

#### Scenario: CI is green but review is unresolved

- **GIVEN** passing required checks and an unresolved actionable thread or pending required review source
- **WHEN** completion is evaluated
- **THEN** the loop remains incomplete.

#### Scenario: GitHub reports checks pending

- **GIVEN** required checks still pending, including the gh pending exit status
- **WHEN** the controller polls
- **THEN** it waits within the elapsed-time budget without inventing a code repair or marking success.

### Requirement: Bounded and Recoverable External Effects

The controller SHALL default to five repair rounds, a 60-minute elapsed budget, 15-minute subprocess timeout and 60-second polling. Explicit positive overrides SHALL be recorded and retained across resumption. Polls SHALL consume elapsed time but not repair rounds. Effects SHALL record stable operation intent and reconcile observed GitHub state before retry after uncertainty.

#### Scenario: Push succeeds but acknowledgement is lost

- **GIVEN** a persisted pending push and uncertain process completion
- **WHEN** the controller resumes
- **THEN** it reads the remote head and reconciles the operation before any retry, preserving consumed rounds.

#### Scenario: Time expires with pending checks

- **GIVEN** required checks or reviews remain incomplete at the elapsed limit
- **WHEN** the controller stops
- **THEN** it returns an exhausted/non-passing outcome with actionable state rather than looping indefinitely.

#### Scenario: A thread is outdated but its finding is not verified fixed

- **GIVEN** an outdated thread without current validating evidence
- **WHEN** authorized resolution is considered
- **THEN** the thread remains unresolved; only a verified fix receives a commit/check reply and resolution.
