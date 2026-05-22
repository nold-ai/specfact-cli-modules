## 1. GitHub readiness and OpenSpec setup

- [x] 1.1 Create OpenSpec change `code-review-12-guided-simplification-enforcement`.
- [x] 1.2 Create GitHub issue [#286](https://github.com/nold-ai/specfact-cli-modules/issues/286), link it under Feature [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275), and label it with `enhancement`, `codebase`, `openspec`, and `change-proposal`.
- [x] 1.3 Confirm issue project assignment, open/Todo state, parent linkage, and source tracking.
- [x] 1.4 Add `openspec/CHANGE_ORDER.md` row as order 05, blocked by [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276).
- [x] 1.5 Validate the OpenSpec change with `openspec validate code-review-12-guided-simplification-enforcement --strict`.

## 2. Spec-first failing tests

- [x] 2.1 Add model tests for guidance fields, legacy compatibility, preserve reason validation, and simplification summary serialization.
- [x] 2.2 Add classifier tests for `safe_mechanical`, `needs_tests`, `design_judgment`, and `preserve` cases.
- [x] 2.3 Add CLI tests proving `--focus simplify --mode enforce` fails only on unresolved safe-mechanical findings.
- [x] 2.4 Add CLI tests proving `--focus simplify --fix` applies only deterministic safe-mechanical rewrites and records action status/evidence.
- [x] 2.5 Add prompt contract tests for walkthrough-level selection, adaptive guidance, headless defaults, and confirmation rules.
- [x] 2.6 Add skill tests or resource checks proving the packaged and repo-local skill carry the same simplify policy.
- [x] 2.7 Record failing-before evidence in `TDD_EVIDENCE.md`.

## 3. Review model and guidance metadata

- [x] 3.1 Extend `ReviewFinding` with optional guided simplification fields.
- [x] 3.2 Add `ReviewReport.simplification_summary` with counts by guidance kind and action status.
- [x] 3.3 Ensure legacy reports still validate and existing scoring/blocking behavior remains unchanged outside simplify enforcement.
- [x] 3.4 Add helper predicates for safe-mechanical and auto-fix eligibility.

## 4. Simplification classifier and preserve policy

- [x] 4.1 Classify existing simplification rules into guidance kinds with deterministic rationale and safety checks.
- [x] 4.2 Reclassify abstract params and meaningful wrappers as `preserve` or `design_judgment`, with contract-preservation guidance documented for prompt/skill users.
- [x] 4.3 Keep long low-complexity and duplicate-shape signals out of automatic cleanup unless stronger metadata proves safe.
- [x] 4.4 Ensure terminal and JSON output make recommended action and preserve reason obvious.

## 5. Enforce/fix workflow

- [x] 5.1 Make `--focus simplify --mode enforce` fail only when unresolved safe-mechanical findings remain.
- [x] 5.2 Implement conservative safe-mechanical auto-fix support for deterministic rewrites only.
- [x] 5.3 Re-run review after auto-fix and record applied/failed/still-recommended outcomes.
- [x] 5.4 Preserve non-autofix behavior for `needs_tests`, `design_judgment`, and `preserve`.

## 6. Prompt and skill interaction flow

- [x] 6.1 Update `/specfact.08-simplify` to ask for or infer walkthrough level: vibe coder, junior developer, senior/pro, or headless agent.
- [x] 6.2 Adapt explanation depth, grouping, confirmation, and headless behavior by walkthrough level.
- [x] 6.3 Update `specfact-code-review` skill copies and packaged skill resource with the same decision policy.
- [x] 6.4 Update docs for guided simplify findings, preserve classifications, enforce/fix behavior, and evidence summaries.

## 7. Packaging, signatures, and verification

- [x] 7.1 Bump affected module versions when packaged resources change.
- [x] 7.2 Refresh affected module manifest integrity checksums; cryptographic signing key was unavailable locally, so approval-time signing remains required.
- [x] 7.3 Re-run targeted tests and record passing evidence in `TDD_EVIDENCE.md`.
- [x] 7.4 Run required gates for touched scope: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, `hatch run contract-test`, relevant `hatch run smart-test`, relevant `hatch run test`, and `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed`.
