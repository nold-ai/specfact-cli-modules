# Tasks: code-review contract and TDD gate runners

## 1. Branch and worktree setup

- [x] 1.1 Review protected-branch state and create
  `feature/code-review-04-contract-test-runners` worktree from `origin/dev`
- [x] 1.2 Run `hatch env create`
- [x] 1.3 Run `hatch run dev-deps` with `SPECFACT_CLI_REPO` pointing to the matching
  `specfact-cli` worktree when available
- [x] 1.4 Run preflight checks: `hatch run smart-test-status` and
  `hatch run contract-test-status`

## 2. Review upstream scope and blockers

- [x] 2.1 Review upstream `specfact-cli` change
  `code-review-04-contract-test-runners`
- [x] 2.2 Confirm bundle-side `ReviewFinding`, `ReviewReport`, Ruff, and Radon outputs
  already exist
- [x] 2.3 Resolve the `code-review-03-type-governance-runners` dependency in
  `specfact-cli-modules`

## 3. Write tests before implementation

- [x] 3.1 Add `tests/unit/specfact_code_review/tools/test_contract_runner.py`
  - [x] 3.1.1 Public function without icontract decorators -> `MISSING_ICONTRACT`
  - [x] 3.1.2 Function with `@require` and `@ensure` -> no finding
  - [x] 3.1.3 Private function -> excluded
  - [x] 3.1.4 CrossHair counterexample -> contracts warning with `tool="crosshair"`
  - [x] 3.1.5 CrossHair timeout -> no exception propagates
  - [x] 3.1.6 CrossHair unavailable -> `tool_error`, AST scan still runs
- [x] 3.2 Add `tests/unit/specfact_code_review/run/test_runner.py`
  - [x] 3.2.1 Tool runners are called in order
  - [x] 3.2.2 Findings are merged across runners
  - [x] 3.2.3 Missing test file -> `TEST_FILE_MISSING`
  - [x] 3.2.4 `no_tests=True` skips the TDD gate
  - [x] 3.2.5 The review run returns `ReviewReport`
- [x] 3.3 Add AST fixture files used by contract-runner tests
- [x] 3.4 Run targeted tests, expect failure, and record evidence in `TDD_EVIDENCE.md`

## 4. Implement bundle runners

- [x] 4.1 Add `packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py`
- [x] 4.2 Export the contract runner from
  `packages/specfact-code-review/src/specfact_code_review/tools/__init__.py`
- [x] 4.3 Add `packages/specfact-code-review/src/specfact_code_review/run/runner.py`
- [x] 4.4 Implement TDD gate path mapping, failure handling, and coverage checks
- [x] 4.5 Ensure all new public functions use `@require`, `@ensure`, and `@beartype`

## 5. Verify behavior and repository quality

- [x] 5.1 Run targeted runner tests, expect pass, and record evidence in
  `TDD_EVIDENCE.md`
- [x] 5.2 Run `hatch run format`
- [x] 5.3 Run `hatch run type-check`
- [x] 5.4 Run `hatch run lint`
- [x] 5.5 Run `hatch run yaml-lint`
- [x] 5.6 Run `hatch run verify-modules-signature --require-signature --enforce-version-bump`
- [x] 5.7 Run `hatch run contract-test`
- [x] 5.8 Run `hatch run smart-test`
- [x] 5.9 Run `hatch run test`

## 6. Documentation and release metadata

- [x] 6.1 Update `docs/modules/code-review.md` with contract runner and TDD gate details
- [x] 6.2 Bump `packages/specfact-code-review/module-package.yaml` patch version and
  review `core_compatibility`
- [x] 6.3 Update `registry/index.json` for the new `specfact-code-review` version and
  artifact metadata

## 7. Finish delivery

- [x] 7.1 Validate the OpenSpec change with `openspec validate code-review-04-contract-test-runners --strict`
- [ ] 7.2 Commit implementation changes on the feature branch
- [ ] 7.3 Push branch and open a PR to `dev`

## 8. Post-review regression fixes

- [x] 8.1 Add failing tests for Semgrep orchestration in `run_review`
- [x] 8.2 Add failing tests covering absolute-path TDD gate inputs
- [x] 8.3 Update contract-runner behavior so missing CrossHair degrades without a blocking finding
- [x] 8.4 Wire `run_semgrep()` into `run_review()` in the documented tool order
- [x] 8.5 Re-run targeted code-review tests and record bugfix evidence in `TDD_EVIDENCE.md`
- [x] 8.6 Re-run required quality gates for the repository

## Post-merge cleanup

- [ ] Remove the worktree, delete the local branch, and prune stale worktree metadata
