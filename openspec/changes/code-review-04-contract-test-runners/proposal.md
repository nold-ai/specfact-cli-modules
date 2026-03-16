# Change: Contract and TDD Gate Runners for the code-review bundle

## Why

The `specfact-code-review` bundle already ships the `ReviewFinding` and `ReviewReport`
models plus the Ruff and Radon runner implementations, but it still lacks the
contract-focused and test-gating runners required by the upstream `specfact-cli`
OpenSpec change `code-review-04-contract-test-runners`.

Without these bundle-side runners, the code-review package cannot enforce two of the
highest-value quality checks in this codebase:

- public APIs should declare `icontract` expectations
- changed source modules should have corresponding tests and acceptable coverage

## What Changes

- **NEW**: `specfact_code_review.tools.contract_runner` for AST scanning of public
  functions missing `@require` / `@ensure`, plus a CrossHair fast pass
- **NEW**: `specfact_code_review.run.runner` to orchestrate available tool runners,
  apply the TDD gate, and build `ReviewReport`
- **NEW**: unit tests for contract scanning, CrossHair degradation behavior,
  orchestration order, and TDD gate findings
- **NEW**: test fixtures used by AST scan coverage
- **UPDATED**: bundle docs for contract runner and TDD gate behavior
- **UPDATED**: bundle release metadata for the next `specfact-code-review` version
- **UPDATED**: regression fixes for the shipped runner wiring and graceful
  degradation paths:
  - include `run_semgrep()` in the main `run_review()` orchestration flow
  - treat missing CrossHair as a non-blocking degradation signal instead of a
    hard error
  - accept both relative and absolute reviewed source paths in the TDD gate

## Impact

- No breaking public command changes
- Keeps the `specfact-code-review` bundle aligned with upstream `specfact-cli`
  OpenSpec scope
- Depends on bundle-side availability of the `code-review-03` type/governance runners
  before implementation can proceed
- Requires bundle version and registry metadata updates once code lands

## Source Tracking

- **Upstream OpenSpec change**:
  `../specfact-cli/openspec/changes/code-review-04-contract-test-runners/`
- **Target repository**: `nold-ai/specfact-cli-modules`
