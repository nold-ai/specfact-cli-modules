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

### Requirement: Review modes use severity-driven exits

The command SHALL continue accepting `--mode shadow` and `--mode enforce`, with
enforce as the default. For completed reviews, process exit and JSON
`ci_exit_code` SHALL follow C15 aggregate authority: non-shadow FAIL/UNKNOWN exit
1 and PASS/NOT_APPLICABLE exit 0; shadow exits 0 without rewriting aggregate
truth. Existing CLI options and legacy report fields SHALL remain supported,
but compatibility projection SHALL NOT preserve obsolete score/count-based
failures or treat the legacy score as a second enforcement authority. Invalid
arguments and command-execution errors SHALL retain their existing error behavior.

#### Scenario: Default mode uses the C15 predicate

- **GIVEN** the command is invoked without `--mode`
- **WHEN** a completed review derives its result
- **THEN** it applies C15 non-shadow effective-error/required-uncertainty enforcement
- **AND** score thresholds and advisory counts do not change the exit result.

#### Scenario: Shadow preserves failing or unknown truth

- **GIVEN** C15 aggregation yields FAIL or UNKNOWN
- **WHEN** `specfact code review run --mode shadow` completes
- **THEN** the process exit and JSON `ci_exit_code` are 0
- **AND** assurance and the compatibility verdict retain the applicable failing or unknown projection instead of manufacturing a passing review.

#### Scenario: Previously score-failing advisory payload now passes

- **GIVEN** warnings/info lower the legacy score below its former failure threshold, with no applicable open unwaived effective error or required uncertainty
- **WHEN** `specfact code review run --mode enforce` completes
- **THEN** assurance is PASS, process exit and JSON `ci_exit_code` are 0, and the compatibility verdict is PASS_WITH_ADVISORY
- **AND** the score remains descriptive rather than recreating the old failure.

#### Scenario: Mode composes with bug-hunt and JSON

- **WHEN** `specfact code review run --bug-hunt --mode shadow --json --out report.json` runs
- **THEN** the options parse successfully, CrossHair uses bug-hunt timeouts and the governed report is written
- **AND** a completed review exits 0 even when findings would fail enforce mode.

## REMOVED Requirements

### Requirement: Review run supports simplify focus

**Reason**: Its guidance-kind-based blocking scenario conflicts with C15's effective-severity enforcement; info-only safe-mechanical advice must not force exit 1.

**Migration**: Replace this requirement with `Review run supports severity-driven simplify focus` in this delta. Preserve the guided queue and deterministic safe-only rewrites; migrate exit and blocking-count tests to effective-error/required-uncertainty semantics.

### Requirement: --mode shadow and --mode enforce

**Reason**: The default's “as today” wording and legacy-exit scenario retain score-based failures that C15 intentionally replaces.

**Migration**: Replace this requirement with `Review modes use severity-driven exits`. Preserve flag syntax, default enforce, shadow truth, JSON/process-exit parity and bug-hunt composition; migrate score-failure expectations without dropping legacy report fields.

## MODIFIED Requirements

### Requirement: --level error and --level warning

The command SHALL accept `--level error` or `--level warning` for presentation
filtering after signed policy resolves effective severity. Descriptive scores
MAY reflect the displayed findings, but score and presentation filtering SHALL
NOT override C15 aggregation over applicable governed findings or hide required
uncertainty. Raw analyzer severity SHALL remain available separately; it SHALL
NOT select the effective-error enforcement set.

#### Scenario: --level error drops warnings and info

- **GIVEN** a run produces effective warning and effective error findings
- **WHEN** `specfact code review run --level error --json` completes
- **THEN** the displayed findings contain only effective errors, with their raw analyzer severity preserved
- **AND** aggregate truth and exit still follow C15 effective-error and required-uncertainty enforcement, independent of descriptive score.

#### Scenario: --level warning retains errors and warnings

- **GIVEN** a run produces effective info, warning and error findings
- **WHEN** `specfact code review run --level warning --json` completes
- **THEN** the displayed findings exclude effective info and retain effective warnings/errors
- **AND** the display filter does not hide governed blocking or uncertainty from aggregate truth.

#### Scenario: Omitted --level keeps all severities

- **WHEN** `specfact code review run --json` runs without `--level`
- **THEN** findings at all effective severities appear, retaining raw severity evidence
- **AND** advisory counts and score do not become enforcement inputs.
