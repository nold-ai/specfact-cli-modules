## Failing Before

- Timestamp: 2026-05-21T22:48:51+02:00
- Command: `hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/tools/test_ast_clean_code_runner.py tests/unit/test_check_prompt_commands_script.py -q`
- Result: failed as expected before production implementation.
- Summary: 13 failed, 99 passed.
- Failed coverage:
  - `ReviewFinding` lacks optional simplification metadata fields.
  - `ReviewReport` remains at schema version `1.0` when metadata-bearing findings are present.
  - `run_review(..., focus="simplify")` is unsupported.
  - CLI `--focus simplify` is rejected before scope resolution reaches the runner.
  - Expanded AI-bloat simplification patterns are not detected.
  - Duplicate-intent findings lack `intent_key` and `related_locations`.
  - `/specfact.08-simplify` does not group by simplification metadata.

## Passing After

- Timestamp: 2026-05-21T23:31:55+02:00
- Targeted tests:
  - `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/tools/test_ai_bloat_runner.py tests/unit/specfact_code_review/run/test_findings.py tests/unit/docs/test_code_review_docs_parity.py -q`
  - Result: 93 passed.
- Prompt and skill/resource contract tests:
  - `hatch run pytest tests/unit/specfact_code_review/rules/test_updater.py tests/unit/test_bundle_resource_payloads.py tests/unit/docs/test_code_review_docs_parity.py tests/unit/test_check_prompt_commands_script.py -q`
  - Result: 53 passed, 2 warnings.
  - `hatch run validate-prompt-commands`
  - Result: passed.
- OpenSpec and static gates:
  - `openspec validate code-review-11-simplification-feedback-loop --strict`
  - Result: valid.
  - `hatch run format`
  - Result: passed.
  - `hatch run type-check`
  - Result: 0 errors, 0 warnings, 0 notes.
  - `hatch run lint`
  - Result: passed; pylint rated 10.00/10.
  - `hatch run yaml-lint`
  - Result: validated 6 manifests and `registry/index.json`.
  - `hatch run check-bundle-imports`
  - Result: import boundary check passed.
  - `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`
  - Result: verified 6 module manifests.
- Full test gates:
  - `hatch run contract-test`
  - Result: 709 passed, 2 warnings.
  - `hatch run smart-test`
  - Result: 709 passed, 2 warnings.
  - `hatch run test`
  - Result: 709 passed, 2 warnings.
- SpecFact review:
  - `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed`
  - Result: exit code 0; report summary `Review completed with 6 findings (0 blocking).`
  - Remaining advisory items:
    - `ai-bloat.loc-vs-complexity` info on Typer `run` wrapper and `run_review`; no blocking score impact.
    - Pylint style warnings for Typer command signature/local variables and a dataclass request carrier; these are framework/data-carrier shape findings and are non-blocking in the generated report.
    - Targeted review coverage warning for `run/commands.py`; full `contract-test`, `smart-test`, and `test` gates passed.
- Real-world Codex skill smoke:
  - Initial smoke without a local module root installed stale v1 skill content because the CLI resolved the existing user-scoped module at `~/.specfact/modules/specfact-code-review` first.
  - Command under test with local module source:
    `SPECFACT_MODULES_ROOTS=/home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/code-review-11-simplification-feedback-loop/packages SPECFACT_ALLOW_UNSIGNED=1 python -m specfact_cli.cli code review rules init --ide codex`
  - Result: created `skills/specfact-code-review/SKILL.md` and installed `.codex/skills/specfact-code-review/SKILL.md` in `/tmp/specfact-skill-smoke-roots`.
  - Content verification: installed skill contains `Updated: 2026-05-21`, `Codex CLI`, `specfact code review run --scope changed --focus simplify --json --out .specfact/code-review.json`, and `Don't copy prompt templates`.
  - Codex detection verification:
    `codex -C /tmp/specfact-skill-smoke-roots debug prompt-input "Use specfact-code-review"`
  - Result: prompt input listed `specfact-code-review: CLI-grounded SpecFact code review workflow and house rules for AI coding sessions` from `/tmp/specfact-skill-smoke-roots/.codex/skills/specfact-code-review/SKILL.md`.
