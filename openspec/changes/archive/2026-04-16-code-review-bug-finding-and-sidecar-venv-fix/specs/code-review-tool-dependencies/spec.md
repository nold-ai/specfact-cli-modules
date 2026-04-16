## ADDED Requirements

### Requirement: pip_dependencies cover all external review tools

The `specfact-code-review` bundle manifest (`packages/specfact-code-review/module-package.yaml`) SHALL declare, under `pip_dependencies`, every PyPI distribution required so that **all external** tools invoked by the default `run_review` pipeline (including the TDD gate and CrossHair) can run in a normal bundle install.

#### Scenario: Manifest includes core CLI tools

- **WHEN** a maintainer inspects `module-package.yaml`
- **THEN** `pip_dependencies` includes packages that provide the `ruff`, `radon`, `semgrep`, `basedpyright`, `pylint`, and `crosshair` CLIs on `PATH` after install
- **AND** `pytest` and `pytest-cov` are listed for the targeted test / coverage subprocess

#### Scenario: New runner adds a new external executable

- **WHEN** a new subprocess-backed review step is added to the pipeline
- **THEN** the change updates `pip_dependencies` and the canonical tool map (see design D9) in the same delivery

### Requirement: Runtime detection skips missing tools with a clear tool_error

Before each external tool subprocess runs, the implementation SHALL verify the tool is available. If the executable is not found on `PATH` (or pytest cannot be launched as today’s gate requires), the implementation SHALL **not** invoke that tool and SHALL return **exactly one** `ReviewFinding` per skipped tool.

#### Scenario: Missing Ruff executable produces a skip finding

- **GIVEN** `ruff` is not on `PATH`
- **WHEN** `run_ruff` is executed for a non-empty file list
- **THEN** no `ruff` subprocess is started
- **AND** exactly one finding is returned with `category="tool_error"` and `tool="ruff"`
- **AND** the message states that review checks for `ruff` were **skipped** because it is **not installed** or unavailable, and names the pip package to install (e.g. `ruff`)

#### Scenario: Missing Semgrep does not raise

- **GIVEN** `semgrep` is not on `PATH`
- **WHEN** the semgrep review step runs
- **THEN** the step returns a single skip finding as above for `semgrep`
- **AND** no uncaught exception propagates

#### Scenario: AST clean-code pass requires no extra CLI dependency

- **WHEN** `run_ast_clean_code` runs
- **THEN** it does not depend on a `pip_dependencies` CLI entry (stdlib / in-package Python only)

#### Scenario: TDD gate reports pytest unavailable clearly

- **GIVEN** `pytest` (or coverage support) is missing such that the targeted test subprocess cannot run
- **WHEN** `_evaluate_tdd_gate` would run tests
- **THEN** findings include a `tool_error` for `pytest` (or the agreed tool id) with a skip / not-installed style message referencing `pytest` and/or `pytest-cov`

### Requirement: No misleading errors when the binary is absent

If a tool executable is missing, runners SHALL NOT surface generic failures such as “Unable to parse JSON output” that imply the tool ran but returned bad data.

#### Scenario: Ruff missing is not reported as a parse failure

- **GIVEN** `ruff` is absent
- **WHEN** `run_ruff` completes
- **THEN** the user-visible message indicates the tool was **skipped** / **not installed**, not a JSON parse error from Ruff output

### Requirement: Automated guard for manifest vs tool map

The repository SHALL include an automated check (unit test or small validation script invoked by the normal test suite) that fails if `module-package.yaml` `pip_dependencies` omits any package from the canonical tool → pip map for the default pipeline.

#### Scenario: Drift fails CI

- **GIVEN** the canonical map lists a pip package for an active runner
- **WHEN** that package is removed from `pip_dependencies` without updating the map
- **THEN** `hatch run test` (or the chosen gate) fails with a clear assertion message
