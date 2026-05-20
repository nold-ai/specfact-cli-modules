# TDD Evidence: code-review-ai-bloat-detection

## Readiness

- 2026-05-20: Refreshed GitHub hierarchy cache with `python scripts/sync_github_hierarchy_cache.py`.
- 2026-05-20: Verified issue #269 is open/Todo with labels and project assignment. Parent Feature #175 is closed/Done and only lists #174; this hierarchy mismatch is documented in the proposal/design before implementation.
- 2026-05-20: `openspec validate code-review-ai-bloat-detection --strict` -> PASS.

## Failing Before

- 2026-05-20: `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_scorer.py tests/unit/specfact_code_review/tools/test_semgrep_runner.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/scripts/test_pre_commit_code_review.py tests/unit/test_bundle_resource_payloads.py -q` -> FAIL as expected.
  - `ModuleNotFoundError: No module named 'specfact_code_review.tools.ai_bloat_runner'`
  - `ModuleNotFoundError: No module named 'specfact_cli'` for the resource payload test before local dev dependency bootstrap.

## Implementation Evidence

- 2026-05-20: `hatch run dev-deps` -> PASS.
- 2026-05-20: `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_scorer.py tests/unit/specfact_code_review/tools/test_semgrep_runner.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/scripts/test_pre_commit_code_review.py tests/unit/test_bundle_resource_payloads.py -q` -> PASS (`131 passed, 2 warnings`).
- 2026-05-20: `PYTHONPATH=packages/specfact-code-review/src hatch run python ... run_ai_bloat(packages/specfact-code-review, packages/specfact-project)` -> 144 advisory candidates; no automatic rewrites applied; accepted-rewrite LOC delta 0.
- 2026-05-20: Created core follow-up issue https://github.com/nold-ai/specfact-cli/issues/573 for the parallel core README/docs callout.
- 2026-05-20: `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/tools/test_semgrep_runner.py -q` -> PASS (`40 passed`) after tightening the optional-parameter heuristic and shared Semgrep append path.

## Quality Gates

- 2026-05-20: `hatch run format` -> PASS.
- 2026-05-20: `hatch run type-check` -> PASS (`0 errors, 0 warnings, 0 notes`).
- 2026-05-20: `hatch run lint` -> PASS (`ruff`, `basedpyright`, and `pylint 10.00/10`).
- 2026-05-20: `hatch run yaml-lint` -> PASS (`Validated 6 manifests and registry/index.json`).
- 2026-05-20: `hatch run check-bundle-imports` -> PASS.
- 2026-05-20: `hatch run validate-prompt-commands` -> PASS.
- 2026-05-20: `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` -> FAIL once after source edits changed the `specfact-code-review` checksum.
- 2026-05-20: `hatch run sign-modules --allow-unsigned --payload-from-filesystem packages/specfact-code-review/module-package.yaml` -> PASS.
- 2026-05-20: `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` -> PASS (`Verified 6 module manifest(s)`).
- 2026-05-20: `hatch run contract-test` -> PASS (`693 passed, 2 warnings`).
- 2026-05-20: `hatch run smart-test` -> PASS (`693 passed, 2 warnings`).
- 2026-05-20: `hatch run test` -> PASS (`693 passed, 2 warnings`).
- 2026-05-20: `openspec validate code-review-ai-bloat-detection --strict` -> PASS.

## Code Review Gate

- 2026-05-20: `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope full` -> FAIL before analysis because the local runtime had not linked `specfact-codebase`.
- 2026-05-20: Linked local development modules with `hatch run link-dev-module specfact-codebase --force` and `hatch run link-dev-module specfact-code-review --force`; reran review with `SPECFACT_ALLOW_UNSIGNED=1`.
- 2026-05-20: `SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope full` -> FAIL due pre-existing full-repository findings outside this change: 379 errors, 601 warnings, 115 `ai_bloat` info findings.
- Modified-artifact triage after fixes: no new `ai_bloat`, DRY, YAGNI, type-safety, testing, or contract findings remain on added/changed files. The only modified-file findings left are two existing warnings on `packages/specfact-code-review/src/specfact_code_review/run/runner.py::run_review`: cyclomatic complexity 13 and 7 parameters. Refactoring the public runner signature is out of scope for this change and would alter command orchestration semantics.
