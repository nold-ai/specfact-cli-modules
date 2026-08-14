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
- [ ] 1.6 Add or retain table-driven `test_planned_mapping_requires_every_schema_v2_field`, `test_selected_test_authored_scenario_requires_exact_selector`, and `test_current_execution_rejects_each_nonpass_or_noncanonical_result` covering missing, duplicate, ambiguous, skipped, failed, errored, missing/mismatched `specfact.selector` properties, display/class-name-only identity, non-canonical selector results, and mismatched mapping digest, plan identity/digest, source revision/tree, or selector set.
- [ ] 1.7 Add table-driven `test_review_context_rejects_each_invalid_requirements_evidence_class` covering unreadable, malformed, unsupported-schema, non-final top-level evidence, and schema-v3 evidence missing either mandatory claim object. Add `test_legacy_v2_passing_review_context_requires_red_junit_or_digest_bound_ledger`; invalid top-level/v3 input and invalid passing-v2 basis must reject before review execution. R07 review fixtures cover only the canonical not-evaluated chronology placeholder; R08 owns unknown/pass/fail chronology provenance.
- [ ] 1.8 Add `test_report_schema_v3_discriminates_corrected_from_legacy_v2` and `test_report_uses_canonical_no_chronology_claim_object` for the mandatory R07 `status: not_evaluated` plus `reason: capsule_not_supplied` placeholder. Assert finalized report v2 routes only to legacy compatibility, finalized report v3 missing either claim is rejected, mapping sidecars remain v2, and R07 has no chronology-request/capsule input and cannot emit chronology pass, fail, or unknown; those tests begin in R08.
- [ ] 1.9 Add or retain `test_mapping_acceptance_requires_complete_provenance` covering mapping digest, decision, stable reviewer identity, reviewer role, timestamp, and immutable reference so the scope correction cannot weaken shipped acceptance checks.
- [ ] 1.10 Add `test_rollback_reader_preserves_independent_claims_as_opaque_provenance` and prove old readers never reinterpret corrected chronology as a legacy basis.
- [ ] 1.11 Record failing commands and outcomes in `TDD_EVIDENCE.md` before source edits.

## 2. Minimal implementation — each task at most two hours

- [ ] 2.1 Add finalized report schema v3 with mandatory current-execution and chronology claim objects; preserve mapping sidecar schema v2 and add an explicit finalized-report v2 compatibility reader. Do not detect legacy by field absence.
- [ ] 2.2 Reconcile current JUnit independently and retain exact outcome classes.
- [ ] 2.3 Update Code Review context validation to require and retain the top-level Requirements gate decision plus both schema-v3 claim objects, including the R07 not-evaluated chronology placeholder; use the versioned compatibility path for truly legacy payloads. R08 later adds non-not-evaluated chronology states.
- [ ] 2.4 Keep old report reading explicit; stop generating legacy-ledger evidence for new changes.
- [ ] 2.5 Update public command/docs fixtures without adding execution or Git behavior.

## 3. Release

- [ ] 3.1 On the feature branch, run focused/full tests, contracts, type/lint, strict OpenSpec, full explicit-range Code Review, and filesystem payload/version-bump verification on the behavior-ready tree.
- [ ] 3.2 After behavior passes, update public docs, bundle version, `module-package.yaml` version and compatibility metadata, and changelog allowed by the implementation plan. Do not generate or hand-edit registry archives, checksums, sidecars, or `registry/index.json` on the feature branch.
- [ ] 3.3 Re-run the complete feature-branch gate sequence after task 3.2 and merge the reviewed implementation PR to `dev` only when it is green. This implementation PR is not yet the signed registry publication.
- [ ] 3.4 Observe the canonical `.github/workflows/publish-modules.yml` run triggered by the `dev` push. It SHALL use the repository signing secret, generate the signed manifest plus registry archive/checksum/signature sidecar/index changes, and open its `auto/publish-dev-<run-id>` PR; no nonexistent local release wrapper may be assumed.
- [ ] 3.5 Review the exact auto-publish PR and require the generated `.tar.sig` sidecar, signed manifest/archive identity, `verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`, and the full final quality matrix to pass before merging that PR to `dev`.
- [ ] 3.6 Give core the immutable merged `dev` commit/tree, package version, registry archive/checksum/signature, manifest integrity, signer, and workflow/auto-publish PR identities. Historical green reports before the auto-publish merge are not signed-release evidence.
- [ ] 3.7 After the implementation and signed handoff merges, run exactly `openspec archive requirements-07-scenario-runtime-proof` from the repository root as the final release-integrity operation; never move the change directory manually.

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
