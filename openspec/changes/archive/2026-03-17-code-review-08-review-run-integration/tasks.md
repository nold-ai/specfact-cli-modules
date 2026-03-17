# Tasks: code-review-08 review run integration

## 1. Rehydrate scope and confirm prerequisites

- [x] 1.1 Reapply the upstream `code-review-08-review-run-integration` scope in this modules repository
- [x] 1.2 Confirm bundle prerequisites from code-review-02 through code-review-07 are present in the dedicated worktree

## 2. Add failing tests and fixtures first

- [x] 2.1 Add clean/dirty review fixtures under `tests/fixtures/review/`
- [x] 2.2 Add command and end-to-end tests for `specfact code review run`
- [x] 2.3 Add cli-val scenario YAML files for `run`, `ledger`, and `rules`
- [x] 2.4 Run the new tests before implementation and record failing evidence in `TDD_EVIDENCE.md`

## 3. Implement the bundle command integration

- [x] 3.1 Complete `packages/specfact-code-review/src/specfact_code_review/run/commands.py`
- [x] 3.2 Adjust runner helpers only where needed to support the command behavior and fixtures

## 4. Validate and document the change

- [x] 4.1 Record passing evidence for tests and runtime execution in `TDD_EVIDENCE.md`
- [x] 4.2 Update `docs/modules/code-review.md` for the run command options, output, and examples
- [x] 4.3 Bump the `specfact-code-review` bundle minor version and update `CHANGELOG.md`
- [x] 4.4 Re-sign and verify the updated module package metadata
- [x] 4.5 Run format, type-check, lint, contract-test, smart-test, targeted test, and docs/runtime validation in the worktree
