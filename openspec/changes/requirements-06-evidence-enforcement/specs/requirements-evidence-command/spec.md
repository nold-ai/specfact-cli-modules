## ADDED Requirements

### Requirement: Requirements evidence is a reusable CLI command

The Requirements module SHALL expose `specfact requirements evidence` as the
single deterministic evaluator for native OpenSpec evidence consumed by local
hooks and CI.

#### Scenario: CI evaluates a base-reference diff

- **GIVEN** a repository and a non-option Git base reference
- **WHEN** `specfact requirements evidence --base-ref <ref> --output <json>`
  runs
- **THEN** it evaluates unique changed active OpenSpec change directories from
  `<ref>...HEAD` in isolated disposable bundles
- **AND** it writes the established JSON verdict before returning its exit code.

#### Scenario: Local hook evaluates staged content

- **GIVEN** the Git index changes an active OpenSpec source
- **WHEN** `specfact requirements evidence --staged --output <json>` runs
- **THEN** it evaluates a disposable snapshot of the Git index
- **AND** unstaged edits under the selected source or linked test target cannot
  affect the verdict.

#### Scenario: Source-selection mode is unambiguous

- **GIVEN** a caller supplies both `--base-ref` and `--staged`, or neither
- **WHEN** the evidence command validates its arguments
- **THEN** it returns an actionable usage error without claiming an evidence
  verdict.

#### Scenario: Failed evidence preserves agent-readable output

- **GIVEN** import diagnostics, failed validation, incomplete test-link
  coverage, or error-level gate findings occur
- **WHEN** the command evaluates a source
- **THEN** it writes JSON and requested Markdown summary containing stable
  source/reason codes before returning non-zero
- **AND** it states that test-execution proof is not included.

#### Scenario: Failed paired-artifact publication restores prior output

- **GIVEN** prior JSON and Markdown evidence artifacts exist
- **AND** replacing either artifact reports an operating-system error after
  the replacement takes effect
- **WHEN** the fallback report publisher handles the error
- **THEN** it restores both prior artifacts before propagating the error.

#### Scenario: Evidence destinations cannot alias each other

- **GIVEN** the JSON output and optional Markdown summary resolve to the same
  filesystem destination or are existing aliases of the same filesystem object
- **WHEN** the evidence command validates its arguments
- **THEN** it returns an actionable usage error before evaluating sources or
  creating either artifact.
- **AND** the direct compatibility adapter returns an argparse usage error
  rather than a traceback.

### Requirement: Local and CI consumers share one evidence contract

The modules pre-commit and CI workflows SHALL invoke the module-owned
Requirements evidence evaluator rather than independent evaluator
implementations. Until the paired core CLI exposes module command routing, a
thin compatibility adapter MAY invoke that evaluator.

#### Scenario: Pre-commit blocks an invalid staged source

- **GIVEN** staged active OpenSpec evidence has a failed verdict
- **WHEN** modules pre-commit Block 2 runs through the module adapter
- **THEN** it stops before code review and contract tests
- **AND** it prints the retained local report path and remediation guidance.

#### Scenario: CI retains a failed command report

- **GIVEN** the requirements-evidence CI adapter returns non-zero
- **WHEN** the workflow completes
- **THEN** it appends the Markdown summary and uploads the JSON report
- **AND** it fails only after those artifacts are retained.
