# Tasks: code-review-ai-bloat-detection

## 1. GitHub readiness and change scaffolding

- [ ] 1.1 Verify `.specfact/backlog/github_hierarchy_cache.md` is fresh, confirm the new change fits Parent Feature [#175](https://github.com/nold-ai/specfact-cli-modules/issues/175) under Modules Epic [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162), and create or sync the User Story issue with labels, project assignment, blockers, and concurrency checks recorded.
- [ ] 1.2 Add `code-review-ai-bloat-detection` to `openspec/CHANGE_ORDER.md` under "Code review and sidecar validation improvements" with its parent Feature and GitHub issue links.
- [ ] 1.3 Validate the new change artifacts with `openspec validate code-review-ai-bloat-detection --strict` before implementation begins.

## 2. Spec-first failing tests

- [ ] 2.1 Add failing semgrep-rule tests with bloated-form and simplified-form fixtures for each pattern: `ai-bloat.manual-loop-comprehension`, `ai-bloat.passthrough-lambda`, `ai-bloat.identity-try-except`, `ai-bloat.none-then-none`, `ai-bloat.single-call-wrapper`.
- [ ] 2.2 Add failing AST-runner tests with bloated-form and simplified-form fixtures for each semantic detector: `ai-bloat.unused-optional-param`, `ai-bloat.dead-branch`, `ai-bloat.loc-vs-complexity`, `ai-bloat.redundant-intermediate`.
- [ ] 2.3 Add a failing policy-pack contract test that asserts `ai-bloat-patterns.yaml` references only existing rule IDs and tags every rule with `principle: ai_bloat`.
- [ ] 2.4 Add a failing integration test that runs the full review pipeline on a seeded bloat-fixture directory and asserts `category=ai_bloat` findings appear in the resulting `.specfact/code-review.json` at `advisory` severity.
- [ ] 2.5 Run the targeted tests to capture failing-before evidence and record commands, timestamps, and failures in `openspec/changes/code-review-ai-bloat-detection/TDD_EVIDENCE.md`.

## 3. Semgrep rule pack

- [ ] 3.1 Author `packages/specfact-code-review/resources/semgrep-rules/ai-bloat.yaml` with rule definitions for the five pattern-shape detectors above.
- [ ] 3.2 Register the new rule IDs in `SEMGREP_RULE_CATEGORY` in `packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py`, mapping each to category `ai_bloat`.
- [ ] 3.3 Extend `semgrep_runner.py`'s findings emission so the `ai_bloat` category is recognised and surfaces with `severity=advisory` regardless of upstream semgrep severity.

## 4. AST runner for semantic detectors

- [ ] 4.1 Add `packages/specfact-code-review/src/specfact_code_review/tools/ai_bloat_runner.py` following the conventions of `ast_clean_code_runner.py` (beartype + icontract on public functions, `skip_if_tool_missing` not required since AST is stdlib).
- [ ] 4.2 Implement visitors for `ai-bloat.unused-optional-param`, `ai-bloat.dead-branch`, `ai-bloat.loc-vs-complexity` (consume existing radon output), and `ai-bloat.redundant-intermediate`.
- [ ] 4.3 Wire the new runner into the review orchestration alongside the other tool runners; ensure findings flow into the same `ReviewFinding` stream.

## 5. Policy pack and module manifests

- [ ] 5.1 Author `packages/specfact-code-review/resources/policy-packs/specfact/ai-bloat-patterns.yaml` with `pack_ref: specfact/ai-bloat-patterns`, `default_mode: advisory`, and entries referencing every rule above with `principle: ai_bloat`.
- [ ] 5.2 Update `packages/specfact-code-review/module-package.yaml`: bump patch version, declare the new semgrep-rule and policy-pack resources in the bundle payload.
- [ ] 5.3 Update `packages/specfact-project/module-package.yaml`: bump patch version, declare the new prompt resource.

## 6. Slash-command prompt

- [ ] 6.1 Author `packages/specfact-project/resources/prompts/specfact.08-simplify.md` mirroring the structure of `specfact.03-review.md`. The prompt MUST: read `.specfact/code-review.json`, filter by `category=ai_bloat`, group by file then rule, present each candidate with rewrite hint, drive a per-change accept/reject/skip/explain loop, apply accepted edits via the IDE, and suggest re-running review afterwards.
- [ ] 6.2 Add the new command to the prompt-command-contract registry and any slash-command discovery surfaces.

## 7. Documentation

- [ ] 7.1 Add a `code-review` docs page or section on modules.specfact.io introducing the `ai_bloat` principle category, the `advisory` severity model, and how findings surface in `.specfact/code-review.json`.
- [ ] 7.2 Cross-reference the new category from `clean-code-principles` docs so reviewers understand the distinction.
- [ ] 7.3 Document the `/specfact.08-simplify` slash command in the project bundle docs.

## 8. Passing evidence, quality gates, and review

- [ ] 8.1 Re-run all targeted tests from sections 2.1–2.4 and record passing evidence in `openspec/changes/code-review-ai-bloat-detection/TDD_EVIDENCE.md`.
- [ ] 8.2 Run the required quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, `hatch run contract-test`, the relevant `hatch run smart-test`, and the relevant `hatch run test`.
- [ ] 8.3 Run `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope full`, fix every finding on modified artifacts, rerun until the report passes, and record the command and timestamp in `TDD_EVIDENCE.md`.
- [ ] 8.4 Commit, push, and open or update the PR to `dev` after verification is green.
