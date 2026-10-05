## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## ADDED Requirements

### Requirement: Auditable Approved Review Suppression

The module SHALL retain every SpecFact suppression directive as evidence and
SHALL waive an error only through a matching authenticated governance exception.

#### Scenario: Approved scoped error waiver is advisory evidence

- **GIVEN** an exact directive names one canonical rule, a non-empty reason, and an exception identifier
- **AND** trusted base policy contains a matching active, approved, unexpired exception for the canonical path and symbol
- **WHEN** the error is evaluated
- **THEN** it is retained with approved suppression evidence and does not block
- **AND** the passing legacy projection is PASS_WITH_ADVISORY.

#### Scenario: Candidate cannot self-approve a blocker

- **GIVEN** the candidate adds a directive and its own exception record
- **WHEN** protected enforcement authenticates the waiver
- **THEN** the candidate record is not approval authority
- **AND** the error remains blocking unless trusted base policy independently authorizes it.

#### Scenario: Invalid or expired waiver remains blocking

- **GIVEN** a directive has a wildcard, missing reason, ambiguous target, mismatched scope/rule, missing approval, or expired exception
- **WHEN** an error is evaluated
- **THEN** suppression status records the exact failure
- **AND** the error remains open and blocking.

#### Scenario: Directive scope is bounded

- **GIVEN** a valid trailing or standalone directive
- **WHEN** source scope is resolved
- **THEN** a trailing directive applies only to its physical line
- **AND** a standalone directive applies only to the immediately following statement or definition
- **AND** no file-wide inference is allowed.
