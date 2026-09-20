## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## ADDED Requirements

### Requirement: Severity-Driven Review Enforcement

The review command SHALL derive aggregate truth and exit code from effective
severity, lifecycle, authenticated waiver, uncertainty, and enforcement mode;
score and autofix availability SHALL NOT weaken that result.

#### Scenario: Open effective error blocks non-shadow enforcement

- **GIVEN** an applicable finding has effective severity error and remains open and unwaived
- **WHEN** changed or full enforcement evaluates it
- **THEN** assurance status is FAIL and CI exit code is 1
- **AND** autofix availability and score do not change the result.

#### Scenario: Advisory findings cannot fail by score

- **GIVEN** a completed review contains warning and info findings but no open error or required uncertainty
- **WHEN** aggregate truth is derived at any score
- **THEN** assurance status is PASS and CI exit code is 0
- **AND** the legacy verdict is PASS_WITH_ADVISORY.

#### Scenario: Shadow preserves truth

- **GIVEN** a review has an open error or required uncertainty
- **WHEN** shadow enforcement is selected
- **THEN** assurance status remains FAIL or UNKNOWN respectively
- **AND** CI exit code is 0.

#### Scenario: Analyzer uncertainty fails closed

- **GIVEN** a required analyzer, policy identity, source attribution, or exception check is uncertain
- **WHEN** non-shadow enforcement derives the aggregate
- **THEN** assurance status is UNKNOWN and CI exit code is 1
- **AND** the condition is not converted into a tool-error finding that can be waived by score.
