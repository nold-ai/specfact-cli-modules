# Tasks: code-review-10 review scope modes

## 1. Rehydrate scope and confirm prerequisites

- [x] 1.1 Reapply upstream `code-review-10-review-scope-modes` in this modules repository
- [x] 1.2 Confirm `code-review-08-review-run-integration` behavior is the baseline for the bundle command
- [x] 1.3 Confirm the upstream default remains changed-only auto-discovery for automation compatibility

## 2. Add failing tests and fixtures first

- [x] 2.1 Add or extend unit tests for `--scope changed` and `--scope full`
- [x] 2.2 Add failing tests for repeatable `--path` subtree filtering in both scope modes
- [x] 2.3 Add failing tests for empty-scope and invalid targeting combinations
- [x] 2.4 Update cli-val `specfact-code-review-run` scenarios for changed-only, full-review, and subtree-filtered runs
- [x] 2.5 Run the new tests before implementation and record failing evidence in `TDD_EVIDENCE.md`

## 3. Implement bundle scope selection

- [x] 3.1 Extend `packages/specfact-code-review/src/specfact_code_review/run/commands.py` with `--scope` and repeatable `--path`
- [x] 3.2 Add or update helper logic for deterministic candidate-file selection and recursive subtree filtering
- [x] 3.3 Reject invocations that mix positional files with auto-scope controls
- [x] 3.4 Emit actionable failures when selected filters leave no reviewable files

## 4. Validate and document the change

- [x] 4.1 Record passing evidence for unit, e2e, and cli-val checks in `TDD_EVIDENCE.md`
- [x] 4.2 Update `docs/modules/code-review.md` with changed-only, full-review, and subtree-review examples
- [x] 4.3 Bump the `specfact-code-review` bundle minor version and update `CHANGELOG.md`
- [x] 4.4 Re-sign and verify the updated module package metadata
- [x] 4.5 Run format, type-check, lint, yaml-lint, contract-test, smart-test, targeted tests, runtime/docs validation, signed-manifest verification, and the final `test` gate in the worktree
