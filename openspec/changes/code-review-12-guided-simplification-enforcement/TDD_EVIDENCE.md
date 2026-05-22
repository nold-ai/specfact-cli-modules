# TDD Evidence: code-review-12-guided-simplification-enforcement

## Failing Before

- `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/test_guided_simplify_resources.py -q`
  - Result: failed as expected before implementation.
  - Evidence: 18 failed, 64 passed.
  - Missing contract areas: guided finding fields, preserve validation, schema 1.2 summary, classifier guidance kinds, simplify enforce behavior, and prompt/skill walkthrough policy.

## Passing After

- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/rules/test_updater.py::test_default_skill_content_stays_within_line_budget tests/unit/specfact_code_review/rules/test_updater.py::test_load_bundled_skill_content_returns_valid_structure_when_available tests/unit/test_guided_simplify_resources.py -q`
  - Result: 116 passed.
- `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py -q`
  - Result after final cleanup: 50 passed.
- `hatch run contract-test`
  - Result: 742 passed, 2 warnings.
- `hatch run smart-test`
  - Result: 742 passed, 2 warnings.
- `hatch run type-check`
  - Result: 0 errors, 0 warnings, 0 notes.
- `hatch run lint`
  - Result: 10.00/10.
- `hatch run yaml-lint`
  - Result: validated 6 manifests and `registry/index.json`.
- `hatch run check-bundle-imports`
  - Result: import boundary check passed.
- `hatch run validate-prompt-commands`
  - Result: prompt command validation passed with no findings.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev`
  - Result: verified 6 module manifests.
- `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed`
  - Result: PASS, CI exit 0, score 115, 0 findings.
- `openspec validate code-review-12-guided-simplification-enforcement --strict`
  - Result: valid.

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

`hatch run sign-modules --changed-only --payload-from-filesystem --bump-version patch --base-ref origin/dev` failed locally because no private signing key was available. I reran with `--allow-unsigned`, which bumped affected module versions and refreshed filesystem checksums. Cryptographic signature restoration remains an approval-time signing step.
