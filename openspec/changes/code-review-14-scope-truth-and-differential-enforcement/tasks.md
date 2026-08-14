# Tasks: Scope Truth and Differential Enforcement

Every implementation task targets at most two hours. Tests precede code. This planning branch must remain OpenSpec-only.

## 0. Planning

- [x] 0.1 Define explicit scope sources, truthful statuses, differential analysis, and non-goals.
- [x] 0.2 Define a one-release compatibility path for `--scope changed`.
- [x] 0.3 Create no package, test, registry, version, signature, prompt, or generated-doc changes.

## Implementation acceptance gate

- [ ] A.1 Before tests or implementation, revalidate this accepted module contract against current `dev`, inspect the public core Code Review callers and the adjudicated #665–#671 benchmark at immutable refs, and confirm the merged core #674 boundary that generic review-scope semantics remain module-owned.
- [ ] A.2 Record those reviewed core refs/paths and the decision that module implementation may proceed independently in this change's `TDD_EVIDENCE.md`. Do not edit core from this change. A separate accepted core adoption change is required before release task 4.7, after the signed module release exists.

## 1. Failing scope tests

- [ ] 1.1 Add `test_range_scope_includes_committed_files_on_clean_checkout`.
- [ ] 1.2 Add `test_range_scope_uses_merge_base_not_head_worktree`.
- [ ] 1.3 Add `test_scope_git_failure_is_unknown_and_blocks_enforcement`.
- [ ] 1.4 Add `test_empty_resolved_range_is_not_applicable`.
- [ ] 1.5 Add `test_range_scope_includes_changed_tests_by_default`.
- [ ] 1.6 Add static CLI-contract red cases for required full refs, invalid combinations, deprecated changed alias, assurance/enforcement projection, and explicit positional files. Do not add Git setup to the argv-only contract harness; tasks 1.8, 1.10, 2.4, and 2.6 own stateful temporary-repository cases.
- [ ] 1.7 Add `test_pr_assurance_rejects_positional_file_downgrade` while retaining local explicit-file enforcement.
- [ ] 1.8 Add `test_range_analysis_uses_materialized_commit_snapshots` with caller-worktree mutation and pre/post manifest mismatch cases.
- [ ] 1.9 Add `test_index_and_range_reject_fix_preview_and_mutation_options`.
- [ ] 1.10 Add `test_index_scope_reads_staged_blobs_not_unstaged_worktree` with conflicting staged/unstaged bytes at the same path.

## 2. Failing differential/report tests

