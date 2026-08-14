# Tasks: Historical Replay Capsule

All later tasks are bounded to at most two hours and must follow tests-before-code.

## 0. Planning

- [x] 0.1 Define module/core ownership and the B/R/H/D capsule boundary.
- [x] 0.2 Define the exact claim, limitations, unknown behavior, delivery binding, and rollback.
- [x] 0.3 Create public tracking issue #414 and pair it with core issue #675.
- [x] 0.4 Make no package/registry/version/signature changes in this planning commit.

## Implementation-session checklist

- [ ] B.1 Create a dedicated feature worktree from current `origin/dev`; run `hatch env create`, `hatch run dev-deps`, `hatch run smart-test-status`, and `hatch run contract-test-status` serially before edits.
- [ ] B.2 Refresh/consult the ephemeral hierarchy cache; verify issue #414 parent Feature #161, requested User Story type, labels, project assignment, blockers, and concurrency state. Stop if metadata is incomplete or the issue is already in progress elsewhere.
- [ ] B.3 Run `openspec validate requirements-08-bounded-red-green-proof --strict`, re-read paired core issue #675/PR #674, and confirm the closed allowlist before tests or source edits.
- [ ] B.4 Follow spec -> tests -> actual failing evidence -> source -> actual passing evidence. Record timestamps, exact commands/results, behavioral summaries, limitations, and artifacts in separate TDD evidence sections.

## 1. Failing tests first

- [ ] 1.1 Add `test_final_reconciliation_accepts_valid_brhd_replay_capsule`.
- [ ] 1.2 Add `test_final_reconciliation_keeps_current_execution_and_tdd_chronology_separate`.
- [ ] 1.3 Add `test_capsule_rejects_non_ancestral_or_mismatched_delivery_identity`.
- [ ] 1.4 Add `test_capsule_rejects_changed_selector_plan_mapping_or_failing_evidence_after_red`.
- [ ] 1.5 Add `test_capsule_rejects_nonimplementation_transition_after_red`.
- [ ] 1.6 Add `test_capsule_rejects_invalid_delivery_evidence_transition`.
- [ ] 1.7 Add `test_capsule_requires_fail_at_r_pass_at_h_and_pass_at_distinct_d` and `test_capsule_rejects_wrong_red_failure_identity_with_same_assertion_class`; require exactly one canonical observed red marker matching each frozen mapped `expected_failure_id`.
- [ ] 1.8 Add `test_missing_capsule_is_unknown_under_strict_policy`.
- [ ] 1.9 Add `test_runtime_observation_cannot_claim_complete_dependency_scope`.
- [ ] 1.10 Add a table-driven mandatory-field test that deletes or alters every identity, transition manifest/digest, mapping/plan/selector/expected-failure ID, observed-red-failure-ID digest, JUnit/outcome, runner/toolchain/environment/network/policy/verifier, resource/timestamp, artifact-link, and signed-module field and requires deterministic non-green chronology.
- [ ] 1.11 Add `test_current_execution_passes_without_tdd_chronology` in `tests/unit/specfact_requirements/test_requirements_lifecycle.py`.
- [ ] 1.12 Add `test_historical_capsule_cannot_substitute_for_missing_current_execution` in `tests/unit/specfact_requirements/test_requirements_lifecycle.py`.
- [ ] 1.13 Add `test_code_review_accepts_current_execution_without_tdd_chronology` in `tests/unit/specfact_code_review/run/test_commands.py`; assert Requirements provenance is retained but does not calculate review findings, score, verdict, or exit code.
- [ ] 1.14 Before any source edit, update `requirements-evidence.yaml` under the accepted mapping schema with the exact selectors from tasks 1.1–1.13 and one stable opaque `expected_failure_id` per replayed selector, verify each selector collects once, and freeze the accepted mapping and plan digests. Do not invent selectors on this planning-only branch.
- [ ] 1.15 Record actual failing commands/results in `TDD_EVIDENCE.md` before source edits.

## 2. Minimal implementation

- [ ] 2.1 In new `requirements/replay_proof.py`, add typed versioned capsule and canonical digest/link validation only.
- [ ] 2.2 Validate B/R/H/D identities, all three transition classifications, frozen red inputs, selector equality, mapped/observed red failure-identity equality, fail/pass/pass outcome rules, every mandatory digest, signed module identity, and verifier epoch.
- [ ] 2.3 Delegate independent chronology reconciliation and the public capsule input from the existing Requirements lifecycle/command seams.
- [ ] 2.4 Retain chronology in Code Review context without verdict fusion.
- [ ] 2.5 Keep legacy-ledger read compatibility and prohibit new generation.

