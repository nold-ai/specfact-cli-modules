# TDD Evidence: code-review-04-contract-test-runners

## Pre-implementation failing run

- **Timestamp**: 2026-03-13 11:17:25 +0100
- **Command**:
  `hatch run test -- tests/unit/specfact_code_review/tools/test_contract_runner.py tests/unit/specfact_code_review/run/test_runner.py -v`
- **Result**: failed during collection

### Failure summary

- `ModuleNotFoundError: No module named 'specfact_code_review.tools.contract_runner'`
- `ModuleNotFoundError: No module named 'specfact_code_review.run.runner'`

This is the expected red-phase failure before implementing the new production modules.

## Status

Red phase complete. Production implementation may now begin.

## Post-implementation passing run

- **Timestamp**: 2026-03-13 11:25:18 +0100
- **Command**:
  `hatch run test -- tests/unit/specfact_code_review/tools/test_contract_runner.py tests/unit/specfact_code_review/run/test_runner.py -v`
- **Result**: pass

### Passing summary

- The new `contract_runner` and `run/runner` modules import cleanly.
- The contract-runner and orchestration/TDD-gate scenarios pass under the repo test entrypoint.
- Repository-wide validation is also green for `format`, `type-check`, `lint`,
  `yaml-lint`, `contract-test`, `smart-test`, and `test`.

## Post-merge regression bugfix evidence

### Regression source

- **Timestamp**: 2026-03-13 12:00:00 +0100
- **Source**: merged-change review findings captured against
  `packages/specfact-code-review/src/specfact_code_review/run/runner.py` and
  `packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py`
- **Observed regressions**:
  - `run_review()` omitted `run_semgrep()`
  - CrossHair unavailability produced a blocking `tool_error`
  - absolute reviewed source paths bypassed the TDD gate

### Bugfix targeted passing run

- **Timestamp**: 2026-03-13 13:16:44 +0100
- **Command**:
  `hatch run pytest tests/unit/specfact_code_review/tools/test_contract_runner.py tests/unit/specfact_code_review/run/test_runner.py -q`
- **Result**: pass

### Bugfix passing summary

- The targeted regression suite passes with 14 tests covering Semgrep orchestration,
  CrossHair graceful degradation, and absolute-path TDD gate handling.
- A follow-up import-cycle fix was required after the initial code changes; the final
  implementation now supports direct targeted pytest collection in addition to the repo
  test entrypoints.
