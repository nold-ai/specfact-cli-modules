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
- [ ] 1.11 Add `test_range_scope_omitted_enforcement_defaults_to_full` and update existing `test_review_run_instructions_prints_ai_workflow_without_running_review` to require the executable range/base/head/`--enforcement full` workflow; retain explicit range-plus-changed rejection.
- [ ] 1.12 Add `test_installed_merge_quality_guidance_uses_pr_range`; prove rules updater output and the bundled skill use range/base/head/full for merge review while simplification preview remains worktree-scoped.
- [ ] 1.13 Add table-driven `test_range_scope_rejects_narrowing_filters_before_analysis` for `--exclude-tests`, `--focus source|tests|docs|simplify`, `--path`, `--no-tests`, and `--level`; no narrowed result may carry `assurance_kind=pr_range` or produce false NOT_APPLICABLE.
- [ ] 1.14 Add `test_merge_quality_guidance_requires_complete_pr_range`; cover both agent-rule files, module/bundle guides, generated instructions, updater/bundled skill, and tracked skill copies. Assert local pre-commit positional and simplification worktree guidance is explicitly non-PR.
- [ ] 1.15 Add `test_pr_range_rejects_base_ref_mismatching_authenticated_expected_target_tip` and `test_pr_range_consumer_rejects_untrusted_target_tip`; bind provider/repository/PR-or-queue/ref/commit/tree/context digest, reject caller self-assertion, and prove producer plus independent consumer equality.

## 2. Failing differential/report tests

