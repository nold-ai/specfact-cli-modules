# Tasks: Separate Current Execution from Historical Chronology

## 0. Planning-only correction

- [x] 0.1 Define independent `current_execution` and `tdd_chronology` claims.
- [x] 0.2 Move new historical proof to R08 and prohibit dependency-closure inference.
- [x] 0.3 Create OpenSpec-only planning changes with no package or registry edits.

## 1. Failing tests first — each task at most two hours

- [ ] 1.1 Add `test_final_reconciliation_reports_current_execution_without_chronology`. Allowed files: focused Requirements lifecycle tests.
- [ ] 1.2 Add `test_current_execution_pass_does_not_emit_passing_after_red`. Allowed files: focused Requirements report tests.
- [ ] 1.3 Add `test_missing_current_junit_cannot_be_replaced_by_historical_context`. Allowed files: focused reconciliation tests.
- [ ] 1.4 Add `test_review_context_accepts_final_current_execution_without_historical_basis`. Allowed files: focused Code Review context tests.
- [ ] 1.5 Add `test_new_reconciliation_cannot_generate_legacy_tdd_ledger`. Allowed files: focused compatibility tests.
- [ ] 1.6 Record failing commands and outcomes in `TDD_EVIDENCE.md` before source edits.

## 2. Minimal implementation — each task at most two hours

- [ ] 2.1 Add versioned current-execution and chronology fields to the Requirements report model.
- [ ] 2.2 Reconcile current JUnit independently and retain exact outcome classes.
- [ ] 2.3 Update Code Review context validation to retain both claims without requiring chronology.
- [ ] 2.4 Keep old report reading explicit; stop generating legacy-ledger evidence for new changes.
- [ ] 2.5 Update public command/docs fixtures without adding execution or Git behavior.

## 3. Release

- [ ] 3.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and full explicit-range Code Review.
- [ ] 3.2 Update bundle version, manifest integrity, registry entry, signatures, and compatibility metadata.
- [ ] 3.3 Publish the signed release and give core the immutable commit/package identities.

## Prohibited shortcuts

- Do not execute pytest or Git in the Requirements module.
- Do not add AST/import/plugin/configuration/data-read inference.
- Do not make missing chronology invalidate an otherwise valid current-run observation.
- Do not let Requirements status change the Code Review verdict.

## Closed R07 implementation allowlist

R07 may edit only:

- `packages/specfact-requirements/src/specfact_requirements/requirements/lifecycle.py` for the canonical independent claim/status shape;
- `packages/specfact-requirements/src/specfact_requirements/requirements/evidence.py` only to propagate that same shape—never to add another verdict engine;
- `packages/specfact-requirements/src/specfact_requirements/requirements/commands.py` and `packages/specfact-requirements/src/specfact_requirements/requirements/app.py` only for public input/help wiring;
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` and `packages/specfact-code-review/src/specfact_code_review/run/findings.py` only to validate and retain Requirements provenance without verdict fusion;
- `tests/unit/specfact_requirements/test_requirements_lifecycle.py`, `tests/unit/specfact_requirements/test_requirements_evidence.py`, `tests/integration/specfact_requirements/test_command_apps.py`, `tests/unit/specfact_code_review/run/test_commands.py`, and `tests/unit/specfact_code_review/run/test_findings.py`;
- Requirements/Code Review module-package metadata, public docs, and generated release outputs only after behavior passes.

Do not edit R07 exact-selector/JUnit parsing except where a named failing test proves the independent-status schema requires it. Do not add a new aggregate report model or any Git/pytest execution path.
