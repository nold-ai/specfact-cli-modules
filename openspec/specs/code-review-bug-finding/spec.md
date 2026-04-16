# code-review-bug-finding Specification

## Purpose
TBD - created by archiving change code-review-bug-finding-and-sidecar-venv-fix. Update Purpose after archive.
## Requirements
### Requirement: Semgrep bug-finding rules pass

The system SHALL run a second semgrep pass using a `bugs.yaml` config alongside
the existing `clean_code.yaml` pass. The `bugs.yaml` config SHALL cover Python
security and correctness patterns. When `bugs.yaml` is absent the pass SHALL be
silently skipped without error.

#### Scenario: bugs.yaml present — security findings emitted

- **WHEN** `.semgrep/bugs.yaml` exists in the bundle
- **AND** `run_semgrep_bugs` is called on Python files matching a bug rule
- **THEN** `ReviewFinding` records are returned with `category="security"` or `category="clean_code"`
- **AND** findings reference the matched rule id from `bugs.yaml`

#### Scenario: bugs.yaml absent — pass is a no-op

- **WHEN** no `.semgrep/bugs.yaml` file is discoverable
- **AND** `run_semgrep_bugs` is called
- **THEN** no finding is returned for the missing bugs pass
- **AND** no exception propagates to the caller

#### Scenario: bugs.yaml findings are included in the JSON report

- **WHEN** `specfact code review run --json` is executed on a file matching a bug rule
- **THEN** the output JSON contains findings from both the clean-code and bug-finding passes
- **AND** `run_review` wires `run_semgrep_bugs` alongside the existing `run_semgrep` pass

### Requirement: CrossHair bug-hunt mode

The system SHALL support a `--bug-hunt` flag on `specfact code review run` that
increases the CrossHair per-path timeout to 10 seconds and the total CrossHair
timeout to 120 seconds. Without `--bug-hunt` the existing timeouts SHALL remain
unchanged.

#### Scenario: --bug-hunt increases CrossHair timeouts

- **WHEN** `specfact code review run --bug-hunt --json <file>` is executed
- **THEN** CrossHair runs with `--per_path_timeout 10`
- **AND** the total CrossHair subprocess timeout is 120 seconds

#### Scenario: Default run uses original CrossHair timeouts

- **WHEN** `specfact code review run --json <file>` is executed without `--bug-hunt`
- **THEN** CrossHair runs with `--per_path_timeout 2`
- **AND** the total CrossHair subprocess timeout is 30 seconds

#### Scenario: --bug-hunt is composable with --scope and --out

- **WHEN** `specfact code review run --bug-hunt --scope full --json --out report.json` is executed
- **THEN** the command completes without error
- **AND** the output JSON is written to `report.json`

