# TDD Evidence

## 2026-03-31

- `2026-03-31T00:56:00+02:00` Bootstrap:
  `hatch run dev-deps`
  linked the local `specfact-cli` checkout into this worktree so the bundle tests and review runner could execute against the live code.
- `2026-03-31T01:02:00+02:00` Red phase:
  `SPECFACT_ALLOW_UNSIGNED=1 hatch run pytest tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/tools/test_ast_clean_code_runner.py tests/unit/specfact_code_review/tools/test_radon_runner.py tests/unit/specfact_code_review/tools/test_semgrep_runner.py -q`
  failed with 5 targeted regressions that matched the new spec change:
  - `test_run_review_requires_explicit_pr_mode_token_for_clean_code_reasoning`
    expected `clean-code.pr-checklist-missing-rationale` but `_checklist_findings()` returned `[]`.
  - `test_run_ast_clean_code_reports_mixed_dependency_roles_for_injected_dependencies`
    expected `solid.mixed-dependency-role` for `self.repo.save()` / `self.client.get()` but the leftmost dependency was still treated as `self`.
  - `test_run_ast_clean_code_continues_after_parse_error`
    expected a per-file `tool_error` plus later-file findings, but the parser branch returned early.
  - `test_run_radon_uses_dedicated_tool_identifier_for_kiss_findings`
    expected `tool="radon-kiss"` but the emitted finding still used `tool="radon"`.
  - `test_run_semgrep_returns_tool_error_when_results_key_is_missing`
    expected a `tool_error` for malformed Semgrep JSON, but the runner treated a missing `results` key as a clean run.
- `2026-03-31T01:04:30+02:00` Implementation:
  updated `packages/specfact-code-review/src/specfact_code_review/run/runner.py`,
  `packages/specfact-code-review/src/specfact_code_review/tools/ast_clean_code_runner.py`,
  `packages/specfact-code-review/src/specfact_code_review/tools/radon_runner.py`,
  `packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py`,
  `packages/specfact-code-review/src/specfact_code_review/resources/skills/specfact-code-review/SKILL.md`,
  `packages/specfact-code-review/src/specfact_code_review/resources/policy-packs/specfact/clean-code-principles.yaml`,
  `docs/modules/code-review.md`,
  and the targeted unit tests so the new clean-code checks, strict PR-mode gating, dependency-root detection, KISS tool labeling, and Semgrep parsing behavior matched the review comments.
- `2026-03-31T01:06:30+02:00` Green phase:
  `SPECFACT_ALLOW_UNSIGNED=1 hatch run pytest tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/tools/test_ast_clean_code_runner.py tests/unit/specfact_code_review/tools/test_radon_runner.py tests/unit/specfact_code_review/tools/test_semgrep_runner.py -q`
  passed with `50 passed in 20.26s`.
- `2026-03-31T01:08:11+02:00` Release validation:
  `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`
  passed after the module was signed again.
- `2026-03-31T01:10:42+02:00` Review validation:
  `SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --json --out .specfact/code-review.json`
  passed with `findings: []`.
