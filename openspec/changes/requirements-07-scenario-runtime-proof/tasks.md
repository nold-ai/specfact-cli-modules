# Tasks: Separate Current Execution from Historical Chronology

## 0. Planning-only correction

- [x] 0.1 Define independent `current_execution` and `red_green_chronology` claims.
- [x] 0.2 Move new historical proof to R08 and prohibit dependency-closure inference.
- [x] 0.3 Create OpenSpec-only planning changes with no package or registry edits.

## Implementation acceptance gate

- [ ] A.1 Before any failing test, source edit, or `specfact_cli` adapter work, verify that the corrected paired core artifacts from merged core PR #674 and this modules contract have both been reviewed and accepted on their target `dev` branches.
- [ ] A.2 Verify issue #368/#414 hierarchy, labels, project assignment, blockers, and concurrency state. Stop when either paired interface or public-work prerequisite is incomplete; re-reading references or confirming the file allowlist is not acceptance.

## 1. Failing tests first — each task at most two hours

- [ ] 1.1 Add `test_final_reconciliation_reports_current_execution_without_chronology`. Allowed files: focused Requirements lifecycle tests.
- [ ] 1.2 Add `test_current_execution_pass_does_not_emit_passing_after_red`. Allowed files: focused Requirements report tests.
- [ ] 1.3 Add `test_missing_current_junit_cannot_be_replaced_by_historical_context`. Allowed files: focused reconciliation tests.
- [ ] 1.4 Add `test_review_context_accepts_final_current_execution_without_historical_basis`. Allowed files: focused Code Review context tests.
- [ ] 1.5 Add `test_new_reconciliation_cannot_generate_legacy_tdd_ledger`. Allowed files: focused compatibility tests.
- [ ] 1.6 Add table-driven `test_current_execution_rejects_each_nonpass_or_noncanonical_result` covering missing, duplicate, ambiguous, skipped, failed, errored, and non-canonical selector results.
- [ ] 1.7 Add table-driven `test_review_context_rejects_each_invalid_requirements_evidence_class` covering unreadable, malformed, unsupported-schema, non-final evidence, and corrected-schema evidence missing the mandatory chronology claim object before review execution.
- [ ] 1.8 Add `test_report_uses_canonical_no_chronology_claim_object` for `status: not_evaluated` plus `reason: capsule_not_supplied`, and `status: unknown` when requested chronology evidence is missing or untrusted.
- [ ] 1.9 Add `test_rollback_reader_preserves_independent_claims_as_opaque_provenance` and prove old readers never reinterpret corrected chronology as a legacy basis.
- [ ] 1.10 Record failing commands and outcomes in `TDD_EVIDENCE.md` before source edits.

## 2. Minimal implementation — each task at most two hours

- [ ] 2.1 Add versioned current-execution and chronology fields to the Requirements report model.
- [ ] 2.2 Reconcile current JUnit independently and retain exact outcome classes.
- [ ] 2.3 Update Code Review context validation to require and retain both corrected-schema claim objects without requiring a successful chronology attestation; use the versioned compatibility path for truly legacy payloads.
- [ ] 2.4 Keep old report reading explicit; stop generating legacy-ledger evidence for new changes.
- [ ] 2.5 Update public command/docs fixtures without adding execution or Git behavior.

## 3. Release

- [ ] 3.1 Run focused/full tests, contracts, type/lint, strict OpenSpec, and full explicit-range Code Review on the behavior-ready tree.
- [ ] 3.2 Update bundle version, manifest integrity, registry entry, signatures, and compatibility metadata only after behavior passes.
- [ ] 3.3 Re-run the complete mandatory quality sequence after every generated manifest, registry, archive, checksum, and signature change, including `verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`; require the generated signature sidecar to exist and match the signed payload, and resolve every finding before publication.
- [ ] 3.4 Publish the signed release and give core the immutable commit/package identities.
- [ ] 3.5 After the implementation and signed handoff merge, run exactly `openspec archive requirements-07-scenario-runtime-proof` from the repository root as the final release-integrity operation; never move the change directory manually.

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