- [ ] 2.1 Add `test_introduced_blocker_off_added_line_still_blocks`.
- [ ] 2.2 Add `test_unchanged_baseline_blocker_is_retained_but_not_introduced`.
- [ ] 2.3 Add `test_baseline_analysis_failure_is_unknown`.
- [ ] 2.4 Add `test_range_differential_uses_merge_base_snapshot_when_base_tip_advanced`.
- [ ] 2.5 Add `test_pure_rename_preserves_unchanged_fingerprint`; use the recorded one-to-one rename map to canonicalize the head file anchor while retaining both paths in evidence.
- [ ] 2.6 Add `test_default_pr_range_analyzer_profile_has_closed_membership`, `test_report_exposes_mandatory_analyzer_coverage`, `test_analyzer_identity_mismatch_is_unknown`, and `test_head_config_cannot_suppress_introduced_finding`. Freeze the eight required IDs plus conditional `semgrep-bugs` and `targeted-pytest-coverage` rules; vary analyzer/toolchain/policy/config identities independently; prove explicit target-policy config argv/root for Ruff, Pylint, and Semgrep plus per-snapshot projected basedpyright argv/root, and UNKNOWN on injection/projection failure. Rename/update existing `test_run_contract_check_ignores_crosshair_timeout` to `test_run_contract_check_reports_crosshair_timeout_for_mandatory_coverage` to prove the adapter emits explicit failure; the runner coverage test proves that failure yields UNKNOWN.
- [ ] 2.7 Add `test_range_uses_authorized_base_tip_policy_when_target_advanced`; keep the source baseline at merge base, bind the target tip to trusted PR/CI context, apply its sealed policy to both source snapshots, and prove moved/untrusted/missing target policy is UNKNOWN.
- [ ] 2.8 Add `test_targeted_pytest_coverage_classifies_failure_vs_unknown` and `test_targeted_pytest_new_input_absent_at_merge_base_is_not_applicable_for_that_side`; cover head assertion failure, infrastructure/no-tests/coverage UNKNOWN, a newly added production file plus test, and rejection of the baseline-absence exception when governed head production survives without tests.
- [ ] 2.9 Add parameterized `test_required_analyzers_structurally_empty_snapshot_is_not_applicable` for add-only and delete-only governed Python ranges; assert manifest-bound per-side NOT_APPLICABLE, required execution on every non-empty side, applicable aggregate range status, and rejection of an unrecorded adapter empty-file return.
- [ ] 2.10 Add `test_run_contract_check_reports_crosshair_process_error_for_mandatory_coverage`; cover documented CrossHair process-error exit code 2 with empty parsed findings, retained exit/stderr diagnostics, UNKNOWN coverage, and a control proving parsed counterexamples remain findings.
- [ ] 2.11 Add `test_basedpyright_project_rebases_relative_paths_per_snapshot` and `test_basedpyright_project_rejects_unbound_paths`; use an imported dependency with different merge-base/head content, cover nested execution-environment paths plus `extraPaths` and `venvPath`/`venv`, prove the per-side projection/toolchain digests, and reject policy-bundle/worktree/escaping/missing paths as UNKNOWN.
- [ ] 2.12 Add `test_import_capable_analyzers_use_snapshot_invocation_context`; parameterize Pylint init-hook, CrossHair, and targeted pytest over an imported dependency with distinct merge-base/head/worktree content. Assert snapshot-root cwd, sanitized PYTHONPATH/PYTHONHOME/user-site/startup/plugin state, sealed non-editable toolchain identity, external output root, context digest, correct side-specific import, and UNKNOWN on caller-source/context mismatch.
- [ ] 2.13 Add `test_fixable_error_remains_blocking_until_applied` and update existing `test_score_review_single_fixable_error` to expect FAIL; production `scorer.py` remains unchanged.
- [ ] 2.14 Add `test_report_never_says_all_passed_with_mandatory_unknown`.
- [ ] 2.15 Add table-driven `test_schema_1_6_assurance_status_legacy_projection_and_exit_matrix` for PASS/FAIL/UNKNOWN/NOT_APPLICABLE under strict and shadow modes, including enforce-to-full normalization, changed/worktree compatibility, and range-plus-changed rejection.
- [ ] 2.16 Add `test_schema_1_6_consumer_compatibility_matrix_is_closed` in `tests/unit/specfact_code_review/run/test_findings.py`; validate the exact checked-in package resource, its four canonical reports, permitted legacy projections, strict/shadow exits, invalid mismatch cases, and canonical digest.
- [ ] 2.17 Add `test_schema_1_6_missing_assurance_status_is_unknown` and legacy-reader cases proving old PASS/FAIL cannot imply UNKNOWN/NOT_APPLICABLE.
- [ ] 2.18 Add table-driven `test_ledger_authoritative_assurance_controls_rewards_and_streaks` for schema 1.6 PASS/FAIL/UNKNOWN/NOT_APPLICABLE plus legacy PASS_WITH_ADVISORY. Prove UNKNOWN/NOT_APPLICABLE persist verbatim, apply zero reward/last delta, leave both streaks unchanged, and are accepted by local/Supabase schemas. Add a no-findings UNKNOWN case proving local and Supabase `report_json` plus canonical SHA-256 `report_digest` retain scope/analyzer diagnostics.
- [ ] 2.19 Add `test_cleanup_enrichment_preserves_schema_1_6_assurance_status`; exercise UNKNOWN with empty findings and prove cleanup forecast refresh preserves schema, assurance, scope/analyzer evidence, legacy projection, and exit code.
- [ ] 2.20 Add `test_requirements_evidence_attachment_preserves_schema_1_6_assurance_status` in `tests/unit/specfact_code_review/run/test_commands.py`; attach validated Requirements context to an UNKNOWN report and prove schema, assurance, scope/analyzer evidence, legacy projection, and exit code remain unchanged.
- [ ] 2.21 Collect the exact canonical pytest node ID for every test-authored CR14 scenario, write each selector into `requirements-evidence.yaml`, and rerun strict mapping validation. Do not edit production source in this task.
- [ ] 2.22 Build the deterministic plan from the accepted mapping and source identity, then write and commit `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/IMPLEMENTATION_CHECKPOINT.json`. Schema version `1` SHALL contain: `change_id`; `checkpoint_parent.commit_sha` and `tree_sha`; `mapping_digest`; `plan.id` and `digest`; sorted `selectors` plus `selector_digest`; sorted `frozen_input_paths` plus `frozen_input_manifest_digest`; and sorted `analyzers[]` entries with `id`, `required`, `version`, `toolchain_digest`, `policy_digest`, and `config_digest`. All digests are canonical SHA-256 values. The parent commit/tree identifies the test-and-mapping checkpoint before this evidence file is added.
- [ ] 2.23 Verify the committed checkpoint against the current frozen inputs, execute its exact selectors, confirm the expected failing outcomes, and record the exact commands, checkpoint-file digest, and outcomes in `TDD_EVIDENCE.md` before any source edit. Any frozen-input mismatch invalidates the checkpoint and repeats tasks 2.21–2.23. Section 3 is blocked until this task passes.

