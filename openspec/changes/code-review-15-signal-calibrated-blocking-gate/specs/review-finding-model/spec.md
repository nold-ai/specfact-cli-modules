## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## ADDED Requirements

### Requirement: Schema 1.7 Finding Policy and Occurrence Evidence

Schema 1.7 SHALL preserve analyzer-native severity separately from effective
severity and SHALL bind policy/profile identity, suppression state, C14 identity
and location evidence, and duplicate occurrence evidence.

#### Scenario: Stable identity excludes raw line movement

- **GIVEN** a finding moves only because unrelated lines were inserted before its uniquely continuous qualified symbol
- **WHEN** schema 1.7 derives its identity fingerprint
- **THEN** tool, normalized rule, path, qualified symbol, and normalized message parameters identify it
- **AND** raw line numbers remain occurrence evidence rather than identity.

#### Scenario: Exact duplicates preserve multiplicity

- **GIVEN** one analyzer invocation emits identical normalized payloads at the same canonical span more than once
- **WHEN** findings are assembled for presentation
- **THEN** one presentation record carries the exact occurrence count and ordered raw emission digests
- **AND** C14 differential multiset evaluation preserves that count.

#### Scenario: Shared line is not sufficient for deduplication

- **GIVEN** different tools or rules report findings on the same line
- **WHEN** report assembly runs
- **THEN** the findings remain distinct
- **AND** neither tool name, rule, message, nor multiplicity is discarded.

#### Scenario: Blocking attribution conflict is unknown

- **GIVEN** an analyzer-reported name/span cannot be reconciled to one canonical source symbol
- **WHEN** the finding would otherwise be blocking
- **THEN** analyzer evidence is UNKNOWN
- **AND** the implementation does not guess a symbol or silently emit a passing report.
