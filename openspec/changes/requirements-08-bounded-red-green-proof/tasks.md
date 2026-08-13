# Tasks: Historical Replay Capsule

All later tasks are bounded to at most two hours and must follow tests-before-code.

## 0. Planning

- [x] 0.1 Define module/core ownership and the capsule boundary.
- [x] 0.2 Define the exact claim, limitations, unknown behavior, and rollback.
- [x] 0.3 Make no package/registry/version/signature changes in this planning commit.

## 1. Failing tests first

- [ ] 1.1 Add `test_final_reconciliation_accepts_valid_historical_replay_capsule`.
- [ ] 1.2 Add `test_final_reconciliation_keeps_current_execution_and_tdd_chronology_separate`.
- [ ] 1.3 Add `test_capsule_rejects_non_ancestral_red_ref`.
- [ ] 1.4 Add `test_capsule_rejects_changed_selector_or_plan_after_red`.
- [ ] 1.5 Add `test_capsule_rejects_frozen_test_harness_change_after_red`.
- [ ] 1.6 Add `test_capsule_rejects_unclassified_transition_path`.
- [ ] 1.7 Add `test_missing_capsule_is_unknown_under_strict_policy`.
- [ ] 1.8 Add `test_runtime_observation_cannot_claim_complete_dependency_scope`.
- [ ] 1.9 Record exact failing commands in `TDD_EVIDENCE.md` before source edits.

## 2. Minimal implementation

- [ ] 2.1 Add typed versioned capsule and artifact-link models.
- [ ] 2.2 Validate selector equality, outcome rules, transition classifications, digests, and verifier epoch.
- [ ] 2.3 Add independent chronology reconciliation and public capsule input.
- [ ] 2.4 Retain chronology in Code Review context without verdict fusion.
- [ ] 2.5 Keep legacy-ledger read compatibility and prohibit new generation.

## 3. Release

- [ ] 3.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and explicit-range Code Review.
- [ ] 3.2 Update docs, bundle version, manifest, registry, integrity, signatures, and core compatibility.
- [ ] 3.3 Publish a signed release and provide its immutable identity to core.

## Prohibited shortcuts

- Do not run Git or pytest in modules.
- Do not infer imports, plugins, configuration, data files, aliases, mutation, namespaces, symlinks, or dynamic execution.
- Do not accept old red JUnit without the new trusted capsule for new proofs.
- Do not generate new legacy-ledger evidence.
- Do not emit pass/no-impact for missing or untrusted capsule facts.

## Closed implementation allowlist

Capsule model/validation:

- New exactly `packages/specfact-requirements/src/specfact_requirements/requirements/replay_proof.py`.
- New exactly `tests/unit/specfact_requirements/test_requirements_replay_proof.py`.
- `replay_proof.py` validates typed data and hash relationships only; it must not run Git, pytest, or subprocesses.

Integration seams:

- `packages/specfact-requirements/src/specfact_requirements/requirements/lifecycle.py`: delegate historical-proof acceptance to `replay_proof.py`; preserve selector validation, plan construction, and JUnit parsing.
- `packages/specfact-requirements/src/specfact_requirements/requirements/commands.py` and, only for registration/help, `packages/specfact-requirements/src/specfact_requirements/requirements/app.py` and `packages/specfact-requirements/src/specfact_requirements/requirements/__init__.py`.
- `packages/specfact-requirements/src/specfact_requirements/requirements/evidence.py` only for canonical current-execution/chronology status propagation; no second verdict engine.
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` and `packages/specfact-code-review/src/specfact_code_review/run/findings.py` only to validate/retain capsule provenance without verdict fusion.

Tests/docs/release:

- `tests/unit/specfact_requirements/test_requirements_lifecycle.py`, `tests/unit/specfact_requirements/test_requirements_evidence.py`, and the new replay-proof test.
- `tests/integration/specfact_requirements/test_command_apps.py`.
- `tests/unit/specfact_code_review/run/test_commands.py` and `tests/unit/specfact_code_review/run/test_findings.py`.
- Requirements/Code Review module-package metadata, public docs, and generated release outputs only after behavior passes.

Explicitly forbidden:

- core-side ancestry, worktree, test-execution, or runtime-tracing code;
- AST/import/conftest/plugin/config/data dependency inference;
- analyzer or AI-review changes;
- editing shipped R07 history as a substitute for this R08 delta.