## 3. Minimal implementation

Each item consumes only the named failing tests from Section 2 and must finish green before the next item starts.

- [ ] 3.1 Add request/status types for worktree, index, range, full, and explicit-files scope; delegate all Git discovery from `run/commands.py` to `scope.py`.
- [ ] 3.2 Resolve full base/head/merge-base identities and validate `expected_target_tip` plus trusted-context digest; mismatch is UNKNOWN.
- [ ] 3.3 Materialize and manifest the exact index snapshot, including conflicts/intent-to-add/object failures and pre/post integrity checks.
- [ ] 3.4 Materialize detached merge-base/head source roots plus rename/deletion facts and pre/post source manifests; clean roots or report UNKNOWN.
- [ ] 3.5 Materialize the authorized target-tip policy bundle and its source digest; candidate head policy remains shadow-only.
- [ ] 3.6 Build and validate per-snapshot configuration projections, including the canonical shared identity and side-specific projected digests.
- [ ] 3.7 Build one `SnapshotInvocationContext` per side with snapshot cwd/import roots, sealed non-editable toolchain/dependencies, sanitized Python/pytest environment, pinned plugins, external output root, and context digest.
- [ ] 3.8 Reject every range narrowing/mutation combination and normalize omitted enforcement to strict full before materialization.
- [ ] 3.9 Emit UNKNOWN for unresolved scope/context and NOT_APPLICABLE only for manifest-proven empty range or per-snapshot analyzer input.
- [ ] 3.10 Define the exact runner-owned `pr-range-v1` membership and serialize per-snapshot required/conditional coverage facts.
- [ ] 3.11 Make CrossHair timeout and documented process-error exits failed contracts coverage while retaining parsed counterexamples as findings.
- [ ] 3.12 Execute targeted pytest/coverage per snapshot with explicit absent-side, FAIL, UNKNOWN, selector, environment, and artifact evidence.
- [ ] 3.13 Update Ruff invocation only for explicit target-policy config or isolated mode.
- [ ] 3.14 Update Pylint invocation only for explicit target-policy rcfile/default plus snapshot invocation context.
- [ ] 3.15 Update basedpyright invocation only for per-snapshot projected project files and sealed toolchain paths.
- [ ] 3.16 Update both Semgrep passes only for explicit target-policy bundle roots and surfaced adapter failures.
- [ ] 3.17 Implement stable base/head fingerprint classification, including one-to-one rename normalization and shared-identity validation.
- [ ] 3.18 Separate finding lifecycle, differential state, autofix availability, waiver reference, and derived blocking policy in the canonical model.
- [ ] 3.19 Add schema 1.6 authoritative status, legacy projection, normalized enforcement, and strict/shadow exit behavior.
- [ ] 3.20 Preserve schema 1.6 fields through cleanup refresh and Requirements-context attachment without verdict fusion.
- [ ] 3.21 Add and validate the closed consumer compatibility matrix package resource; bind its digest in package metadata/tests.
- [ ] 3.22 Update ledger model/local persistence and neutral reward/streak behavior for UNKNOWN/NOT_APPLICABLE while retaining legacy reads.
- [ ] 3.23 Migrate Supabase constraints and canonical `report_json`/`report_digest` persistence; preserve legacy rows.
- [ ] 3.24 Update CLI contracts and canonical agent/module/bundle/generated/updater/skill guidance to complete PR range; keep staged positional and simplification worktree guidance explicitly non-PR.

## 4. Release and adoption