- [ ] 2.1 Add `test_introduced_blocker_off_added_line_still_blocks`.
- [ ] 2.2 Add `test_unchanged_baseline_blocker_is_retained_but_not_introduced`.
- [ ] 2.3 Add `test_baseline_analysis_failure_is_unknown`.
- [ ] 2.4 Add `test_range_differential_uses_merge_base_snapshot_when_base_tip_advanced`.
- [ ] 2.5 Add `test_pure_rename_preserves_unchanged_fingerprint`; use the recorded one-to-one rename map to canonicalize the head file anchor while retaining both paths in evidence.
- [ ] 2.6 Add `test_report_exposes_mandatory_analyzer_coverage` and `test_analyzer_identity_mismatch_is_unknown`; the latter varies analyzer version, toolchain, policy, and config identities independently.
- [ ] 2.7 Add `test_fixable_error_remains_blocking_until_applied` and update existing `test_score_review_single_fixable_error` to expect FAIL; production `scorer.py` remains unchanged.
- [ ] 2.8 Add `test_report_never_says_all_passed_with_mandatory_unknown`.
- [ ] 2.9 Add table-driven `test_schema_1_6_assurance_status_legacy_projection_and_exit_matrix` for PASS/FAIL/UNKNOWN/NOT_APPLICABLE under strict and shadow modes, including enforce-to-full normalization, changed/worktree compatibility, and range-plus-changed rejection.
- [ ] 2.10 Add `test_schema_1_6_missing_assurance_status_is_unknown` and legacy-reader cases proving old PASS/FAIL cannot imply UNKNOWN/NOT_APPLICABLE.
- [ ] 2.11 Add table-driven `test_ledger_authoritative_assurance_controls_rewards_and_streaks` for schema 1.6 PASS/FAIL/UNKNOWN/NOT_APPLICABLE plus legacy PASS_WITH_ADVISORY. Prove UNKNOWN/NOT_APPLICABLE persist verbatim, apply zero reward/last delta, leave both streaks unchanged, and are accepted by local/Supabase schemas. Add a no-findings UNKNOWN case proving local and Supabase `report_json` plus canonical SHA-256 `report_digest` retain scope/analyzer diagnostics.
- [ ] 2.12 Collect the exact canonical pytest node ID for every test-authored CR14 scenario, write each selector into `requirements-evidence.yaml`, and rerun strict mapping validation. Do not edit production source in this task.
- [ ] 2.13 Build the deterministic plan from the accepted mapping and source identity, then write and commit `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/IMPLEMENTATION_CHECKPOINT.json`. Schema version `1` SHALL contain: `change_id`; `checkpoint_parent.commit_sha` and `tree_sha`; `mapping_digest`; `plan.id` and `digest`; sorted `selectors` plus `selector_digest`; sorted `frozen_input_paths` plus `frozen_input_manifest_digest`; and sorted `analyzers[]` entries with `id`, `required`, `version`, `toolchain_digest`, `policy_digest`, and `config_digest`. All digests are canonical SHA-256 values. The parent commit/tree identifies the test-and-mapping checkpoint before this evidence file is added.
- [ ] 2.14 Verify the committed checkpoint against the current frozen inputs, execute its exact selectors, confirm the expected failing outcomes, and record the exact commands, checkpoint-file digest, and outcomes in `TDD_EVIDENCE.md` before any source edit. Any frozen-input mismatch invalidates the checkpoint and repeats tasks 2.12–2.14. Section 3 is blocked until this task passes.

## 3. Minimal implementation

- [ ] 3.1 Implement the explicit worktree/index/range/full resolver and immutable scope evidence.
- [ ] 3.2 In `scope.py`, materialize the exact index snapshot and detached merge-base/head commit trees, produce and pre/post verify selected-input manifests, and clean temporary roots; no other component may invoke Git.
- [ ] 3.3 Reject positional-file downgrade for PR-range policy and reject fix/preview/mutation options in index and range snapshot modes.
- [ ] 3.4 Add unknown/not-applicable handling before analyzer execution.
- [ ] 3.5 Implement isolated symmetric merge-base/head analyzer execution with identical immutable analyzer-version, toolchain, policy, and configuration identities; any identity mismatch yields UNKNOWN.
- [ ] 3.6 Add stable fingerprints and introduced/fixed/unchanged/unknown classification only after task 3.5 proves identical identities; normalize head file anchors through resolved one-to-one rename facts before matching.
- [ ] 3.7 Add mandatory analyzer coverage evidence.
- [ ] 3.8 Separate finding status, differential state, autofix availability, and blocking policy.
- [ ] 3.9 Add schema 1.6 `assurance_status`, versioned legacy reading, closed dual-write projection, and strict/shadow exit matrix.
- [ ] 3.10 Update the existing ledger client/model, local reader, Supabase DDL constraints/columns, focused ledger tests/contracts, and ledger docs so schema 1.6 UNKNOWN/NOT_APPLICABLE are persisted neutral states while pre-1.6 behavior remains compatible. Persist the complete canonical report in `report_json` with `report_digest`; legacy rows may leave both nullable.
- [ ] 3.11 Update CLI behavior, `docs/bundles/code-review/run.md`, and exactly `tests/cli-contracts/specfact-code-review-run.scenarios.yaml` for static argv/report cases only; retain `changed` only as a deprecated worktree alias and keep stateful Git setup in the named unit/e2e modules.

## 4. Release and adoption