## 3. Verification and release

- [ ] 3.1 Run format, type, lint, YAML, bundle imports, signature/version-bump verification, contracts, focused/full tests, strict OpenSpec, and explicit-range/full Code Review; resolve every finding.
- [ ] 3.2 Update `docs/bundles/requirements/overview.md`, `CHANGELOG.md`, and `packages/specfact-requirements/module-package.yaml`; update the Code Review manifest/docs only if its serialized proof context changes.
- [ ] 3.3 Run `python scripts/publish_module.py --bundle specfact-requirements` as the publish pre-check, then use the existing release wrapper to generate `registry/index.json`, `registry/modules/specfact-requirements-<version>.tar.gz`, its `.sha256`, and `registry/signatures/specfact-requirements-<version>.tar.sig`. Never hand-edit archives, checksums, or signatures.
- [ ] 3.4 Record immutable repository commit/tree, package/capsule-schema versions, manifest integrity, signer/signature identities, registry/archive/checksum identities, core compatibility, and passing verification evidence for the signed release supplied to core.
- [ ] 3.5 After implementation and passing evidence are merged and rollout prerequisites hold, from the repository root run exactly `openspec archive requirements-08-bounded-red-green-proof`; never move the change directory manually.
- [ ] 3.6 Remove the merged worktree/branch, run `git worktree prune`, and record the policy self-check.

## Prohibited shortcuts

- Do not run Git, pytest, or subprocesses in modules.
- Do not infer imports, plugins, configuration, data files, aliases, mutation, namespaces, symlinks, or dynamic execution.
- Do not accept old red JUnit without the new trusted capsule for new proofs.
- Do not generate new legacy-ledger evidence.
- Do not emit pass/no-impact for missing or untrusted capsule facts.
- Do not manually move OpenSpec change directories or hand-edit generated registry archives/checksums/signatures.

## Closed implementation allowlist

OpenSpec mapping and evidence records:

- `openspec/changes/requirements-08-bounded-red-green-proof/requirements-evidence.yaml`: before source edits only, add the exact selectors from tasks 1.1–1.13, one stable opaque `expected_failure_id` per replayed selector, and freeze the accepted mapping/plan digests.
- `openspec/changes/requirements-08-bounded-red-green-proof/TDD_EVIDENCE.md`: add failing-before evidence after the named tests fail and before source edits; add a separate passing-after section only after implementation passes.
- `openspec/changes/requirements-08-bounded-red-green-proof/CHANGE_VALIDATION.md`: final implementation validation only after implementation and all required gates complete.

Capsule model/validation:

- New exactly `packages/specfact-requirements/src/specfact_requirements/requirements/replay_proof.py`.
- New exactly `tests/unit/specfact_requirements/test_requirements_replay_proof.py`.
- `replay_proof.py` validates typed data and canonical hash relationships only; it must not run Git, pytest, or subprocesses.

Integration seams:

- `packages/specfact-requirements/src/specfact_requirements/requirements/lifecycle.py`: delegate historical-proof acceptance to `replay_proof.py`; preserve selector validation, plan construction, and JUnit parsing.
- `packages/specfact-requirements/src/specfact_requirements/requirements/commands.py` and, only for registration/help, `app.py` and `__init__.py`.
- `packages/specfact-requirements/src/specfact_requirements/requirements/evidence.py` only for canonical current-execution/chronology propagation; no second verdict engine.
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` and `findings.py` only to validate/retain capsule provenance without verdict fusion.

Tests/docs/release:

- `tests/unit/specfact_requirements/test_requirements_lifecycle.py`, `test_requirements_evidence.py`, and new `test_requirements_replay_proof.py`.
- `tests/integration/specfact_requirements/test_command_apps.py`.
- `tests/unit/specfact_code_review/run/test_commands.py` and `test_findings.py` only if Code Review context changes.
- `docs/bundles/requirements/overview.md`; Code Review docs only if its public payload changes.
- `packages/specfact-requirements/module-package.yaml`; `packages/specfact-code-review/module-package.yaml` only if its payload changes.
- `CHANGELOG.md`, `registry/index.json`, generated Requirements archive/checksum/signature paths named in task 3.3, and generated command/docs outputs required by policy, only after behavior passes and only through existing generators.

Explicitly forbidden:

- core-side ancestry, worktree, test-execution, or runtime-tracing code;
- AST/import/conftest/plugin/config/data dependency inference;
- analyzer or AI-review changes;
- editing shipped R07 history as a substitute for this R08 delta.
