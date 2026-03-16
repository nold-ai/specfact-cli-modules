# TDD Evidence: code-review-08-review-run-integration

## Failing First

- `2026-03-16`: `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/e2e/specfact_code_review/test_review_run_e2e.py -q`
  failed during collection before the intended command assertions because the
  worktree had not yet installed the sibling `specfact-cli` dependency set.
- `2026-03-16`: After `hatch run dev-deps`, rerunning the same pytest command
  failed as expected against the stubbed `run/commands.py` surface. The new
  tests could not monkeypatch `run_review`, `_changed_files_from_git_diff`, or
  `_apply_fixes` because those functions did not exist yet.

## Passing

- `2026-03-16`: `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/e2e/specfact_code_review/test_review_run_e2e.py -q`
  passed with `7 passed in 7.42s`.
- `2026-03-16`: `hatch run format`, `hatch run type-check`, `hatch run yaml-lint`,
  `hatch run validate-cli-contracts`, and `hatch run lint` all passed in the
  dedicated worktree.
- `2026-03-16`: `hatch run contract-test`, `hatch run smart-test`, and
  `hatch run test -- -q` each passed with the full `337` test suite green.
- `2026-03-16`: `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`
  verified all six module manifests, including `packages/specfact-code-review/module-package.yaml`.
- `2026-03-16`: runtime validation passed after installing the updated bundle
  into the worktree-local `.specfact/modules/specfact-code-review` shadow root:
  - `hatch run specfact code review run --json tests/fixtures/review/clean_module.py` exited `0` with `overall_verdict=PASS`
  - `hatch run specfact code review run --json tests/fixtures/review/dirty_module.py` exited `1` with `overall_verdict=FAIL`
- `2026-03-16`: `openspec validate code-review-08-review-run-integration --strict`
  reported the change as valid. The command emitted non-fatal telemetry flush
  noise because network access to `edge.openspec.dev` is unavailable in this environment.
