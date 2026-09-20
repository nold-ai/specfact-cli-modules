## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## ADDED Requirements

### Requirement: Signed Signal-Calibrated Review Policy

The Code Review module SHALL map analyzer output to effective severity through a
signed policy whose identity, context decision, and thresholds are report evidence.

#### Scenario: Production Radon and KISS thresholds are calibrated

- **GIVEN** a general production function is analyzed
- **WHEN** cyclomatic complexity, nesting, LOC, and parameter metrics are mapped
- **THEN** CC 13-25 is warning and CC >=26 is error
- **AND** nesting 4-6 is warning and nesting >=7 is error
- **AND** LOC >80 remains warning with no initial error tier
- **AND** parameter count 6-9 is warning and >=10 is error.

#### Scenario: Context prevents structural false blockers

- **GIVEN** a finding belongs to a test, resolved Typer/Click callback, or constrained override
- **WHEN** KISS policy is evaluated
- **THEN** test structural metrics are advisory
- **AND** CLI/constrained parameter-count findings are exempt
- **AND** the context source and policy decision are recorded.

#### Scenario: Pylint and Semgrep mappings use the initial allowlist

- **GIVEN** Pylint or Semgrep emits a governed finding
- **WHEN** the signed initial policy maps it
- **THEN** Pylint C0415/C0301 are info, E1101 is error, and other E/F rules are advisory pending evidence
- **AND** Semgrep swallowed-exception, eval/exec, os.system, and unsafe yaml.load rules are error
- **AND** context-dependent pickle/password findings remain warning.

#### Scenario: Ambiguous path policy fails closed

- **GIVEN** explicit policy path scopes assign incompatible contexts to one symbol
- **WHEN** effective policy is resolved
- **THEN** policy status is UNKNOWN
- **AND** first-match ordering is not used.
