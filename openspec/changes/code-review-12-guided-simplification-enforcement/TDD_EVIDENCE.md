# TDD Evidence: code-review-12-guided-simplification-enforcement

## Failing Before

- `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/test_guided_simplify_resources.py -q`
  - Result: failed as expected before implementation.
  - Evidence: 18 failed, 64 passed.
  - Missing contract areas: guided finding fields, preserve validation, schema 1.2 summary, classifier guidance kinds, simplify enforce behavior, and prompt/skill walkthrough policy.
- `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/rules/test_updater.py tests/unit/test_guided_simplify_resources.py -q`
  - Result: failed as expected before PR review fixes.
  - Evidence: 6 failed, 87 passed.
  - Missing contract areas: orphan guided-field validation, failed safe-mechanical blocking counts, missing deterministic safe-mechanical fixers, bottom-up rewrite ordering, and headless action-table defaults.
- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_dead_branch_with_else tests/unit/specfact_code_review/run/test_findings.py::test_review_finding_rejects_guided_evidence_fields_without_guidance_kind -q`
  - Result: failed as expected before follow-up PR review fixes.
  - Evidence: 4 failed.
  - Missing contract areas: dead-branch fixer skipped no-else guard and guided evidence fields required `guidance_kind`.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_after_else_path tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_impure_duplicate_guard tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_impure_duplicate_guard tests/unit/specfact_code_review/run/test_findings.py::test_review_finding_accepts_guided_metadata_without_action_status tests/unit/specfact_code_review/run/test_findings.py::test_review_report_counts_missing_status_safe_mechanical_findings_as_blocking tests/unit/specfact_code_review/tools/test_semgrep_runner.py::test_ai_bloat_guidance_matches_ai_bloat_rule_categories -q`
  - Result: failed as expected before final PR review fixes.
  - Evidence: 5 failed, 1 passed.
  - Missing contract areas: duplicate guard safety after else branches, impure predicate safety, optional guided `action_status`, unresolved safe-mechanical counting without status, and Semgrep guidance parity coverage.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_nonterminal_duplicate_guard tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_with_else -q`
  - Result: failed as expected before final detector tightening.
  - Evidence: 2 failed.
  - Missing contract areas: safe-mechanical dead-branch detection required the current duplicate guard to be terminal and have no `else`.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_after_assignment tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_dead_branch_after_assignment tests/unit/specfact_code_review/run/test_commands.py::test_run_review_once_applies_simplification_fixes_before_rerun -q`
  - Result: failed as expected before PR 289 dev-branch review fixes.
  - Evidence: 3 failed.
  - Missing contract areas: duplicate guard state invalidation, dead-branch autofix state invalidation, and applied simplification evidence in the post-fix report.

## Passing After

- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/rules/test_updater.py::test_default_skill_content_stays_within_line_budget tests/unit/specfact_code_review/rules/test_updater.py::test_load_bundled_skill_content_returns_valid_structure_when_available tests/unit/test_guided_simplify_resources.py -q`
  - Result: 116 passed.
- `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/rules/test_updater.py tests/unit/test_guided_simplify_resources.py -q`
  - Result after PR review fixes: 93 passed.
- `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/rules/test_updater.py tests/unit/test_guided_simplify_resources.py -q`
  - Result after strict metadata fallout fix: 125 passed.
- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py -q`
  - Result after final cleanup: 50 passed.
- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_findings.py -q`
  - Result after follow-up PR review fixes: 77 passed.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_flags_duplicate_prior_return_guard tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_after_else_path tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_impure_duplicate_guard tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_removes_dead_branch tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_dead_branch_with_else tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_impure_duplicate_guard tests/unit/specfact_code_review/run/test_findings.py::test_review_finding_accepts_guided_metadata_without_action_status tests/unit/specfact_code_review/run/test_findings.py::test_review_report_counts_missing_status_safe_mechanical_findings_as_blocking tests/unit/specfact_code_review/tools/test_semgrep_runner.py::test_ai_bloat_guidance_matches_ai_bloat_rule_categories -q`
  - Result after final PR review fixes: 9 passed.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/tools/test_semgrep_runner.py -q`
  - Result after final PR review fixes: 172 passed.
- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_removes_dead_branch tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_dead_branch_with_else tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_impure_duplicate_guard -q`
  - Result after complexity cleanup: 3 passed.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_flags_duplicate_prior_return_guard tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_after_else_path tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_nonterminal_duplicate_guard tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_with_else tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_impure_duplicate_guard -q`
  - Result after final detector tightening: 5 passed.
- `hatch run pytest tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py::test_dead_branch_ignores_duplicate_guard_after_assignment tests/unit/specfact_code_review/run/test_commands.py::test_apply_simplification_fixes_keeps_dead_branch_after_assignment tests/unit/specfact_code_review/run/test_commands.py::test_run_review_once_applies_simplification_fixes_before_rerun -q`
  - Result after PR 289 dev-branch review fixes: 3 passed.
- `hatch run pytest tests/unit/test_guided_simplify_resources.py -q`
  - Result after prompt/skill user-experience tightening: 2 passed.
- `hatch run validate-prompt-commands`
  - Result after prompt/skill user-experience tightening: prompt command validation passed with no findings.
- `hatch run pytest tests/unit/specfact_code_review/review/test_commands.py::test_review_run_help_lists_simplify_focus tests/unit/specfact_code_review/review/test_commands.py::test_review_run_instructions_prints_ai_workflow_without_running_review tests/unit/docs/test_code_review_docs_parity.py::test_code_review_run_doc_mentions_public_ty_options tests/unit/test_guided_simplify_resources.py tests/unit/specfact_code_review/rules/test_updater.py::test_load_bundled_skill_content_returns_valid_structure_when_available -q`
  - Result after adding the AI instructions fallback and docs: 6 passed.
- `hatch run specfact code review run --instructions`
  - Result after adding the AI instructions fallback: printed the guided simplify / clean-code workflow and exited successfully without running review analysis.
- Subagent simulation with only `specfact code review run --instructions` guidance
  - Result: the assistant followed the conservative decision-card workflow, treated missing `guidance_kind` findings as unguided advisories, and identified the clean-PR branch fallback as actionable after adding a base-ref diff example.
- `hatch run contract-test`
  - Result after PR review fixes: 758 passed, 2 warnings.
- `hatch run smart-test`
  - Result: 742 passed, 2 warnings.
- `hatch run type-check`
  - Result: 0 errors, 0 warnings, 0 notes.
- `hatch run lint`
  - Result after AI instructions fallback: 10.00/10.
- `hatch run yaml-lint`
  - Result after AI instructions fallback: validated 6 manifests and `registry/index.json`.
- `hatch run check-bundle-imports`
  - Result: import boundary check passed.
- `hatch run validate-prompt-commands`
  - Result: prompt command validation passed with no findings.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev`
  - Result after AI instructions fallback: verified 6 module manifests.
- `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed`
  - Result after final PR review fixes: PASS, CI exit 0, score 120, 0 findings.
- `hatch run specfact code review run --bug-hunt --include-tests --json --out .specfact/code-review.json --scope changed`
  - Result after AI instructions fallback: PASS, CI exit 0, 0 findings.
- `openspec validate code-review-12-guided-simplification-enforcement --strict`
  - Result after AI instructions fallback: valid.

## Local Dev-Link Validation

- Linked live modules with:
  - `hatch run link-dev-module specfact-code-review --force`
  - `hatch run link-dev-module specfact-project --force`
- Verified runtime precedence through CLI output: project-scope `.specfact/modules/specfact-code-review` and `.specfact/modules/specfact-project` shadow user-scope copies.
- Current changed-scope mode checks:
  - Default: PASS, schema `1.0`, score 115, 0 findings.
  - Bug-hunt: PASS, schema `1.0`, score 115, 0 findings.
  - Simplify shadow: PASS, schema `1.0`, score 115, 0 findings.
  - Simplify enforce: PASS, schema `1.0`, score 115, 0 findings.
- Guided fixture checks:
  - Simplify shadow on fixture: PASS, schema `1.2`, 3 findings, summary counts `safe_mechanical=1`, `needs_tests=1`, `preserve=1`.
  - Simplify enforce on same fixture: FAIL, schema `1.2`, `ci_exit_code=1`, blocked only by the unresolved safe-mechanical recommendation.
  - Simplify enforce with `--fix` on safe-mechanical fixture: rewrote `return sum(values)`, then PASS. Remaining Semgrep wrapper finding now carries `design_judgment` guidance and schema `1.2`.
- Prompt/skill dry run with subagent:
  - Confirmed walkthrough levels, `guidance_kind` policy, no batch edits, and action status requirements.
  - Found and fixed gaps: missing-report explanation, headless batching language, and concrete action-log shape.
- Final dev-link bug-hunt with extended targeted-test timeout:
  - `SPECFACT_ALLOW_UNSIGNED=1 SPECFACT_CODE_REVIEW_TARGETED_TEST_TIMEOUT=300 hatch run specfact code review run --bug-hunt --json --out .specfact/tmp-local-dev-link-review/changed-bughunt-clean-final.json --scope changed`
  - Result: PASS, CI exit 0, score 115, 0 findings.

## Signing Note

`hatch run verify-modules-signature --payload-from-filesystem --require-signature --enforce-version-bump --version-check-base origin/main` passed before the final source edits, verifying the existing `0.47.23` signature was a real cryptographic signature. The final local payload is refreshed at `0.47.25` for `specfact-code-review` and `0.41.16` for `specfact-project` with `hatch run sign-modules --changed-only --base-ref origin/dev --bump-version patch --allow-unsigned --payload-from-filesystem`, because no private signing key is available in the local worktree. Cryptographic signature restoration remains an approval-time or post-merge signing step.