- [ ] 4.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and explicit-range self-review.
- [ ] 4.2 Benchmark #665–#671 and seeded false-green, staged-versus-unstaged index, mutable-worktree, advanced-base-tip, positional-downgrade, pure-rename, and false-introduction cases.
- [ ] 4.3 After behavior passes, update public docs, command references, bundle version, changelog, and `module-package.yaml` with `core_compatibility: '>=0.56.0,<1.0.0'`. Do not generate or hand-edit registry archives, checksums, signatures, sidecars, or `registry/index.json` on the feature branch.
- [ ] 4.4 Re-run the complete feature-branch gates and merge the reviewed implementation PR to `dev` only when schema 1.6 consumer compatibility is proven.
- [ ] 4.5 Observe the canonical `.github/workflows/publish-modules.yml` run and review its `auto/publish-dev-<run-id>` PR.
- [ ] 4.6 Require the generated signed manifest/archive/checksum/sidecar/index, filesystem signature/version-bump verification, and full quality matrix before merging the auto-publish PR.
- [ ] 4.7 After a separate core adoption change is accepted, give core the final merged commit/tree, module version, schema 1.6 contract, archive/checksum/signature, signer, workflow, and auto-publish PR identities. Core PR CI SHALL pass full base/head refs to range scope, require the reported merge-base/head identities and `assurance_kind=pr_range`, and migrate in shadow, warning, then enforce mode.
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
- `scope.py` is the only component allowed to invoke Git for scope discovery, index materialization, and detached merge-base/head snapshot materialization; replace/delegate the old scope helpers in `run/commands.py`.

Differential enforcement:

- New exactly `packages/specfact-code-review/src/specfact_code_review/run/differential.py`.
- New exactly `tests/unit/specfact_code_review/run/test_differential.py`.
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py` collects analyzer facts and consumes classification; `differential.py` classifies already-produced base/head findings and contains no analyzer or Requirements logic.

Report truth:

- `packages/specfact-code-review/src/specfact_code_review/run/findings.py` remains the only report/finding model; do not create a parallel model. `fixable` must not affect `is_blocking()`.
- `tests/unit/specfact_code_review/run/test_findings.py`, `tests/unit/specfact_code_review/run/test_runner.py`, and existing `tests/unit/specfact_code_review/run/test_scorer.py` only to update the fixable-error regression expectation; production `scorer.py` remains forbidden.

First-party ledger consumer:

- `packages/specfact-code-review/src/specfact_code_review/ledger/client.py` only for authoritative-status persistence and neutral reward/streak policy.
- `tests/unit/specfact_code_review/ledger/test_client.py`.
- `packages/specfact-code-review/src/specfact_code_review/resources/supabase/review_ledger_ddl.sql` only to migrate verdict constraints and add nullable `report_json`/`report_digest` columns for canonical schema 1.6 audit evidence while preserving existing rows.
- `tests/cli-contracts/specfact-code-review-ledger.scenarios.yaml` and `docs/bundles/code-review/ledger.md` only for the public ledger status contract.

End-to-end/docs/release:

- `tests/e2e/specfact_code_review/test_review_run_e2e.py`, the CLI-contract YAML, and `docs/bundles/code-review/run.md`.
- `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/requirements-evidence.yaml` only in task 2.12 to add exact collected selectors and freeze their mapping identity.
- New exactly `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/IMPLEMENTATION_CHECKPOINT.json` in task 2.13 with only the closed schema named there.
- `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/TDD_EVIDENCE.md` for acceptance task A.2, task 2.14 failing evidence, and later verified green evidence.
- `packages/specfact-code-review/module-package.yaml` and generated docs/registry/signatures only after tests pass; use existing generators and never hand-edit archives.

Explicitly forbidden:

- `packages/specfact-code-review/src/specfact_code_review/run/cleanup_evidence.py`, `packages/specfact-code-review/src/specfact_code_review/run/forecast.py`, `packages/specfact-code-review/src/specfact_code_review/run/scorer.py`, and analyzer implementations under `specfact_code_review/tools/`;
- the Requirements package and archived OpenSpec changes;
- any new source/test file other than the four exact `scope.py`/`differential.py` files above.