- [ ] 4.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and explicit-range self-review.
- [ ] 4.2 Benchmark #665–#671 and seeded false-green, staged-versus-unstaged index, mutable-worktree, advanced-base-tip, positional-downgrade, pure-rename, and false-introduction cases.
- [ ] 4.3 After behavior passes, update public docs, command references, bundle version, changelog, and `module-package.yaml` with `core_compatibility: '>=0.56.0,<1.0.0'`. Do not generate or hand-edit registry archives, checksums, signatures, sidecars, or `registry/index.json` on the feature branch.
- [ ] 4.4 Re-run the complete feature-branch gates and merge the reviewed implementation PR to `dev` only when schema 1.6 consumer compatibility is proven.
- [ ] 4.5 Observe the canonical `.github/workflows/publish-modules.yml` run and review its `auto/publish-dev-<run-id>` PR.
- [ ] 4.6 Require the generated signed manifest/archive/checksum/sidecar/index, filesystem signature/version-bump verification, and full quality matrix before merging the auto-publish PR.
- [ ] 4.7 After the signed consumer compatibility matrix passes and a separate core adoption change is accepted, give core the final merged commit/tree, module version, schema 1.6 contract and compatibility-matrix digest, archive/checksum/signature, signer, workflow, and auto-publish PR identities. The core PR SHALL keep `scripts/pre_commit_code_review.py` limited to `explicit_files` but make it consume authoritative schema 1.6 status/exit fields; a separate PR-range consumer SHALL reject any report or code path that cannot consume them. Core PR CI SHALL pass full base/head refs plus the authenticated expected target-tip commit/tree/context from the trusted GitHub PR or merge-queue event, require the reported expected/resolved target-tip, merge-base, and head identities plus `assurance_kind=pr_range`, independently compare them to that event context, and migrate in shadow, warning, then enforce mode.
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
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` only for request translation/validation, consumption of `ScopeResolution`, and the existing post-analysis Requirements-evidence attachment model-copy so it preserves schema 1.6 truth without changing Requirements verdict semantics.
- `tests/unit/specfact_code_review/review/test_commands.py` only to replace the obsolete positional-file PR instruction expectation with the executable range/base/head/full workflow.
- `tests/unit/specfact_code_review/run/test_commands.py` and `tests/cli-contracts/specfact-code-review-run.scenarios.yaml`.

Canonical merge-quality guidance:

- `docs/agent-rules/20-repository-context.md` and `docs/agent-rules/50-quality-gates-and-review.md` only to replace mandatory merge-review commands with complete range/base/head/full guidance and label the staged pre-commit helper non-PR.
- `docs/modules/code-review.md` and `docs/bundles/code-review/run.md` only to remove positional branch-delta/changed-worktree PR guidance, document the complete range contract, and retain clearly local examples.
- `packages/specfact-code-review/src/specfact_code_review/rules/updater.py` only to replace merge-quality changed/worktree guidance with the executable range/base/head/full command; simplification preview remains worktree-scoped.
- `packages/specfact-code-review/src/specfact_code_review/resources/skills/specfact-code-review/SKILL.md` for the same merge-quality correction.
- `skills/specfact-code-review/SKILL.md` and `.vibe/skills/specfact-code-review/SKILL.md` only as updater-generated tracked copies after the bundled source and tests pass; never hand-edit them independently.
- `tests/unit/specfact_code_review/rules/test_updater.py` and `tests/unit/docs/test_code_review_docs_parity.py` only for focused guidance/parity regressions.
- `scripts/pre_commit_code_review.py`, `scripts/pre-commit-quality-checks.sh`, and their tests remain unchanged: they are local staged positional-file evidence, not PR assurance.

Scope:

- New exactly `packages/specfact-code-review/src/specfact_code_review/run/scope.py`.
- New exactly `tests/unit/specfact_code_review/run/test_scope.py`.
- `scope.py` is the only component allowed to invoke Git for scope discovery, index materialization, and detached merge-base/head snapshot materialization; replace/delegate the old scope helpers in `run/commands.py`.

Differential enforcement:

- New exactly `packages/specfact-code-review/src/specfact_code_review/run/differential.py`.
- New exactly `tests/unit/specfact_code_review/run/test_differential.py`.
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py` builds/validates snapshot invocation contexts, runs targeted pytest under them, collects analyzer facts, and consumes classification; `differential.py` classifies already-produced base/head findings and contains no analyzer or Requirements logic.

Analyzer configuration and failure propagation:

