# Tasks: Scope Truth and Differential Enforcement

Every implementation task targets at most two hours. Tests precede code. This planning branch must remain OpenSpec-only.

## 0. Planning

- [x] 0.1 Define explicit scope sources, truthful statuses, differential analysis, and non-goals.
- [x] 0.2 Define a one-release compatibility path for `--scope changed`.
- [x] 0.3 Create no package, test, registry, version, signature, prompt, or generated-doc changes.

## 1. Failing scope tests

- [ ] 1.1 Add `test_range_scope_includes_committed_files_on_clean_checkout`.
- [ ] 1.2 Add `test_range_scope_uses_merge_base_not_head_worktree`.
- [ ] 1.3 Add `test_scope_git_failure_is_unknown_and_blocks_enforcement`.
- [ ] 1.4 Add `test_empty_resolved_range_is_not_applicable`.
- [ ] 1.5 Add `test_range_scope_includes_changed_tests_by_default`.
- [ ] 1.6 Add CLI-contract red cases for full refs, invalid combinations, deprecated changed alias, and explicit positional files.

## 2. Failing differential/report tests

- [ ] 2.1 Add `test_introduced_blocker_off_added_line_still_blocks`.
- [ ] 2.2 Add `test_unchanged_baseline_blocker_is_retained_but_not_introduced`.
- [ ] 2.3 Add `test_baseline_analysis_failure_is_unknown`.
- [ ] 2.4 Add `test_report_exposes_mandatory_analyzer_coverage`.
- [ ] 2.5 Add `test_fixable_error_remains_blocking_until_applied`.
- [ ] 2.6 Add `test_report_never_says_all_passed_with_mandatory_unknown`.
- [ ] 2.7 Record failing commands and outcomes in `TDD_EVIDENCE.md` before source edits.

## 3. Minimal implementation

- [ ] 3.1 Implement the explicit worktree/index/range/full resolver and immutable scope evidence.
- [ ] 3.2 Add unknown/not-applicable handling before analyzer execution.
- [ ] 3.3 Implement isolated symmetric base/head analyzer execution with pinned identities.
- [ ] 3.4 Add stable fingerprints and introduced/fixed/unchanged/unknown classification.
- [ ] 3.5 Add mandatory analyzer coverage evidence.
- [ ] 3.6 Separate finding status, differential state, autofix availability, and blocking policy.
- [ ] 3.7 Update CLI/docs/fixtures and retain `changed` only as a deprecated worktree alias.

## 4. Release and adoption

- [ ] 4.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and explicit-range self-review.
- [ ] 4.2 Benchmark #665–#671 and seeded false-green/false-introduction cases.
- [ ] 4.3 Update bundle version, manifest integrity, registry, signatures, compatibility, and public docs.
- [ ] 4.4 Publish a signed release; migrate core CI in shadow, warning, then enforce mode.

## Prohibited shortcuts

- Do not treat Git errors as an empty file/line set.
- Do not determine introduction solely from changed-line intersection.
- Do not exclude changed tests silently.
- Do not make `autofix_available` mean resolved/non-blocking.
- Do not add detector rules or AI review to this change.

## Closed implementation allowlist

CLI/request parsing:

- `packages/specfact-code-review/src/specfact_code_review/review/commands.py`.
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` only for request translation/validation and consumption of `ScopeResolution`.
- `tests/unit/specfact_code_review/run/test_commands.py` and `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`.

Scope:

- New exactly `packages/specfact-code-review/src/specfact_code_review/run/scope.py`.
- New exactly `tests/unit/specfact_code_review/run/test_scope.py`.
- `scope.py` is the only component allowed to invoke Git for scope discovery; replace/delegate the old scope helpers in `run/commands.py`.

Differential enforcement:

- New exactly `packages/specfact-code-review/src/specfact_code_review/run/differential.py`.
- New exactly `tests/unit/specfact_code_review/run/test_differential.py`.
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py` collects analyzer facts and consumes classification; `differential.py` classifies already-produced base/head findings and contains no analyzer or Requirements logic.

Report truth:

- `packages/specfact-code-review/src/specfact_code_review/run/findings.py` remains the only report/finding model; do not create a parallel model. `fixable` must not affect `is_blocking()`.
- `tests/unit/specfact_code_review/run/test_findings.py` and `tests/unit/specfact_code_review/run/test_runner.py`.

End-to-end/docs/release:

- `tests/e2e/specfact_code_review/test_review_run_e2e.py`, the CLI-contract YAML, and `docs/bundles/code-review/run.md`.
- `packages/specfact-code-review/module-package.yaml` and generated docs/registry/signatures only after tests pass; use existing generators and never hand-edit archives.

Explicitly forbidden:

- `packages/specfact-code-review/src/specfact_code_review/run/cleanup_evidence.py`, `packages/specfact-code-review/src/specfact_code_review/run/forecast.py`, `packages/specfact-code-review/src/specfact_code_review/run/scorer.py`, and analyzer implementations under `specfact_code_review/tools/`;
- the Requirements package and archived OpenSpec changes;
- any new source/test file other than the four exact `scope.py`/`differential.py` files above.
