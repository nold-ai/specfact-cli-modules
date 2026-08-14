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
- [ ] 1.7 Add `test_pr_assurance_rejects_positional_file_downgrade` while retaining local explicit-file enforcement.
- [ ] 1.8 Add `test_range_analysis_uses_materialized_commit_snapshots` with caller-worktree mutation and pre/post manifest mismatch cases.
- [ ] 1.9 Add `test_range_rejects_fix_preview_and_mutation_options`.

## 2. Failing differential/report tests

- [ ] 2.1 Add `test_introduced_blocker_off_added_line_still_blocks`.
- [ ] 2.2 Add `test_unchanged_baseline_blocker_is_retained_but_not_introduced`.
- [ ] 2.3 Add `test_baseline_analysis_failure_is_unknown`.
- [ ] 2.4 Add `test_report_exposes_mandatory_analyzer_coverage`.
- [ ] 2.5 Add `test_fixable_error_remains_blocking_until_applied`.
- [ ] 2.6 Add `test_report_never_says_all_passed_with_mandatory_unknown`.
- [ ] 2.7 Add table-driven `test_schema_1_6_assurance_status_legacy_projection_and_exit_matrix` for PASS/FAIL/UNKNOWN/NOT_APPLICABLE under strict and shadow modes.
- [ ] 2.8 Add `test_schema_1_6_missing_assurance_status_is_unknown` and legacy-reader cases proving old PASS/FAIL cannot imply UNKNOWN/NOT_APPLICABLE.
- [ ] 2.9 Collect the exact canonical pytest node ID for every test-authored CR14 scenario, write each selector into `requirements-evidence.yaml`, and rerun strict mapping validation. Do not edit production source in this task.
- [ ] 2.10 Build the deterministic plan from the accepted mapping and source identity, then record and freeze the mapping digest, plan identity/digest, source revision/tree, analyzer policy/config identities, and selector set. Any later change to a frozen input repeats tasks 2.9–2.10.
- [ ] 2.11 Execute the frozen exact selectors, confirm the expected failing outcomes, and record the exact commands and outcomes in `TDD_EVIDENCE.md` before any source edit. Section 3 is blocked until tasks 2.9–2.11 are complete.

## 3. Minimal implementation

- [ ] 3.1 Implement the explicit worktree/index/range/full resolver and immutable scope evidence.
- [ ] 3.2 In `scope.py`, materialize detached base/head commit trees, produce and pre/post verify selected-input manifests, and clean temporary roots; no other component may invoke Git.
- [ ] 3.3 Reject positional-file downgrade for PR-range policy and reject fix/preview/mutation options in range mode.
- [ ] 3.4 Add unknown/not-applicable handling before analyzer execution.
- [ ] 3.5 Implement isolated symmetric base/head analyzer execution with pinned toolchain and trusted base-policy/config identities.
- [ ] 3.6 Add stable fingerprints and introduced/fixed/unchanged/unknown classification.
- [ ] 3.7 Add mandatory analyzer coverage evidence.
- [ ] 3.8 Separate finding status, differential state, autofix availability, and blocking policy.
- [ ] 3.9 Add schema 1.6 `assurance_status`, versioned legacy reading, closed dual-write projection, and strict/shadow exit matrix.
- [ ] 3.10 Update CLI/docs/fixtures and retain `changed` only as a deprecated worktree alias.

## 4. Release and adoption

- [ ] 4.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and explicit-range self-review.
- [ ] 4.2 Benchmark #665–#671 and seeded false-green, mutable-worktree, positional-downgrade, and false-introduction cases.
- [ ] 4.3 After behavior passes, update public docs, command references, bundle version, changelog, and `module-package.yaml` with `core_compatibility: '>=0.56.0,<1.0.0'`. Do not generate or hand-edit registry archives, checksums, signatures, sidecars, or `registry/index.json` on the feature branch.
- [ ] 4.4 Re-run the complete feature-branch gates and merge the reviewed implementation PR to `dev` only when schema 1.6 consumer compatibility is proven.
- [ ] 4.5 Observe the canonical `.github/workflows/publish-modules.yml` run and review its `auto/publish-dev-<run-id>` PR.
- [ ] 4.6 Require the generated signed manifest/archive/checksum/sidecar/index, filesystem signature/version-bump verification, and full quality matrix before merging the auto-publish PR.
- [ ] 4.7 Give core the final merged commit/tree, module version, schema 1.6 contract, archive/checksum/signature, signer, workflow, and auto-publish PR identities. Core PR CI migrates in shadow, warning, then enforce mode and requires `assurance_kind=pr_range`.
- [ ] 4.8 After implementation and signed handoff merge, run exactly `openspec archive code-review-14-scope-truth-and-differential-enforcement` from the repository root; never move the change manually.

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
- `scope.py` is the only component allowed to invoke Git for scope discovery and detached snapshot materialization; replace/delegate the old scope helpers in `run/commands.py`.

Differential enforcement:

- New exactly `packages/specfact-code-review/src/specfact_code_review/run/differential.py`.
- New exactly `tests/unit/specfact_code_review/run/test_differential.py`.
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py` collects analyzer facts and consumes classification; `differential.py` classifies already-produced base/head findings and contains no analyzer or Requirements logic.

Report truth:

- `packages/specfact-code-review/src/specfact_code_review/run/findings.py` remains the only report/finding model; do not create a parallel model. `fixable` must not affect `is_blocking()`.
- `tests/unit/specfact_code_review/run/test_findings.py` and `tests/unit/specfact_code_review/run/test_runner.py`.

End-to-end/docs/release:

- `tests/e2e/specfact_code_review/test_review_run_e2e.py`, the CLI-contract YAML, and `docs/bundles/code-review/run.md`.
- `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/requirements-evidence.yaml` only in task 2.9 to add exact collected selectors and freeze their mapping identity.
- `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/TDD_EVIDENCE.md` for task 2.11 failing evidence and later verified green evidence.
- `packages/specfact-code-review/module-package.yaml` and generated docs/registry/signatures only after tests pass; use existing generators and never hand-edit archives.

Explicitly forbidden:

- `packages/specfact-code-review/src/specfact_code_review/run/cleanup_evidence.py`, `packages/specfact-code-review/src/specfact_code_review/run/forecast.py`, `packages/specfact-code-review/src/specfact_code_review/run/scorer.py`, and analyzer implementations under `specfact_code_review/tools/`;
- the Requirements package and archived OpenSpec changes;
- any new source/test file other than the four exact `scope.py`/`differential.py` files above.
