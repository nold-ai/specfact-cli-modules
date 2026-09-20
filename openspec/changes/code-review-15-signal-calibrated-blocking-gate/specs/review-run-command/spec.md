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

### Requirement: Review run supports severity-driven simplify focus

The `specfact code review run` command SHALL accept `--focus simplify` as a
targeted review focus for simplification feedback. The focus SHALL retain
findings that belong in the simplification queue and SHALL classify them with
actionable guidance. Simplify enforcement SHALL use the same C15 effective-error
and required-uncertainty predicate as other review enforcement; guidance kind
or rewrite availability alone SHALL NOT block or elevate a finding's severity.
Any reported blocking simplification count SHALL count only applicable open
unwaived effective-error findings; required uncertainty SHALL remain separately
visible as UNKNOWN rather than inventing an error finding.

#### Scenario: Simplify focus emits guided simplification queue

- **WHEN** `specfact code review run --focus simplify --json --out .specfact/code-review.json` completes
- **THEN** the JSON report SHALL retain simplification-focused findings
- **AND** retained findings SHALL include guidance metadata for actionability, preservation, or design judgment
- **AND** the report SHALL include a simplification summary when guided findings are present.

#### Scenario: Simplify enforce keeps advisory mechanical debt non-blocking

- **GIVEN** a completed simplify review contains unresolved `safe_mechanical`, `needs_tests`, `design_judgment` or `preserve` findings at info or warning severity, with no applicable open unwaived effective error or required uncertainty
- **WHEN** `specfact code review run --focus simplify --mode enforce` runs
- **THEN** assurance SHALL be PASS, CI exit code SHALL be 0 and the blocking simplification count SHALL be zero
- **AND** recommendations remain visible without being reclassified as errors to preserve the old exit behavior.

#### Scenario: Simplify enforce retains effective-error and uncertainty blocking

- **GIVEN** simplify enforcement has an applicable open unwaived effective error or required uncertainty
- **WHEN** non-shadow enforcement evaluates it
- **THEN** assurance SHALL be FAIL or UNKNOWN respectively and CI exit code SHALL be 1
- **AND** guidance kind, score and rewrite availability SHALL NOT waive that outcome.

#### Scenario: Simplify fix applies only safe mechanical rewrites

- **WHEN** `specfact code review run --focus simplify --fix` runs
- **THEN** automatic rewrites SHALL be limited to deterministic safe-mechanical findings
- **AND** the command SHALL rerun review after applying rewrites
- **AND** the JSON report SHALL record applied, failed, and still-recommended outcomes.

## REMOVED Requirements

### Requirement: Review run supports simplify focus

**Reason**: Its guidance-kind-based blocking scenario conflicts with C15's effective-severity enforcement; info-only safe-mechanical advice must not force exit 1.

**Migration**: Replace this requirement with `Review run supports severity-driven simplify focus` in this delta. Preserve the guided queue and deterministic safe-only rewrites; migrate exit and blocking-count tests to effective-error/required-uncertainty semantics.