- `packages/specfact-code-review/src/specfact_code_review/tools/ruff_runner.py` and `tests/unit/specfact_code_review/tools/test_ruff_runner.py` only to accept the invocation context and use explicit baseline `--config` or `--isolated`.
- `packages/specfact-code-review/src/specfact_code_review/tools/pylint_runner.py` and `tests/unit/specfact_code_review/tools/test_pylint_runner.py` only to use the explicit target-policy `--rcfile` or sealed pinned-default config and consume the snapshot-root cwd/import environment so init hooks cannot resolve caller/head source.
- `packages/specfact-code-review/src/specfact_code_review/tools/basedpyright_runner.py` and `tests/unit/specfact_code_review/tools/test_basedpyright_runner.py` only to consume the per-snapshot projected `--project` artifact, remove `--project .`/direct policy-bundle use, and prove imported-path/toolchain binding; projection construction and path validation remain in `scope.py`.
- `packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py` and `tests/unit/specfact_code_review/tools/test_semgrep_runner.py` only to require the explicit target-policy `bundle_root` for both Semgrep passes.
- `packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py` only to consume the snapshot invocation context and replace swallowed CrossHair timeout and documented tool/process-error exits (including code 2) with explicit failed contracts coverage; contract rules and parsed counterexample semantics remain unchanged.
- `tests/unit/specfact_code_review/tools/test_contract_runner.py` only to replace the timeout-ignore regression with the named fail-closed timeout case and add the focused process-error-exit regression/control.

Report truth:

- New exactly `packages/specfact-code-review/src/specfact_code_review/resources/contracts/review-report-schema-1.6-consumer-matrix.json` for the closed signed producer/consumer status-projection-exit contract; no other compatibility fixture is allowed.
- `packages/specfact-code-review/src/specfact_code_review/run/findings.py` remains the only report/finding model; do not create a parallel model. `fixable` must not affect `is_blocking()`.
- `packages/specfact-code-review/src/specfact_code_review/run/cleanup_evidence.py` only to preserve the incoming schema-1.6 report/status/evidence fields while refreshing cleanup evidence; cleanup algorithms and forecast semantics are out of scope.
- `tests/unit/specfact_code_review/run/test_cleanup_evidence.py` only for the schema/status preservation regression.
- `tests/unit/specfact_code_review/run/test_findings.py`, `tests/unit/specfact_code_review/run/test_runner.py`, and existing `tests/unit/specfact_code_review/run/test_scorer.py` only to update the fixable-error regression expectation; production `scorer.py` remains forbidden.

First-party ledger consumer:

- `packages/specfact-code-review/src/specfact_code_review/ledger/client.py` only for authoritative-status persistence and neutral reward/streak policy.
- `tests/unit/specfact_code_review/ledger/test_client.py`.
- `packages/specfact-code-review/src/specfact_code_review/resources/supabase/review_ledger_ddl.sql` only to migrate verdict constraints and add nullable `report_json`/`report_digest` columns for canonical schema 1.6 audit evidence while preserving existing rows.
- `tests/cli-contracts/specfact-code-review-ledger.scenarios.yaml` and `docs/bundles/code-review/ledger.md` only for the public ledger status contract.

End-to-end/docs/release:

- `tests/e2e/specfact_code_review/test_review_run_e2e.py`, the CLI-contract YAML, and `docs/bundles/code-review/run.md`.
- `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/requirements-evidence.yaml` only in task 2.21 to add exact collected selectors and freeze their mapping identity.
- New exactly `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/IMPLEMENTATION_CHECKPOINT.json` in task 2.22 with only the closed schema named there.
- `openspec/changes/code-review-14-scope-truth-and-differential-enforcement/TDD_EVIDENCE.md` for acceptance task A.2, task 2.23 failing evidence, and later verified green evidence.
- `CHANGELOG.md` and `packages/specfact-code-review/module-package.yaml` only after behavior passes for the required release note, version, and compatibility metadata.
- Generated docs/registry/signatures only after tests pass; use existing generators and never hand-edit archives.

Explicitly forbidden:

- `packages/specfact-code-review/src/specfact_code_review/run/forecast.py`, `packages/specfact-code-review/src/specfact_code_review/run/scorer.py`, and detector/rule-semantic changes under `specfact_code_review/tools/`; only the exact adapter configuration/failure plumbing above is allowed;
- the Requirements package and archived OpenSpec changes;
- any new source/test/resource file other than the four exact `scope.py`/`differential.py` files and the one exact schema 1.6 consumer-matrix resource above.
