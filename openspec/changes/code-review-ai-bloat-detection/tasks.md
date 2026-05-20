# Tasks: code-review-ai-bloat-detection

## 1. GitHub readiness and change scaffolding

 - [x] 1.1 Verify `.specfact/backlog/github_hierarchy_cache.md` is fresh, confirm issue [#269](https://github.com/nold-ai/specfact-cli-modules/issues/269) is ready, and record the hierarchy mismatch that Parent Feature [#175](https://github.com/nold-ai/specfact-cli-modules/issues/175) is closed/Done while this change broadens that feature. Do not implement if new blockers or an `in progress` concurrency conflict appears.
 - [x] 1.2 Add `code-review-ai-bloat-detection` to `openspec/CHANGE_ORDER.md` under "Code review and sidecar validation improvements" with its parent Feature and GitHub issue links.
 - [x] 1.3 Validate the new change artifacts with `openspec validate code-review-ai-bloat-detection --strict` before implementation begins.

## 2. Spec-first failing tests

 - [x] 2.1 Add failing semgrep-rule tests with bloated-form and simplified-form fixtures for each pattern: `ai-bloat.manual-loop-comprehension`, `ai-bloat.passthrough-lambda`, `ai-bloat.identity-try-except`, `ai-bloat.none-then-none`, `ai-bloat.single-call-wrapper`.
 - [x] 2.2 Add failing AST-runner tests with bloated-form and simplified-form fixtures for each semantic detector: `ai-bloat.unused-optional-param`, `ai-bloat.dead-branch`, `ai-bloat.loc-vs-complexity`, `ai-bloat.redundant-intermediate`.
 - [x] 2.3 Add a failing policy-pack contract test that asserts `ai-bloat-patterns.yaml` references only existing rule IDs and tags every rule with `principle: ai_bloat`.
 - [x] 2.4 Add a failing integration test that runs the full review pipeline on a seeded bloat-fixture directory and asserts `category=ai_bloat` findings appear in the resulting `.specfact/code-review.json` at `severity=info` (non-blocking) and never at `warning` or `error`.
 - [x] 2.5 Add a failing scorer/model test proving `ai_bloat` is accepted by the strict `ReviewFinding.category` schema and is score-neutral.
 - [x] 2.6 Run the targeted tests to capture failing-before evidence and record commands, timestamps, and failures in `openspec/changes/code-review-ai-bloat-detection/TDD_EVIDENCE.md`.

## 3. Semgrep rule pack

 - [x] 3.1 Author `packages/specfact-code-review/resources/semgrep-rules/ai-bloat.yaml` with rule definitions for the five pattern-shape detectors above.
 - [x] 3.2 Register the new rule IDs in `SEMGREP_RULE_CATEGORY` in `packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py`, mapping each to category `ai_bloat`.
 - [x] 3.3 Extend `semgrep_runner.py`'s findings emission so the `ai_bloat` category is recognised and surfaces with `severity=info` (the existing non-blocking severity on `ReviewFinding`) regardless of upstream semgrep severity. The "advisory" framing is provided by the policy pack's `default_mode: advisory`, not by the finding's `severity` value.

## 4. AST runner for semantic detectors

 - [x] 4.1 Add `packages/specfact-code-review/src/specfact_code_review/tools/ai_bloat_runner.py` following the conventions of `ast_clean_code_runner.py` (beartype + icontract on public functions, `skip_if_tool_missing` not required since AST is stdlib).
 - [x] 4.2 Implement conservative local visitors for `ai-bloat.unused-optional-param`, `ai-bloat.dead-branch`, `ai-bloat.loc-vs-complexity` (LOC >= 40 and local branch/call complexity <= 4), and `ai-bloat.redundant-intermediate`.
 - [x] 4.3 Wire the new runner into the review orchestration alongside the other tool runners; ensure findings flow into the same `ReviewFinding` stream.

## 5. Policy pack and module manifests

 - [x] 5.1 Author `packages/specfact-code-review/resources/policy-packs/specfact/ai-bloat-patterns.yaml` with `pack_ref: specfact/ai-bloat-patterns`, `default_mode: advisory`, and entries referencing every rule above with `principle: ai_bloat`.
 - [x] 5.2 Update `packages/specfact-code-review/module-package.yaml`: bump patch version and ensure resource payload/signature tests cover the new semgrep-rule and policy-pack files.
 - [x] 5.3 Update `packages/specfact-project/module-package.yaml`: bump patch version and ensure prompt discovery/resource payload tests cover the new prompt resource.

## 5b. Pre-commit hook surfaces ai_bloat advisories

 - [x] 5b.1 Update `scripts/pre_commit_code_review.py` so the `--level error` block-threshold filter does not strip `ai_bloat` findings from `.specfact/code-review.json`. Either narrow `--level` to apply to block/exit semantics only (not to JSON-out filtering), or invoke the review with a wider emit-level and apply the error-block decision after the JSON is written. The hook MUST exit zero when only `ai_bloat`/`info` findings are present and MUST print a stderr summary of any `ai_bloat` findings detected.
 - [x] 5b.2 Add a failing-then-passing test for the hook covering: (a) only `ai_bloat`/`info` findings → exit 0, JSON contains them, stderr summary printed; (b) at least one `error` finding → exit non-zero, JSON contains both `ai_bloat` and `error` findings.
 - [x] 5b.3 Update review scoring so `ai_bloat` findings are score-neutral while other `info` findings retain existing behavior.

## 6. Slash-command prompt

 - [x] 6.1 Author `packages/specfact-project/resources/prompts/specfact.08-simplify.md` mirroring the structure of `specfact.03-review.md`. The prompt MUST: read `.specfact/code-review.json`, filter by `category=ai_bloat`, group by file then rule, present each candidate with rewrite hint, drive a per-change accept/reject/skip/explain loop, apply accepted edits via the IDE, and suggest re-running review afterwards.
 - [x] 6.2 Add the new command to the prompt-command-contract registry and any slash-command discovery surfaces.

## 7. Reference documentation

 - [x] 7.1 Add a `code-review` docs page or section on modules.specfact.io introducing the `ai_bloat` principle category, the `advisory` severity model, and how findings surface in `.specfact/code-review.json`.
 - [x] 7.2 Cross-reference the new category from `clean-code-principles` docs so reviewers understand the distinction.
 - [x] 7.3 Document the `/specfact.08-simplify` slash command in the project bundle docs.

## 8. Headline docs and showcase

Goal: position the `ai_bloat` capability as a flagship entry point to SpecFact's review surface, framed honestly as "bloat detection tuned for the shapes AI code commonly produces" rather than as an `is-this-AI` classifier. All marketing copy MUST use this framing and MUST NOT claim the detectors identify AI authorship.

 - [x] 8.1 Update the modules repo root `README.md` with a top-level feature callout introducing AI-shaped bloat detection alongside the existing review capability, including a one-paragraph rationale (AI-generated code amplifies a recognisable bloat pattern surface that conventional clean-code gates do not name as a category) and a link to the quickstart walkthrough.
 - [x] 8.2 Add a quickstart walkthrough page under `docs/` (e.g., `docs/quickstart-ai-bloat.md` or the equivalent permalink slot per `docs/reference/documentation-url-contract.md`) that demonstrates the end-to-end flow: install bundle → run `specfact code review run` on a seeded fixture → inspect `ai_bloat` findings in `.specfact/code-review.json` → invoke `/specfact.08-simplify` in the IDE → accept / reject rewrites → re-run review to show findings cleared. Include before/after code snippets for at least two detectors (e.g., manual-loop comprehension and identity try/except).
 - [x] 8.3 Add a homepage callout on modules.specfact.io introducing the capability with the honest framing above and linking to 8.2. Coordinate copy with any existing top-of-fold content; do not displace currently-promoted capabilities without explicit approval.
 - [x] 8.4 Capture real before/after evidence from running the detectors on this repo (`specfact-cli-modules`) or a sibling repo (`specfact-cli`), then embed the numbers (e.g., findings count, LOC delta on accepted rewrites) into 8.1 and 8.2 so the showcase is grounded in measured outcomes rather than claims. Record the source repo, commit SHA, and command invocations in `TDD_EVIDENCE.md`.
 - [x] 8.5 Open a follow-up tracking issue in `nold-ai/specfact-cli` (core CLI repo) for a parallel README/docs callout there, linked to this change and to issue [#269](https://github.com/nold-ai/specfact-cli-modules/issues/269). The core-side update is out of scope for this PR but in scope for the rollout; record the follow-up issue URL in `TDD_EVIDENCE.md`.

## 9. Passing evidence, quality gates, and review

 - [x] 9.1 Re-run all targeted tests from sections 2.1–2.4 and record passing evidence in `openspec/changes/code-review-ai-bloat-detection/TDD_EVIDENCE.md`.
- [x] 9.2 Run the required quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, `hatch run contract-test`, the relevant `hatch run smart-test`, and the relevant `hatch run test`.
- [x] 9.3 Run `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope full`, fix every finding on modified artifacts, rerun, and record the command/timestamp plus the documented full-repository legacy exception in `TDD_EVIDENCE.md`.
- [x] 9.4 Commit, push, and open or update the PR to `dev` after verification is green.
